from __future__ import annotations

import asyncio
from typing import Set

from fastapi import WebSocket

from app.domain.ports.notification_service import INotificationService


class OverlayNotificationService(INotificationService):
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)

    async def unregister(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def publish(self, event: dict) -> None:
        # broadcast without failing the caller
        async with self._lock:
            clients = list(self._clients)
        to_drop: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_json(event)
            except Exception:
                to_drop.append(ws)
        if to_drop:
            async with self._lock:
                for ws in to_drop:
                    self._clients.discard(ws)

    async def publish_toast(self, message: str, *, level: str = "info", timeout_ms: int = 2000) -> None:
        await self.publish({"type": "toast", "message": message, "level": level, "timeout_ms": timeout_ms})


# singleton instance for app wiring
overlay_notifications = OverlayNotificationService()


