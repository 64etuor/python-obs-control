from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


_log = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = Path("config")
_DEFAULT_CONFIG_FILE = _DEFAULT_CONFIG_DIR / "screenshot_retention.json"


@dataclass
class ScreenshotRetention:
    enabled: bool = True
    days: int = 90
    interval_sec: int = 3600


_settings_lock = asyncio.Lock()


async def load_settings() -> ScreenshotRetention:
    async with _settings_lock:
        try:
            if not _DEFAULT_CONFIG_FILE.exists():
                return ScreenshotRetention()
            data = json.loads(_DEFAULT_CONFIG_FILE.read_text(encoding="utf-8"))
            return ScreenshotRetention(
                enabled=bool(data.get("enabled", True)),
                days=int(data.get("days", 90)),
                interval_sec=int(data.get("interval_sec", 3600)),
            )
        except Exception:
            return ScreenshotRetention()


async def save_settings(value: ScreenshotRetention) -> None:
    async with _settings_lock:
        try:
            _DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        _DEFAULT_CONFIG_FILE.write_text(json.dumps(asdict(value), ensure_ascii=False, indent=2), encoding="utf-8")


def _iter_image_files(paths: Iterable[os.PathLike[str] | str]) -> Iterable[Path]:
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    for p in paths:
        root = Path(p)
        if not root.exists():
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            d = Path(dirpath)
            for name in filenames:
                if Path(name).suffix.lower() in exts:
                    yield d / name


def cleanup_once(paths: Iterable[os.PathLike[str] | str], *, days: int) -> dict:
    cutoff = datetime.now() - timedelta(days=int(days))
    deleted = 0
    checked = 0
    bytes_deleted = 0
    for f in _iter_image_files(paths):
        try:
            checked += 1
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                try:
                    bytes_deleted += f.stat().st_size
                except Exception:
                    pass
                f.unlink(missing_ok=True)
                deleted += 1
        except Exception:
            continue
    return {
        "checked": checked,
        "deleted": deleted,
        "bytes_deleted": int(bytes_deleted),
        "cutoff": cutoff.isoformat(),
    }


async def retention_loop(stop_event: asyncio.Event, paths: list[str]) -> None:
    while not stop_event.is_set():
        try:
            cfg = await load_settings()
            if cfg.enabled and cfg.days > 0:
                result = cleanup_once(paths, days=cfg.days)
                _log.info(
                    "screenshot retention: checked=%s deleted=%s bytes=%s cutoff=%s",
                    result.get("checked"),
                    result.get("deleted"),
                    result.get("bytes_deleted"),
                    result.get("cutoff"),
                )
            wait_sec = max(30, int(cfg.interval_sec))
        except Exception as exc:
            _log.error("screenshot retention error: %s", exc)
            wait_sec = 300
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_sec)
        except asyncio.TimeoutError:
            pass


