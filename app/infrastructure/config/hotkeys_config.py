from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict
from app.domain.ports.hotkeys_config_repository import IHotkeysConfigRepository


CONFIG_DIR = Path("config")
HOTKEYS_CONFIG_PATH = CONFIG_DIR / "hotkeys.json"


DEFAULT_HOTKEY_CONFIG: Dict[str, Any] = {
    # Explicit per-scene hotkeys (scene name -> key combo)
    "scene_hotkeys": {
        "Home": "F10",
        "ReferenceSearch": "F11",
        "LiveFront": "ctrl+1",
        "LiveSide": "ctrl+2",
        "LiveRear": "ctrl+3",
        "LiveThreeWay": "ctrl+4",
        "ProcedureBeforeFront": "alt+1",
        "ProcedureBeforeSide": "alt+2",
        "ProcedureBeforeRear": "alt+3",
        "ProcedureAfterFront": "alt+shift+1",
        "ProcedureAfterSide": "alt+shift+2",
        "ProcedureAfterRear": "alt+shift+3",
        "Relax": "F12",
        "Reels": "ctrl+F12",
        "YouTube": "shift+F12",
    },
    "screenshot": {
        "procedure_before": {
            "front": {"key": "F5", "source": "cam_front", "update_input": "img_before_front", "width": 1080, "height": 1920},
            "side": {"key": "F6", "source": "cam_side", "update_input": "img_before_side", "width": 1080, "height": 1920},
            "rear": {"key": "F7", "source": "cam_rear", "update_input": "img_before_rear", "width": 1080, "height": 1920}
        },
        "procedure_after": {
            "front": {"key": "shift+F5", "source": "cam_front", "update_input": "img_after_front", "width": 1080, "height": 1920},
            "side": {"key": "shift+F6", "source": "cam_side", "update_input": "img_after_side", "width": 1080, "height": 1920},
            "rear": {"key": "shift+F7", "source": "cam_rear", "update_input": "img_after_rear", "width": 1080, "height": 1920}
        },
        "hair_reference": {
            "key": "F8",
            "source": "window_capture",
            "update_input": "img_hair_reference",
            "width": 1920,
            "height": 1080
        }
    },
    "img_reset": {
        "key": "ctrl+F8",
        "targets": "img_before_front,img_after_front,img_before_side,img_after_side,img_before_rear,img_after_rear,img_hair_reference",
        "confirm_window_sec": 5,
    },
    "stream_toggle_key": "F9",
    "scene_map": {},
    "screenshot_map": {},
}


def _deep_merge(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(defaults)
    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[index]
        else:
            out[k] = v
    return out


def ensure_hotkeys_config_exists() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not HOTKEYS_CONFIG_PATH.exists():
            HOTKEYS_CONFIG_PATH.write_text(
                json.dumps(DEFAULT_HOTKEY_CONFIG, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    except Exception:
        pass


def load_hotkey_config() -> Dict[str, Any]:
    ensure_hotkeys_config_exists()
    try:
        data = json.loads(HOTKEYS_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    return _deep_merge(DEFAULT_HOTKEY_CONFIG, data)


def save_hotkey_config(cfg: Dict[str, Any]) -> None:
    ensure_hotkeys_config_exists()
    try:
        # Merge to ensure required defaults present
        merged = _deep_merge(DEFAULT_HOTKEY_CONFIG, cfg or {})
        HOTKEYS_CONFIG_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        # swallow to avoid crashing callers; API should report failure if needed
        raise


class FileHotkeysConfigRepository(IHotkeysConfigRepository):
    def load(self) -> Dict[str, Any]:
        return load_hotkey_config()

    def save(self, cfg: Dict[str, Any]) -> None:
        save_hotkey_config(cfg)


