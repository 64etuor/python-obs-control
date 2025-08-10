from __future__ import annotations

from functools import lru_cache

from app.infrastructure.obs.obs_service_impl import ObsService
from app.application.use_cases.obs_use_cases import (
    GetObsVersion,
    ListScenes,
    SetScene,
    TakeScreenshot,
    StartStream,
    StopStream,
    ToggleStream,
)
from app.application.use_cases.camera_use_cases import (
    ListCameraDevices,
    GetCameraConfig,
    ApplyCameraConfig,
)


@lru_cache(maxsize=1)
def obs_service() -> ObsService:
    return ObsService()


@lru_cache(maxsize=None)
def get_obs_version() -> GetObsVersion:
    return GetObsVersion(svc=obs_service())


@lru_cache(maxsize=None)
def list_scenes() -> ListScenes:
    return ListScenes(svc=obs_service())


@lru_cache(maxsize=None)
def set_scene() -> SetScene:
    return SetScene(svc=obs_service())


@lru_cache(maxsize=None)
def take_screenshot() -> TakeScreenshot:
    return TakeScreenshot(svc=obs_service())


@lru_cache(maxsize=None)
def start_stream() -> StartStream:
    return StartStream(svc=obs_service())


@lru_cache(maxsize=None)
def stop_stream() -> StopStream:
    return StopStream(svc=obs_service())


@lru_cache(maxsize=None)
def toggle_stream() -> ToggleStream:
    return ToggleStream(svc=obs_service())


@lru_cache(maxsize=None)
def list_camera_devices() -> ListCameraDevices:
    return ListCameraDevices()


@lru_cache(maxsize=None)
def get_camera_config() -> GetCameraConfig:
    return GetCameraConfig()


@lru_cache(maxsize=None)
def apply_camera_config() -> ApplyCameraConfig:
    return ApplyCameraConfig()
