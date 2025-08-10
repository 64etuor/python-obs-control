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
except Exception:  # keyboard 미설치/권한 문제 시 핫키 비활성화
    keyboard = None  # type: ignore
    _KEYBOARD_AVAILABLE = False

from .obs_client import obs_manager
from app.container import toast_success, toast_error


class HotkeyManager:
    def __init__(self) -> None:
        self._log = logging.getLogger(__name__)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

        # Single-action fallbacks (canonical defaults)
        self.scene_key = os.getenv("HOTKEY_SCENE_KEY", "F10")
        self.scene_name = os.getenv("HOTKEY_SCENE_NAME", "Home")

        self.ss_key = os.getenv("HOTKEY_SCREENSHOT_KEY", "F12")
        self.ss_source = os.getenv("HOTKEY_SCREENSHOT_SOURCE", "cam_front")
        self.ss_dir = Path(os.getenv("SCREENSHOT_DIR", str(Path.home() / "Pictures" / "OBS-Screenshots")))
        # 날짜별 폴더 분할 옵션
        self.ss_split_by_date = os.getenv("SCREENSHOT_SPLIT_BY_DATE", "1").strip() not in {"0", "false", "False"}
        self.ss_format = os.getenv("SCREENSHOT_FORMAT", "png")
        self.ss_width = int(os.getenv("SCREENSHOT_WIDTH", "1080"))
        self.ss_height = int(os.getenv("SCREENSHOT_HEIGHT", "1920"))
        # 기본 업데이트 입력(프론트용)
        self.ss_update_input = os.getenv("SCREENSHOT_UPDATE_INPUT", "img_before_front")

        self.ss_side_key = os.getenv("HOTKEY_SCREENSHOT_SIDE_KEY", "F7")
        self.ss_side_source = os.getenv("HOTKEY_SCREENSHOT_SIDE_SOURCE", "cam_side")
        self.ss_side_update_input = os.getenv("SCREENSHOT_UPDATE_INPUT_SIDE", "img_before_side")

        self.ss_rear_key = os.getenv("HOTKEY_SCREENSHOT_REAR_KEY", "F8")
        self.ss_rear_source = os.getenv("HOTKEY_SCREENSHOT_REAR_SOURCE", "cam_rear")
        self.ss_rear_update_input = os.getenv("SCREENSHOT_UPDATE_INPUT_REAR", "img_before_rear")

        self.stream_toggle_key = os.getenv("HOTKEY_STREAM_TOGGLE_KEY", "F9")

        self.scene_map = self._parse_map_env("HOTKEY_SCENE_MAP")
        self.screenshot_map = self._parse_map_env("HOTKEY_SCREENSHOT_MAP")

        self._registered: list[int | str] = []

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
        self._log.info("hotkeys listener stopped")

    def _run(self) -> None:
        # Prepare dirs
        try:
            self.ss_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self._log.info("hotkeys listener starting")
        # Scene map registrations
        for key_combo, scene in self.scene_map.items():
            self._registered.append(
                keyboard.add_hotkey(key_combo, lambda s=scene: keyboard.call_later(lambda: self._switch_scene_name(s)))
            )
            self._log.info("bind %s -> scene '%s'", key_combo, scene)

        # Screenshot map registrations (generic)
        for key_combo, source in self.screenshot_map.items():
            self._registered.append(
                keyboard.add_hotkey(
                    key_combo,
                    lambda src=source: keyboard.call_later(lambda: self._take_screenshot_source(src)),
                )
            )
            self._log.info("bind %s -> screenshot '%s'", key_combo, source)

        # Backward-compatible single bindings (front default)
        if self.scene_name:
            self._registered.append(
                keyboard.add_hotkey(self.scene_key, lambda: keyboard.call_later(self._switch_scene))
            )
        if self.ss_source:
            self._registered.append(
                keyboard.add_hotkey(self.ss_key, lambda: keyboard.call_later(self._take_screenshot))
            )
            extra = f", update_input='{self.ss_update_input}'" if self.ss_update_input else ""
            self._log.info(
                "bind %s -> screenshot '%s' %sx%s%s",
                self.ss_key,
                self.ss_source,
                self.ss_width,
                self.ss_height,
                extra,
            )

        # New: side/rear dedicated keys
        if self.ss_side_source and self.ss_side_key:
            self._registered.append(
                keyboard.add_hotkey(
                    self.ss_side_key, lambda: keyboard.call_later(lambda: self._take_screenshot_source_custom(self.ss_side_source, self.ss_side_update_input))
                )
            )
            self._log.info(
                "bind %s -> screenshot '%s' (update '%s')",
                self.ss_side_key,
                self.ss_side_source,
                self.ss_side_update_input,
            )
        if self.ss_rear_source and self.ss_rear_key:
            self._registered.append(
                keyboard.add_hotkey(
                    self.ss_rear_key, lambda: keyboard.call_later(lambda: self._take_screenshot_source_custom(self.ss_rear_source, self.ss_rear_update_input))
                )
            )
            self._log.info(
                "bind %s -> screenshot '%s' (update '%s')",
                self.ss_rear_key,
                self.ss_rear_source,
                self.ss_rear_update_input,
            )

        if self.stream_toggle_key:
            self._registered.append(
                keyboard.add_hotkey(self.stream_toggle_key, lambda: keyboard.call_later(self._toggle_stream))
            )

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
        self._take_screenshot_source_custom(self.ss_source, self.ss_update_input)

    def _take_screenshot_source(self, source_name: str):
        self._take_screenshot_source_custom(source_name, self.ss_update_input)

    def _take_screenshot_source_custom(self, source_name: str, update_input: str | None):
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        safe_source = re.sub(r"[^A-Za-z0-9._-]+", "_", source_name)
        target_dir = self.ss_dir
        if self.ss_split_by_date:
            target_dir = target_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        out = target_dir / f"{ts}_{safe_source}.{self.ss_format}"
        import asyncio
        try:
            self._log.info("screenshot request: %s -> %s", source_name, out)
            saved = asyncio.run(
                obs_manager.save_source_screenshot(
                    source_name=source_name,
                    image_file_path=str(out),
                    image_format=self.ss_format,
                    image_width=self.ss_width,
                    image_height=self.ss_height,
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

    def _toggle_stream(self):
        import asyncio
        try:
            asyncio.run(obs_manager.toggle_streaming())
            self._log.info("stream toggle requested")
        except Exception as exc:
            self._log.error("stream toggle failed: %s", exc)


hotkeys = HotkeyManager()


