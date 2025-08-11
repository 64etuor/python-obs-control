from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header

from app.container import (
    get_obs_version,
    list_scenes,
    set_scene as uc_set_scene,
    take_screenshot as uc_take_screenshot,
    start_stream as uc_start_stream,
    stop_stream as uc_stop_stream,
    toast_success,
)
from app.utils.screenshot import build_screenshot_path
from app.config import settings
from app.container import get_hotkeys_config as uc_get_hotkeys_config, save_hotkeys_config as uc_save_hotkeys_config
from app.hotkeys import hotkeys
from app.obs_client import obs_manager
import logging
import platform
import psutil
import time
from datetime import datetime
import sys
import threading
import traceback
from app.infrastructure.obs.bootstrap import STANDARD_SCENES
from app.infrastructure.overlay.notification_service_impl import overlay_notifications

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/hotkeys/scenes")
async def hotkeys_scenes() -> dict:
    names = set(STANDARD_SCENES)
    try:
        data = await obs_manager.get_scenes()
        for s in data:
            nm = s.get("sceneName") or s.get("name")
            if nm:
                names.add(str(nm))
    except Exception:
        pass
    return {"scenes": sorted(names)}


@router.get("/hotkeys")
async def get_hotkeys() -> dict:
    data = uc_get_hotkeys_config()()
    return {"hotkeys": data}


@router.post("/hotkeys")
async def set_hotkeys(payload: dict) -> dict:
    try:
        uc_save_hotkeys_config()(payload or {})
        try:
            # Attempt to hot-reload hotkeys without server restart
            hotkeys.reload_config()
        except Exception:
            pass
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/obs/version")
async def obs_version() -> dict:
    try:
        return await get_obs_version()()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/obs/scenes")
async def obs_scenes() -> dict:
    try:
        scenes = await list_scenes()()
        return {"scenes": scenes}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/scene/{scene_name}")
async def set_scene(scene_name: str) -> dict:
    try:
        await uc_set_scene()(scene_name)
        try:
            scene_norm = (scene_name or "").strip().lower()
            action = "resume" if scene_norm in {"youtube", "shorts"} else "pause"
            await overlay_notifications.publish({"type": "overlay_control", "action": action, "scene": scene_name})
        except Exception:
            pass
        return {"ok": True, "scene": scene_name}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/screenshot")
async def take_screenshot(
    source_name: str,
    image_file_path: str,
    image_format: str = "png",
    image_width: int | None = None,
    image_height: int | None = None,
    image_compression_quality: int = 100,
    image_input_update: str | None = None,
) -> dict:
    try:
        # If client passed a relative path, anchor it under unified screenshot root
        from pathlib import Path as _P
        p = _P(image_file_path)
        if not p.is_absolute():
            root = _P(str(settings.screenshot_dir)) if getattr(settings, "screenshot_dir", None) else _P.cwd()
            image_file_path = str(root / p)

        result = await uc_take_screenshot()(
            source_name=source_name,
            image_file_path=image_file_path,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height,
            image_compression_quality=image_compression_quality,
            image_input_update=image_input_update,
        )
        # fire-and-forget toast
        try:
            import asyncio as _asyncio

            _asyncio.create_task(
                toast_success()(f"Screenshot saved: {result['path']}", timeout_ms=1500)
            )
        except Exception:
            pass
        return result
    except Exception as exc:  # noqa: BLE001
        s = str(exc)
        if "702" in s or "render screenshot" in s.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. 소스명이 정확한지, 소스가 현재 활성/렌더 상태인지 확인. "
                    "필요하면 width/height 지정 혹은 다른 포맷을 시도하세요."
                ),
            )
        if "imageWidth" in s and "minimum" in s:
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. width/height 최소값(>=8)을 지정하세요. 예: image_width=1920&image_height=1080"
                ),
            )
        if "code 600" in s or "directory for your file path does not exist" in s.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. 저장 경로의 디렉토리가 존재하지 않습니다. 전체 경로가 유효한지 확인하세요."
                ),
            )
        raise HTTPException(status_code=500, detail=str(exc))


# Dedicated helpers

@router.post("/obs/screenshot/front")
async def screenshot_front(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_before_front",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_front", image_format=image_format)
    return await take_screenshot(
        source_name="cam_front",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/front/after")
async def screenshot_front_after(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_after_front",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_front", image_format=image_format)
    return await take_screenshot(
        source_name="cam_front",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/side")
async def screenshot_side(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_before_side",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_side", image_format=image_format)
    return await take_screenshot(
        source_name="cam_side",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/side/after")
async def screenshot_side_after(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_after_side",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_side", image_format=image_format)
    return await take_screenshot(
        source_name="cam_side",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/rear")
async def screenshot_rear(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_before_rear",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_rear", image_format=image_format)
    return await take_screenshot(
        source_name="cam_rear",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/rear/after")
async def screenshot_rear_after(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_after_rear",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_rear", image_format=image_format)
    return await take_screenshot(
        source_name="cam_rear",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


# --------------------------------------
# Diagnostics
# --------------------------------------

_LOG_BUFFER_MAX = 1000
_log_records: list[dict] = []


class _RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            data = {
                "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
                "level": record.levelname,
                "name": record.name,
                "msg": record.getMessage(),
            }
            _log_records.append(data)
            if len(_log_records) > _LOG_BUFFER_MAX:
                del _log_records[: len(_log_records) - _LOG_BUFFER_MAX]
        except Exception:
            pass


_installed_ring = False


def _ensure_ring_handler() -> None:
    global _installed_ring
    if _installed_ring:
        return
    logging.getLogger().addHandler(_RingBufferHandler())
    _installed_ring = True


def _check_diag_token(x_diag_token: str | None) -> None:
    token = settings.diag_token
    # Require token to be configured and provided
    if not token:
        raise HTTPException(status_code=401, detail="diagnostics disabled (token required)")
    if x_diag_token != token:
        raise HTTPException(status_code=401, detail="invalid diagnostics token")


@router.get("/diagnostics")
async def diagnostics(x_diag_token: str | None = Header(default=None)) -> dict:
    _ensure_ring_handler()
    _check_diag_token(x_diag_token)

    # OBS status
    try:
        stream = await obs_manager.get_stream_status()
    except Exception as exc:  # noqa: BLE001
        stream = {"error": str(exc)}

    # Hotkey status
    hk_status = {
        "enabled": bool(hotkeys is not None),
        "listener_alive": bool(getattr(hotkeys, "_thread", None) and hotkeys._thread.is_alive()),
        "scene_key": getattr(hotkeys, "scene_key", None),
        "screenshot_key": getattr(hotkeys, "ss_key", None),
        "stream_toggle_key": getattr(hotkeys, "stream_toggle_key", None),
        "scene_map": getattr(hotkeys, "scene_map", {}),
    }

    # System/process snapshot
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=None)
    proc = psutil.Process()
    pm = proc.memory_info()

    info = {
        "app": {
            "name": settings.app_name,
            "time": datetime.utcnow().isoformat() + "Z",
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "python": platform.python_version(),
        },
        "obs": {
            "stream": stream,
        },
        "hotkeys": hk_status,
        "system": {
            "cpu_percent": cpu,
            "mem_used_bytes": vm.used,
            "mem_available_bytes": vm.available,
        },
        "process": {
            "pid": proc.pid,
            "cpu_percent": proc.cpu_percent(interval=None),
            "rss_bytes": pm.rss,
            "vms_bytes": pm.vms,
            "num_threads": proc.num_threads(),
            "uptime_seconds": max(0.0, time.time() - proc.create_time()),
        },
    }
    return info


@router.get("/logs")
async def get_logs(limit: int = 200, x_diag_token: str | None = Header(default=None)) -> dict:
    _ensure_ring_handler()
    _check_diag_token(x_diag_token)
    if limit <= 0:
        limit = 100
    if limit > _LOG_BUFFER_MAX:
        limit = _LOG_BUFFER_MAX
    return {"logs": _log_records[-limit:]}


@router.get("/diagnostics/log-level")
async def get_log_level(x_diag_token: str | None = Header(default=None)) -> dict:
    _check_diag_token(x_diag_token)
    level = logging.getLogger().getEffectiveLevel()
    return {"level": logging.getLevelName(level)}


@router.post("/diagnostics/log-level")
async def set_log_level(level: str, x_diag_token: str | None = Header(default=None)) -> dict:
    _check_diag_token(x_diag_token)
    name = level.strip().upper()
    if name not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise HTTPException(status_code=400, detail="invalid level")
    logging.getLogger().setLevel(getattr(logging, name))
    return {"ok": True, "level": name}


@router.get("/diagnostics/threads")
async def diagnostics_threads(x_diag_token: str | None = Header(default=None), max_frames: int = 20) -> dict:
    _check_diag_token(x_diag_token)
    frames = sys._current_frames()  # type: ignore[attr-defined]
    threads = []
    for th in threading.enumerate():
        fid = getattr(th, "ident", None)
        stack_summary = []
        if fid in frames:
            stack_summary = traceback.format_stack(frames[fid], limit=max_frames)
        threads.append(
            {
                "name": th.name,
                "daemon": th.daemon,
                "alive": th.is_alive(),
                "ident": fid,
                "stack": stack_summary,
            }
        )
    return {"threads": threads}


@router.get("/diagnostics/processes")
async def diagnostics_processes(x_diag_token: str | None = Header(default=None), limit: int = 10) -> dict:
    _check_diag_token(x_diag_token)
    if limit <= 0:
        limit = 10
    procs = []
    # Prime cpu_percent snapshot
    for p in psutil.process_iter(attrs=["pid", "name", "username"]):
        try:
            p.cpu_percent(None)
        except Exception:
            pass
    time.sleep(0.05)
    for p in psutil.process_iter(attrs=["pid", "name", "username"]):
        try:
            with p.oneshot():
                cpu = p.cpu_percent(None)
                mem = p.memory_info()
                procs.append(
                    {
                        "pid": p.pid,
                        "name": p.info.get("name"),
                        "user": p.info.get("username"),
                        "cpu_percent": cpu,
                        "rss_bytes": mem.rss,
                        "vms_bytes": mem.vms,
                        "create_time": p.create_time(),
                    }
                )
        except Exception:
            continue
    procs.sort(key=lambda x: (x.get("cpu_percent", 0.0), x.get("rss_bytes", 0)), reverse=True)
    return {"processes": procs[:limit]}


@router.get("/diagnostics/services")
async def diagnostics_services(x_diag_token: str | None = Header(default=None)) -> dict:
    _check_diag_token(x_diag_token)
    out: list[dict] = []
    if platform.system().lower().startswith("win") and hasattr(psutil, "win_service_iter"):
        try:
            for svc in psutil.win_service_iter():  # type: ignore[attr-defined]
                try:
                    info = svc.as_dict()
                    out.append(
                        {
                            "name": info.get("name"),
                            "display_name": info.get("display_name"),
                            "status": info.get("status"),
                            "start_type": info.get("start_type"),
                        }
                    )
                except Exception:
                    continue
        except Exception:
            pass
    return {"services": out}
