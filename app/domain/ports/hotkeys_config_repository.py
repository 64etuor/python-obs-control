from __future__ import annotations

from typing import Protocol, Dict, Any


class IHotkeysConfigRepository(Protocol):
    def load(self) -> Dict[str, Any]:
        ...

    def save(self, cfg: Dict[str, Any]) -> None:
        ...


