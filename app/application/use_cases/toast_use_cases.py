from __future__ import annotations

from dataclasses import dataclass

from app.domain.ports.notification_service import INotificationService


@dataclass(slots=True)
class ToastSuccess:
    svc: INotificationService

    async def __call__(self, message: str, timeout_ms: int = 2000) -> None:
        await self.svc.publish_toast(message, level="success", timeout_ms=timeout_ms)


@dataclass(slots=True)
class ToastInfo:
    svc: INotificationService

    async def __call__(self, message: str, timeout_ms: int = 2000) -> None:
        await self.svc.publish_toast(message, level="info", timeout_ms=timeout_ms)


@dataclass(slots=True)
class ToastWarning:
    svc: INotificationService

    async def __call__(self, message: str, timeout_ms: int = 2500) -> None:
        await self.svc.publish_toast(message, level="warning", timeout_ms=timeout_ms)


@dataclass(slots=True)
class ToastError:
    svc: INotificationService

    async def __call__(self, message: str, timeout_ms: int = 3000) -> None:
        await self.svc.publish_toast(message, level="error", timeout_ms=timeout_ms)


