from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.infrastructure.devices.enumerate import list_video_devices, list_video_devices_detailed
from app.infrastructure.obs.camera_config import get_camera_config, set_camera_config


@dataclass(slots=True)
class ListCameraDevices:
    async def __call__(self) -> dict:
        return {
            "devices": list_video_devices(),
            "detail": list_video_devices_detailed(),
        }


@dataclass(slots=True)
class GetCameraConfig:
    async def __call__(self) -> dict:
        return await get_camera_config()


@dataclass(slots=True)
class ApplyCameraConfig:
    async def __call__(self, *, front: Optional[str], side: Optional[str], rear: Optional[str]) -> dict:
        return await set_camera_config(front=front, side=side, rear=rear)
