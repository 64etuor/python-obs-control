from __future__ import annotations

from typing import Protocol, Optional, Mapping, Any


class IAlertService(Protocol):
    def notify_incident(self, message: str, *, level: str = "CRITICAL", context: Optional[Mapping[str, Any]] = None) -> None:  # noqa: D401
        """Send a high-priority incident notification.

        Implementations must be non-blocking or very fast; heavy work should be offloaded.
        """
        ...


