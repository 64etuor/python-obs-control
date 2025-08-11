from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path


def build_screenshot_path(
    source_name: str,
    *,
    image_format: str = "png",
    base_dir: str | os.PathLike[str] | None = None,
    split_by_date: bool = True,
) -> str:
    if base_dir is None:
        try:
            from app.config import settings  # lazy import to avoid cycles during startup

            base_dir = getattr(settings, "screenshot_dir", None) or os.getenv(
                "SCREENSHOT_DIR", str(Path.home() / "Pictures" / "OBS-Screenshots")
            )
        except Exception:
            base_dir = os.getenv("SCREENSHOT_DIR", str(Path.home() / "Pictures" / "OBS-Screenshots"))
    now = datetime.now()
    target_dir = Path(base_dir)
    if split_by_date:
        target_dir = target_dir / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    ts = now.strftime("%Y%m%d_%H%M%S")
    safe_source = re.sub(r"[^A-Za-z0-9._-]+", "_", source_name)
    return str(target_dir / f"{ts}_{safe_source}.{image_format}")
