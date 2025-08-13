import os
import re
import threading
import time
import logging
from datetime import datetime
from pathlib import Path

try:
    import keyboard  # type: ignore
    _KEYBOARD_AVAILABLE = True
except Exception:
    keyboard = None  # type: ignore
    _KEYBOARD_AVAILABLE = False

from .obs_client import obs_manager
from app.config import settings
from app.container import toast_success, toast_error, toast_warning
from app.utils.screenshot import build_screenshot_path
from app.container import get_hotkeys_config as uc_get_hotkeys_config


class HotkeyManager:
    def __init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._registered: list[int | str] = []

        # Unified screenshot root from settings (env SCREENSHOT_DIR still respected by settings)
        self.ss_dir = Path(getattr(settings, "screenshot_dir", str(Path.home() / "Pictures" / "OBS-Screenshots")))
        # 날짜별 폴더 분할 옵션
        self.ss_split_by_date = os.getenv("SCREENSHOT_SPLIT_BY_DATE", "1").strip() not in {"0", "false", "False"}
        self.ss_format = os.getenv("SCREENSHOT_FORMAT", "png")
        self.ss_width = int(os.getenv("SCREENSHOT_WIDTH", "1080"))
        self.ss_height = int(os.getenv("SCREENSHOT_HEIGHT", "1920"))
        # Load JSON config for hotkeys via use-case (after env defaults ready)
        self._apply_config(self._load_config())
        # Dimension constraints
        self.CAM_MIN_W, self.CAM_MIN_H = 320, 240
        self.CAM_MAX_W, self.CAM_MAX_H = 1080, 1920
        self.WIN_MIN_W, self.WIN_MIN_H = 320, 180
        self.WIN_MAX_W, self.WIN_MAX_H = 1920, 1080
        # 기본 업데이트 입력(프론트용) will be set by _apply_config

        # After-shot (시술 후) will be set by _apply_config

        # Side will be set by _apply_config

        # After-shot side set by _apply_config

        # Rear set by _apply_config

        # After-shot rear set by _apply_config

        # Hair config will be set by _apply_config

        # Reset config will be set by _apply_config
        self._img_reset_armed_at: float | None = None

        # Stream toggle set by _apply_config

        # Maps set by _apply_config

    def _load_config(self) -> dict:
        try:
            return uc_get_hotkeys_config()()
        except Exception:
            return {}

    def _apply_config(self, _cfg: dict) -> None:
        # scene: no global default; optional if provided
        self.scene_key = str((_cfg.get("scene") or {}).get("key", ""))
        self.scene_name = str((_cfg.get("scene") or {}).get("name", ""))

        sc = (_cfg.get("screenshot") or {})
        pb = (sc.get("procedure_before") or {})
        pa = (sc.get("procedure_after") or {})

        d = (pb.get("front") or {})
        self.ss_key = str(d.get("key", "F5"))
        self.ss_source = str(d.get("source", "cam_front"))
        self.ss_update_input = str(d.get("update_input", "img_before_front"))
        self.ss_front_width = int(str(d.get("width", self.ss_width)))
        self.ss_front_height = int(str(d.get("height", self.ss_height)))

        s = (pb.get("side") or {})
        self.ss_side_key = str(s.get("key", "F6"))
        self.ss_side_source = str(s.get("source", "cam_side"))
        self.ss_side_update_input = str(s.get("update_input", "img_before_side"))
        self.ss_side_width = int(str(s.get("width", self.ss_width)))
        self.ss_side_height = int(str(s.get("height", self.ss_height)))

        r = (pb.get("rear") or {})
        self.ss_rear_key = str(r.get("key", "F7"))
        self.ss_rear_source = str(r.get("source", "cam_rear"))
        self.ss_rear_update_input = str(r.get("update_input", "img_before_rear"))
        self.ss_rear_width = int(str(r.get("width", self.ss_width)))
        self.ss_rear_height = int(str(r.get("height", self.ss_height)))

        af = (pa.get("front") or {})
        self.ss_after_key = str(af.get("key", "shift+F5"))
        self.ss_after_source = str(af.get("source", "cam_front"))
        self.ss_after_update_input = str(af.get("update_input", "img_after_front"))
        self.ss_after_front_width = int(str(af.get("width", self.ss_width)))
        self.ss_after_front_height = int(str(af.get("height", self.ss_height)))

        sa = (pa.get("side") or {})
        self.ss_side_after_key = str(sa.get("key", "shift+F6"))
        self.ss_side_after_source = str(sa.get("source", "cam_side"))
        self.ss_side_after_update_input = str(sa.get("update_input", "img_after_side"))
        self.ss_side_after_width = int(str(sa.get("width", self.ss_width)))
        self.ss_side_after_height = int(str(sa.get("height", self.ss_height)))

        ra = (pa.get("rear") or {})
        self.ss_rear_after_key = str(ra.get("key", "shift+F7"))
        self.ss_rear_after_source = str(ra.get("source", "cam_rear"))
        self.ss_rear_after_update_input = str(ra.get("update_input", "img_after_rear"))
        self.ss_rear_after_width = int(str(ra.get("width", self.ss_width)))
        self.ss_rear_after_height = int(str(ra.get("height", self.ss_height)))

        h = (sc.get("hair_reference") or {})
        self.ss_hair_key = str(h.get("key", "F8"))
        self.ss_hair_source = str(h.get("source", "window_capture"))
        self.ss_hair_update_input = str(h.get("update_input", "img_hair_reference"))
        self.ss_hair_width = int(str(h.get("width", 1920)))
        self.ss_hair_height = int(str(h.get("height", 1080)))

        imr = (_cfg.get("img_reset") or {})
        self.img_reset_key = str(imr.get("key", "ctrl+F8"))
        self.img_reset_targets = str(
            imr.get(
                "targets",
                "img_before_front,img_after_front,img_before_side,img_after_side,img_before_rear,img_after_rear,img_hair_reference",
            )
        )
        self.img_reset_confirm_window_sec = int(str(imr.get("confirm_window_sec", 5)))

        self.stream_toggle_key = str(_cfg.get("stream_toggle_key", "F9"))
        self.scene_map = (_cfg.get("scene_map") or {})
        self.screenshot_map = (_cfg.get("screenshot_map") or {})

    def reload_config(self) -> None:
        # Stop listener, re-apply config, and restart
        was_alive = bool(self._thread and self._thread.is_alive())
        self.stop()
        self._apply_config(self._load_config())
        if was_alive:
            self.start()

        # _registered initialized in __init__

    @staticmethod
    def _parse_map_env(var_name: str) -> dict[str, str]:
        raw = os.getenv(var_name, "").strip()
        if not raw:
            return {}
        parts = re.split(r"[;\n,]+", raw)
        result: dict[str, str] = {}
        for p in parts:
            if not p:
                continue
            if "=" not in p:
                continue
            k, v = p.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k and v:
                result[k] = v
        return result

    def _wrap_hotkey(self, combo: str, category: str, target: str | None, action: callable) -> callable:
        def _cb() -> None:
            def _execute() -> None:
                try:
                    self._log.info(
                        "hotkey pressed: %s -> %s",
                        combo,
                        target or category,
                        extra={
                            "hotkey.combo": combo,
                            "hotkey.category": category,
                            "hotkey.target": target,
                        },
                    )
                except Exception:
                    pass
                try:
                    action()
                except Exception:
                    pass
            if _KEYBOARD_AVAILABLE:
                keyboard.call_later(_execute)
            else:
                _execute()
        return _cb

    def start(self) -> None:
        if not _KEYBOARD_AVAILABLE:
            self._log.warning("hotkeys disabled: keyboard module unavailable or permission denied")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="hotkey-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            if _KEYBOARD_AVAILABLE:
                for hk in self._registered:
                    keyboard.remove_hotkey(hk)
        except Exception:
            pass
        # Ensure listener thread fully stops before returning to allow immediate restart
        try:
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
        except Exception:
            pass
        # Reset state
        self._registered.clear()
        self._thread = None
        self._log.info("hotkeys listener stopped")

    def _run(self) -> None:
        # Prepare dirs
        try:
            self.ss_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self._log.info("hotkeys listener starting")
        # Scene map registrations (from config maps + explicit scene_hotkeys)
        sc_map = dict(self.scene_map)
        try:
            cfg = self._load_config()
            for scene_name, key_combo in (cfg.get("scene_hotkeys") or {}).items():
                kc = str(key_combo or '').strip()
                if kc:
                    sc_map[kc] = str(scene_name)
        except Exception:
            pass
        for key_combo, scene in sc_map.items():
            try:
                cb = self._wrap_hotkey(key_combo, "scene", scene, lambda s=scene: self._switch_scene_name(s))
                self._registered.append(keyboard.add_hotkey(key_combo, cb))
                self._log.info("bind %s -> scene '%s'", key_combo, scene)
            except Exception as exc:
                self._log.warning("failed bind for scene hotkey %s -> %s: %s", key_combo, scene, exc)

        # Screenshot map registrations (generic)
        for key_combo, source in self.screenshot_map.items():
            cb = self._wrap_hotkey(key_combo, "screenshot", source, lambda src=source: self._take_screenshot_source(src))
            self._registered.append(keyboard.add_hotkey(key_combo, cb))
            self._log.info("bind %s -> screenshot '%s'", key_combo, source)

        # Backward-compatible single bindings (front default)
        if self.scene_name:
            self._registered.append(
                keyboard.add_hotkey(self.scene_key, lambda: keyboard.call_later(self._switch_scene))
            )
        if self.ss_source:
            cb = self._wrap_hotkey(self.ss_key, "screenshot", self.ss_source, self._take_screenshot)
            self._registered.append(keyboard.add_hotkey(self.ss_key, cb))
            extra = f", update_input='{self.ss_update_input}'" if self.ss_update_input else ""
            self._log.info(
                "bind %s -> screenshot '%s' %sx%s%s",
                self.ss_key,
                self.ss_source,
                getattr(self, "ss_front_width", self.ss_width),
                getattr(self, "ss_front_height", self.ss_height),
                extra,
            )

        # After-shot front
        if self.ss_after_source and self.ss_after_key:
            cb = self._wrap_hotkey(
                self.ss_after_key,
                "screenshot",
                self.ss_after_source,
                lambda: self._take_screenshot_source_custom(
                    self.ss_after_source,
                    self.ss_after_update_input,
                    self.ss_after_front_width,
                    self.ss_after_front_height,
                ),
            )
            self._registered.append(keyboard.add_hotkey(self.ss_after_key, cb))
            self._log.info(
                "bind %s -> screenshot(after) '%s' %sx%s (update '%s')",
                self.ss_after_key,
                self.ss_after_source,
                getattr(self, "ss_after_front_width", self.ss_width),
                getattr(self, "ss_after_front_height", self.ss_height),
                self.ss_after_update_input,
            )

        # New: side/rear dedicated keys
        if self.ss_side_source and self.ss_side_key:
            cb = self._wrap_hotkey(
                self.ss_side_key,
                "screenshot",
                self.ss_side_source,
                lambda: self._take_screenshot_source_custom(
                    self.ss_side_source,
                    self.ss_side_update_input,
                    self.ss_side_width,
                    self.ss_side_height,
                ),
            )
            self._registered.append(keyboard.add_hotkey(self.ss_side_key, cb))
            self._log.info(
                "bind %s -> screenshot '%s' %sx%s (update '%s')",
                self.ss_side_key,
                self.ss_side_source,
                getattr(self, "ss_side_width", self.ss_width),
                getattr(self, "ss_side_height", self.ss_height),
                self.ss_side_update_input,
            )
        # After-shot side
        if self.ss_side_after_source and self.ss_side_after_key:
            cb = self._wrap_hotkey(
                self.ss_side_after_key,
                "screenshot",
                self.ss_side_after_source,
                lambda: self._take_screenshot_source_custom(
                    self.ss_side_after_source,
                    self.ss_side_after_update_input,
                    self.ss_side_after_width,
                    self.ss_side_after_height,
                ),
            )
            self._registered.append(keyboard.add_hotkey(self.ss_side_after_key, cb))
            self._log.info(
                "bind %s -> screenshot(after) '%s' %sx%s (update '%s')",
                self.ss_side_after_key,
                self.ss_side_after_source,
                getattr(self, "ss_side_after_width", self.ss_width),
                getattr(self, "ss_side_after_height", self.ss_height),
                self.ss_side_after_update_input,
            )
        if self.ss_rear_source and self.ss_rear_key:
            cb = self._wrap_hotkey(
                self.ss_rear_key,
                "screenshot",
                self.ss_rear_source,
                lambda: self._take_screenshot_source_custom(
                    self.ss_rear_source,
                    self.ss_rear_update_input,
                    self.ss_rear_width,
                    self.ss_rear_height,
                ),
            )
            self._registered.append(keyboard.add_hotkey(self.ss_rear_key, cb))
            self._log.info(
                "bind %s -> screenshot '%s' %sx%s (update '%s')",
                self.ss_rear_key,
                self.ss_rear_source,
                getattr(self, "ss_rear_width", self.ss_width),
                getattr(self, "ss_rear_height", self.ss_height),
                self.ss_rear_update_input,
            )
        # After-shot rear
        if self.ss_rear_after_source and self.ss_rear_after_key:
            cb = self._wrap_hotkey(
                self.ss_rear_after_key,
                "screenshot",
                self.ss_rear_after_source,
                lambda: self._take_screenshot_source_custom(
                    self.ss_rear_after_source,
                    self.ss_rear_after_update_input,
                    self.ss_rear_after_width,
                    self.ss_rear_after_height,
                ),
            )
            self._registered.append(keyboard.add_hotkey(self.ss_rear_after_key, cb))
            self._log.info(
                "bind %s -> screenshot(after) '%s' %sx%s (update '%s')",
                self.ss_rear_after_key,
                self.ss_rear_after_source,
                getattr(self, "ss_rear_after_width", self.ss_width),
                getattr(self, "ss_rear_after_height", self.ss_height),
                self.ss_rear_after_update_input,
            )

        # Hair reference hotkey: window_capture screenshot -> update img_hair_reference
        if self.ss_hair_source and self.ss_hair_key:
            cb = self._wrap_hotkey(
                self.ss_hair_key,
                "screenshot",
                self.ss_hair_source,
                lambda: self._take_screenshot_source_custom(
                    self.ss_hair_source,
                    self.ss_hair_update_input,
                    self.ss_hair_width,
                    self.ss_hair_height,
                ),
            )
            self._registered.append(keyboard.add_hotkey(self.ss_hair_key, cb))
            self._log.info(
                "bind %s -> screenshot '%s' %sx%s (update '%s')",
                self.ss_hair_key,
                self.ss_hair_source,
                self.ss_hair_width,
                self.ss_hair_height,
                self.ss_hair_update_input,
            )

        # Reset all image inputs hotkey
        if self.img_reset_key:
            cb = self._wrap_hotkey(self.img_reset_key, "img_reset", self.img_reset_targets, self._on_img_reset_hotkey)
            self._registered.append(keyboard.add_hotkey(self.img_reset_key, cb))
            self._log.info("bind %s -> reset all image inputs (2-step confirm)", self.img_reset_key)

        if self.stream_toggle_key:
            cb = self._wrap_hotkey(self.stream_toggle_key, "stream", "toggle", self._toggle_stream)
            self._registered.append(keyboard.add_hotkey(self.stream_toggle_key, cb))

        # Keep the thread alive until stop
        while not self._stop.is_set():
            time.sleep(0.2)

    # Actions
    def _switch_scene(self):
        if not self.scene_name:
            return
        import asyncio
        asyncio.run(self._async_switch_scene(self.scene_name))

    def _switch_scene_name(self, scene_name: str):
        import asyncio
        try:
            asyncio.run(self._async_switch_scene(scene_name))
        except Exception as exc:
            self._log.error("scene switch failed: %s — %s", scene_name, exc)

    async def _async_switch_scene(self, scene_name: str):
        await obs_manager.set_current_scene(scene_name)

    def _take_screenshot(self):
        self._take_screenshot_source_custom(self.ss_source, self.ss_update_input, self.ss_front_width, self.ss_front_height)

    def _take_screenshot_source(self, source_name: str):
        self._take_screenshot_source_custom(source_name, self.ss_update_input, None, None)

    def _take_screenshot_source_custom(self, source_name: str, update_input: str | None, width: int | None, height: int | None):
        out_str = build_screenshot_path(
            source_name,
            image_format=self.ss_format,
            base_dir=self.ss_dir,
            split_by_date=self.ss_split_by_date,
        )
        out = Path(out_str)
        import asyncio
        try:
            self._log.info("screenshot request: %s -> %s", source_name, out)
            # 해상도 결정: 우선 명시값, 다음 헤어 소스, 마지막 글로벌 기본
            w = int(width) if width else self.ss_width
            h = int(height) if height else self.ss_height
            if not width and not height and source_name == self.ss_hair_source:
                w = self.ss_hair_width
                h = self.ss_hair_height

            # Clamp by source type
            req_w, req_h = int(w), int(h)
            if source_name == self.ss_hair_source:
                clamped_w = max(self.WIN_MIN_W, min(req_w, self.WIN_MAX_W))
                clamped_h = max(self.WIN_MIN_H, min(req_h, self.WIN_MAX_H))
                kind = "window"
            else:
                clamped_w = max(self.CAM_MIN_W, min(req_w, self.CAM_MAX_W))
                clamped_h = max(self.CAM_MIN_H, min(req_h, self.CAM_MAX_H))
                kind = "camera"
            if clamped_w != req_w or clamped_h != req_h:
                self._log.info(
                    "screenshot size clamp (%s): requested=%sx%s -> effective=%sx%s",
                    kind,
                    req_w,
                    req_h,
                    clamped_w,
                    clamped_h,
                )
            else:
                self._log.info("screenshot size (%s): %sx%s", kind, req_w, req_h)
            w, h = clamped_w, clamped_h
            saved = asyncio.run(
                obs_manager.save_source_screenshot(
                    source_name=source_name,
                    image_file_path=str(out),
                    image_format=self.ss_format,
                    image_width=w,
                    image_height=h,
                )
            )
            self._log.info("screenshot saved: %s", saved)
            if update_input:
                try:
                    asyncio.run(obs_manager.update_image_source_file(update_input, str(saved)))
                    self._log.info("image input update: %s -> %s", update_input, saved)
                except Exception as exc:
                    self._log.error("image input update failed: %s — %s", update_input, exc)
            try:
                asyncio.run(toast_success()(f"스크린샷 저장됨: {saved}", timeout_ms=2000))
            except Exception:
                pass
        except Exception as exc:
            self._log.error("screenshot failed: %s — %s", source_name, exc)
            try:
                asyncio.run(toast_error()(f"스크린샷 실패: {exc}", timeout_ms=2000))
            except Exception:
                pass

    def _reset_all_img_inputs(self):
        import asyncio
        try:
            targets = [t.strip() for t in re.split(r"[,;\s]+", self.img_reset_targets) if t.strip()]
            if not targets:
                return
            for name in targets:
                try:
                    asyncio.run(obs_manager.set_input_settings(name, {"file": ""}, False))
                except Exception as exc:
                    self._log.warning("image input reset failed for %s: %s", name, exc)
            try:
                asyncio.run(toast_success()(f"이미지 경로 초기화 완료: {len(targets)}개", timeout_ms=1800))
            except Exception:
                pass
        except Exception as exc:
            self._log.error("image inputs reset failed: %s", exc)
            try:
                asyncio.run(toast_error()(f"이미지 초기화 실패: {exc}", timeout_ms=2000))
            except Exception:
                pass

    def _toggle_stream(self):
        import asyncio
        try:
            asyncio.run(obs_manager.toggle_streaming())
            self._log.info("stream toggle requested")
        except Exception as exc:
            self._log.error("stream toggle failed: %s", exc)

    def _on_img_reset_hotkey(self) -> None:
        import asyncio
        try:
            now = time.time()
            window = max(1, int(self.img_reset_confirm_window_sec))
            if self._img_reset_armed_at is not None and (now - self._img_reset_armed_at) <= window:
                # Confirmed within window
                self._img_reset_armed_at = None
                self._reset_all_img_inputs()
                return
            # Arm and prompt
            self._img_reset_armed_at = now
            try:
                asyncio.run(
                    toast_warning()(f"이미지 경로 초기화 준비됨: {window}초 내에 한번 더 누르면 실행", timeout_ms=min(window * 1000, 8000))
                )
            except Exception:
                pass
        except Exception as exc:
            self._log.error("img reset hotkey handler failed: %s", exc)


hotkeys = HotkeyManager()


