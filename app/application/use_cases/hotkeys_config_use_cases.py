from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from app.domain.ports.hotkeys_config_repository import IHotkeysConfigRepository


@dataclass(slots=True)
class GetHotkeysConfig:
    repo: IHotkeysConfigRepository

    def __call__(self) -> Dict[str, Any]:
        return self.repo.load()


@dataclass(slots=True)
class SaveHotkeysConfig:
    repo: IHotkeysConfigRepository

    def __call__(self, cfg: Dict[str, Any]) -> None:
        self.repo.save(cfg)


