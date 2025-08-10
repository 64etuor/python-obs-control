from __future__ import annotations

from typing import Protocol, TypedDict, Literal


class ToastEvent(TypedDict, total=False):
    type: Literal["toast"]
    message: str
    level: Literal["info", "success", "warning", "error"]
    timeout_ms: int


class INotificationService(Protocol):
    async def publish(self, event: dict) -> None: ...

    async def publish_toast(
        self,
        message: str,
        *,
        level: Literal["info", "success", "warning", "error"] = "info",
        timeout_ms: int = 2000,
    ) -> None: ...


