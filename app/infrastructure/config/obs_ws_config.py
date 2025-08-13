from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.config import settings


CONFIG_DIR = Path("config")
OBS_WS_CONFIG_PATH = CONFIG_DIR / "obs_ws.json"


DEFAULT_WS_CONFIG: Dict[str, Any] = {
    "host": settings.obs_host,
    "port": int(settings.obs_port),
    "password": settings.obs_password,
    "heartbeat": float(getattr(settings, "obs_heartbeat", 15.0)),
}


def ensure_obs_ws_config_exists() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not OBS_WS_CONFIG_PATH.exists():
            OBS_WS_CONFIG_PATH.write_text(
                json.dumps(DEFAULT_WS_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Exception:
        pass


def load_obs_ws_config() -> Dict[str, Any]:
    ensure_obs_ws_config_exists()
    try:
        data = json.loads(OBS_WS_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    # Fill defaults
    out: Dict[str, Any] = dict(DEFAULT_WS_CONFIG)
    out.update({k: v for k, v in (data or {}).items() if v is not None})
    # Normalize types
    try:
        out["port"] = int(out.get("port", settings.obs_port))
    except Exception:
        out["port"] = int(settings.obs_port)
    try:
        out["heartbeat"] = float(out.get("heartbeat", getattr(settings, "obs_heartbeat", 15.0)))
    except Exception:
        out["heartbeat"] = float(getattr(settings, "obs_heartbeat", 15.0))
    out["host"] = str(out.get("host", settings.obs_host) or settings.obs_host)
    out["password"] = str(out.get("password", settings.obs_password) or "")
    return out


def save_obs_ws_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    ensure_obs_ws_config_exists()
    # Merge and normalize
    cur = load_obs_ws_config()
    merged: Dict[str, Any] = {**cur, **(cfg or {})}
    # Persist
    OBS_WS_CONFIG_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


