from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
from pathlib import Path
import configparser

import psutil
import socket

from app.config import settings
from app.obs_client import obs_manager

logger = logging.getLogger(__name__)

_OBS_CANDIDATES = [
    r"C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe",
    r"C:\\Program Files (x86)\\obs-studio\\bin\\64bit\\obs64.exe",
]


def _candidate_paths() -> list[Path]:
    paths: list[str] = []
    if settings.obs_exe_path:
        paths.append(settings.obs_exe_path)
    paths.extend(_OBS_CANDIDATES)
    return [Path(p) for p in paths if p]


def is_obs_running() -> bool:
    for proc in psutil.process_iter(["name", "exe", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            exe = str(proc.info.get("exe") or "").lower()
            if "obs64.exe" in name or os.path.basename(exe) == "obs64.exe" or "obs64.exe" in exe:
                return True
        except Exception:
            continue
    return False


def _resolve_obs_data_path(exe_dir: Path, obs_root: Path) -> Path | None:
    # Priority:
    # 1) settings.obs_data_path (if valid)
    if settings.obs_data_path:
        p = Path(settings.obs_data_path)
        if (p / "locale").exists():
            return p
    # 2) typical install: obs_root/data
    candidate = obs_root / "data"
    if (candidate / "locale").exists():
        return candidate
    # 3) portable zip layouts sometimes: exe_dir/.. (already obs_root), or exe_dir/data
    candidate = exe_dir / "data"
    if (candidate / "locale").exists():
        return candidate
    # 4) common miss: data/obs-studio/locale
    alt = obs_root / "data" / "obs-studio"
    if (alt / "locale").exists():
        return alt
    return None


def launch_obs() -> None:
    exe_path: Path | None = None
    for p in _candidate_paths():
        if p.exists():
            exe_path = p
            break
    if not exe_path:
        raise FileNotFoundError("OBS 실행 파일을 찾지 못했습니다. settings.obs_exe_path를 지정하세요.")

    if settings.obs_ws_autoconfigure:
        try:
            _ensure_obs_ws_enabled()
        except Exception as exc:
            logger.warning("failed to autoconfigure OBS WebSocket: %s", exc)
    # Ensure crash/safe-mode dialogs are suppressed if requested
    if getattr(settings, "obs_auto_dismiss_safemode", True):
        try:
            _ensure_obs_general_prefs()
        except Exception as exc:
            logger.warning("failed to apply OBS general prefs: %s", exc)

    args = [str(exe_path)]
    if settings.obs_launch_args:
        args.extend(shlex.split(settings.obs_launch_args, posix=False))

    exe_dir = exe_path.parent
    obs_root = exe_dir.parent  # .../obs-studio
    env = os.environ.copy()
    # Resolve OBS data path automatically (portable/packaged variants)
    resolved_data = _resolve_obs_data_path(exe_dir, obs_root)
    if resolved_data is not None:
        env["OBS_DATA_PATH"] = str(resolved_data)
        logger.info("OBS_DATA_PATH resolved to %s", env["OBS_DATA_PATH"])
    elif settings.obs_data_path:
        env["OBS_DATA_PATH"] = str(Path(settings.obs_data_path))
        logger.info("OBS_DATA_PATH set from settings to %s", env["OBS_DATA_PATH"])

    try:
        # Prefer CWD at binary dir to match normal shortcuts; data path is provided via OBS_DATA_PATH
        subprocess.Popen(args, cwd=str(exe_dir), env=env)  # noqa: S603
        logger.info("launched OBS: %s", exe_path)
    except Exception as exc:
        logger.error("failed to launch OBS: %s", exc)
        raise


def _ensure_obs_ws_enabled() -> None:
    # Locate %APPDATA%/obs-studio/global.ini
    base_dir: Path
    if settings.obs_config_dir:
        base_dir = Path(settings.obs_config_dir)
    else:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA not found; cannot locate OBS config")
        base_dir = Path(appdata) / "obs-studio"
    cfg_path = base_dir / "global.ini"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    config = configparser.ConfigParser()
    if cfg_path.exists():
        config.read(cfg_path, encoding="utf-8")

    if "OBSWebSocket" not in config:
        config["OBSWebSocket"] = {}

    ws = config["OBSWebSocket"]
    # Enable WebSocket and set port/password per settings
    ws.setdefault("ServerEnabled", "true")
    ws["ServerEnabled"] = "true"
    ws.setdefault("ServerPort", str(settings.obs_port))
    ws["ServerPort"] = str(settings.obs_port)
    if settings.obs_password:
        ws.setdefault("ServerPassword", settings.obs_password)
        ws["ServerPassword"] = settings.obs_password

    with cfg_path.open("w", encoding="utf-8") as f:
        config.write(f)


def _ensure_obs_general_prefs() -> None:
    base_dir: Path
    if settings.obs_config_dir:
        base_dir = Path(settings.obs_config_dir)
    else:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA not found; cannot locate OBS config")
        base_dir = Path(appdata) / "obs-studio"
    cfg_path = base_dir / "global.ini"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    config = configparser.ConfigParser()
    if cfg_path.exists():
        config.read(cfg_path, encoding="utf-8")

    if "General" not in config:
        config["General"] = {}
    gen = config["General"]
    # Disable crash/safe mode dialogs (speculative but widely referenced keys)
    gen["ShowCrashDialog"] = "false"
    gen["ShowCrashRecoveryDialog"] = "false"
    # Some builds use this naming
    gen.setdefault("ShowSafeModeDialog", "false")
    gen["ShowSafeModeDialog"] = "false"

    with cfg_path.open("w", encoding="utf-8") as f:
        config.write(f)


def _is_ws_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


async def wait_for_obs_websocket(timeout_sec: int) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_sec
    while asyncio.get_event_loop().time() < deadline:
        if _is_ws_port_open(settings.obs_host, int(settings.obs_port), timeout=0.5):
            return
        await asyncio.sleep(1.0)
    raise TimeoutError("OBS WebSocket 포트가 열리지 않았습니다")


async def ensure_obs_running() -> None:
    if not is_obs_running():
        logger.info("OBS not running; launching...")
        launch_obs()
    await wait_for_obs_websocket(int(settings.obs_launch_timeout))


async def guardian_loop(stop_event: asyncio.Event) -> None:
    interval = max(1, int(settings.obs_guardian_interval))
    unready_since: float | None = None
    while not stop_event.is_set():
        try:
            if not is_obs_running():
                logger.warning("OBS down detected; relaunching...")
                launch_obs()
                await wait_for_obs_websocket(int(settings.obs_launch_timeout))
                unready_since = None
            else:
                if not _is_ws_port_open(settings.obs_host, int(settings.obs_port), timeout=0.5):
                    now = asyncio.get_event_loop().time()
                    if unready_since is None:
                        unready_since = now
                    # If WS has been unready for longer than launch timeout, force restart
                    if now - unready_since > int(settings.obs_launch_timeout):
                        logger.warning("OBS process present but WS not ready; restarting OBS")
                        _kill_obs_processes()
                        launch_obs()
                        await wait_for_obs_websocket(int(settings.obs_launch_timeout))
                        unready_since = None
                else:
                    unready_since = None
        except Exception as exc:  # noqa: BLE001
            logger.error("OBS guardian error: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


def _kill_obs_processes(grace_seconds: float = 5.0) -> None:
    procs: list[psutil.Process] = []
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = (proc.info.get("name") or "").lower()
            exe = str(proc.info.get("exe") or "").lower()
            if "obs64.exe" in name or os.path.basename(exe) == "obs64.exe" or "obs64.exe" in exe:
                procs.append(proc)
        except Exception:
            continue
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    try:
        psutil.wait_procs(procs, timeout=grace_seconds)
    except Exception:
        pass
    for p in procs:
        if p.is_running():
            try:
                p.kill()
            except Exception:
                pass


