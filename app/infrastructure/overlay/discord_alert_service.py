from __future__ import annotations

import threading
import json
import os
from typing import Mapping, Any, Optional

import requests

from app.domain.ports.alert_service import IAlertService


class DiscordAlertService(IAlertService):
    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self._url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL") or ""

    def notify_incident(self, message: str, *, level: str = "CRITICAL", context: Optional[Mapping[str, Any]] = None) -> None:
        if not self._url:
            return
        payload = {
            "content": None,
            "embeds": [
                {
                    "title": f"[{level}] python-obs-control",
                    "description": str(message)[:4000],
                    "color": 0xE11D48 if str(level).upper() in {"CRITICAL", "ERROR"} else 0xF59E0B,
                    "fields": [
                        {"name": k, "value": "```json\n" + json.dumps(v, ensure_ascii=False, indent=2)[:1000] + "\n```", "inline": False}
                        for k, v in (context or {}).items()
                    ],
                }
            ],
        }

        def _send() -> None:
            try:
                requests.post(self._url, json=payload, timeout=5)
            except Exception:
                pass

        threading.Thread(target=_send, name="discord-alert", daemon=True).start()


