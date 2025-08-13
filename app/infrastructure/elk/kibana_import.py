from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import requests
import json

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
        try:
            body = r.json()
            if isinstance(body, dict):
                if body.get("success") is False or body.get("errors"):
                    _log.warning("kibana import warnings for %s: %s", file_path.name, json.dumps(body, ensure_ascii=False))
        except Exception:
            pass


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
        # Post-fix Lens references to ensure index-pattern ids are set
        try:
            lens_to_dataview: dict[str, str] = {
                # logs
                "logs_timeseries_count_lens": "python_obs_control_logs",
                "logs_top_loggers_lens": "python_obs_control_logs",
                "logs_top_hotkeys_func_lens": "python_obs_control_logs",
                "logs_top_actions_lens": "python_obs_control_logs",
                "logs_top_modules_lens": "python_obs_control_logs",
                "logs_top_hotkey_combos_lens": "python_obs_control_logs",
                "logs_top_hotkey_targets_lens": "python_obs_control_logs",
                "logs_hotkeys_timeseries_count_lens": "python_obs_control_logs",
                # metrics
                "metrics_cpu_percent_lens": "metricbeat_metrics",
                "metrics_process_rss_lens": "metricbeat_metrics",
                "metrics_process_cpu_lens": "metricbeat_metrics",
                "metrics_process_vms_lens": "metricbeat_metrics",
                "metrics_open_handles_lens": "metricbeat_metrics",
            }
            base = base_url.rstrip("/")
            headers = {"kbn-xsrf": "true", "content-type": "application/json"}

            for lens_id, dv_id in lens_to_dataview.items():
                try:
                    gr = requests.get(f"{base}/api/saved_objects/lens/{lens_id}", headers=headers, timeout=30)
                    if not (200 <= gr.status_code < 300):
                        continue
                    obj = gr.json()
                    attrs = obj.get("attributes", {})
                    refs = obj.get("references", []) or []
                    new_refs = []
                    has_current = False
                    for r in refs:
                        if r.get("type") == "index-pattern":
                            new_refs.append({"type": "index-pattern", "name": r.get("name"), "id": dv_id})
                            if r.get("name") == "indexpattern-datasource-current-indexpattern":
                                has_current = True
                        else:
                            # keep other refs as-is
                            new_refs.append(r)
                    if not has_current:
                        new_refs.append({
                            "type": "index-pattern",
                            "name": "indexpattern-datasource-current-indexpattern",
                            "id": dv_id,
                        })
                    body = json.dumps({"attributes": attrs, "references": new_refs})
                    pr = requests.put(f"{base}/api/saved_objects/lens/{lens_id}", headers=headers, data=body, timeout=30)
                    if not (200 <= pr.status_code < 300):
                        _log.warning("kibana lens post-fix failed for %s: %s %s", lens_id, pr.status_code, pr.text)
                except Exception as _exc:  # noqa: BLE001
                    _log.warning("kibana lens post-fix error for %s: %s", lens_id, _exc)
            # Additionally, scan all lenses to fix missing index-pattern ids heuristically
            try:
                fr = requests.get(f"{base}/api/saved_objects/_find", params={"type": "lens", "per_page": 1000}, headers={"kbn-xsrf": "true"}, timeout=30)
                if 200 <= fr.status_code < 300:
                    data = fr.json() or {}
                    for it in (data.get("saved_objects") or []):
                        lid = it.get("id")
                        attrs = it.get("attributes", {})
                        refs = it.get("references", []) or []
                        changed = False
                        for r in refs:
                            if r.get("type") == "index-pattern" and not r.get("id"):
                                # Heuristic mapping by lens id prefix
                                dv_id = "metricbeat_metrics" if str(lid).startswith("metrics_") else "python_obs_control_logs"
                                r["id"] = dv_id
                                if r.get("name") == "indexpattern-datasource-current-indexpattern":
                                    changed = True
                        # Ensure current-indexpattern exists
                        if not any((r.get("type") == "index-pattern" and r.get("name") == "indexpattern-datasource-current-indexpattern") for r in refs):
                            refs.append({
                                "type": "index-pattern",
                                "name": "indexpattern-datasource-current-indexpattern",
                                "id": "metricbeat_metrics" if str(lid).startswith("metrics_") else "python_obs_control_logs",
                            })
                            changed = True
                        if changed:
                            body = json.dumps({"attributes": attrs, "references": refs})
                            ur = requests.put(f"{base}/api/saved_objects/lens/{lid}", headers=headers, data=body, timeout=30)
                            if not (200 <= ur.status_code < 300):
                                _log.warning("kibana lens sweep post-fix failed for %s: %s %s", lid, ur.status_code, ur.text)
            except Exception as _exc2:  # noqa: BLE001
                _log.warning("kibana lens sweep post-fix error: %s", _exc2)
        except Exception as exc2:  # noqa: BLE001
            _log.warning("kibana post-fix skipped/failed: %s", exc2)

        _log.info("kibana ndjson import completed")
    except Exception as exc:  # noqa: BLE001
        _log.warning("kibana import failed: %s", exc)


