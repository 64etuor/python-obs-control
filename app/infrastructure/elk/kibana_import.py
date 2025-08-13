from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import requests

from app.config import settings


_log = logging.getLogger(__name__)


def _resolve_repo_root() -> Path:
    try:
        return Path(__file__).resolve().parents[3]
    except Exception:
        return Path.cwd()


def _kibana_ready(base_url: str, timeout_sec: int = 5) -> bool:
    base = base_url.rstrip("/")
    try:
        r = requests.get(f"{base}/api/status", timeout=timeout_sec)
        if 200 <= r.status_code < 300:
            return True
    except Exception:
        pass
    try:
        r = requests.get(
            f"{base}/api/saved_objects/_find",
            params={"type": "dashboard", "per_page": 1},
            headers={"kbn-xsrf": "true"},
            timeout=timeout_sec,
        )
        if 200 <= r.status_code < 300:
            return True
    except Exception:
        pass
    return False


def _import_ndjson(base_url: str, file_path: Path) -> None:
    base = base_url.rstrip("/")
    url = f"{base}/api/saved_objects/_import"
    headers = {"kbn-xsrf": "true"}
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/ndjson")}
        r = requests.post(url, headers=headers, params={"overwrite": "true"}, files=files, timeout=60)
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"Kibana import failed for {file_path.name}: {r.status_code} {r.text}")


async def kibana_import_background() -> None:
    base_url = getattr(settings, "kibana_url", "http://localhost:5601")
    timeout_total = int(getattr(settings, "kibana_import_timeout_sec", 300))
    repo_root = _resolve_repo_root()
    data_views = repo_root / "elk" / "kibana" / "data_views.ndjson"
    lens_full = repo_root / "elk" / "kibana" / "lens_full.ndjson"

    if not data_views.exists() or not lens_full.exists():
        _log.info("kibana import skipped: ndjson files not found")
        return

    # Wait for Kibana readiness with timeout
    deadline = asyncio.get_event_loop().time() + timeout_total
    while asyncio.get_event_loop().time() < deadline:
        if await asyncio.to_thread(_kibana_ready, base_url):
            break
        await asyncio.sleep(3)
    else:
        _log.warning("kibana not ready within %ss; skip import", timeout_total)
        return

    try:
        # Import data views first, then dashboards/lens
        await asyncio.to_thread(_import_ndjson, base_url, data_views)
        await asyncio.to_thread(_import_ndjson, base_url, lens_full)
        _log.info("kibana ndjson import completed")
    except Exception as exc:  # noqa: BLE001
        _log.warning("kibana import failed: %s", exc)


