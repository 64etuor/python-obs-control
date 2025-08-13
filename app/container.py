from __future__ import annotations

from functools import lru_cache

from app.infrastructure.obs.obs_service_impl import ObsService
from app.infrastructure.overlay.notification_service_impl import overlay_notifications
from app.infrastructure.overlay.discord_alert_service import DiscordAlertService
from app.domain.ports.notification_service import INotificationService
from app.domain.ports.alert_service import IAlertService
from app.application.use_cases.obs_use_cases import (
    GetObsVersion,
    ListScenes,
    SetScene,
    TakeScreenshot,
    StartStream,
    StopStream,
    ToggleStream,
)
from app.application.use_cases.toast_use_cases import ToastSuccess, ToastInfo, ToastError, ToastWarning
from app.application.use_cases.hotkeys_config_use_cases import GetHotkeysConfig, SaveHotkeysConfig
from app.infrastructure.config.hotkeys_config import FileHotkeysConfigRepository
from app.application.use_cases.camera_use_cases import (
    ListCameraDevices,
    GetCameraConfig,
    ApplyCameraConfig,
)


@lru_cache(maxsize=1)
def obs_service() -> ObsService:
    return ObsService()


@lru_cache(maxsize=1)
def notification_service() -> INotificationService:
    return overlay_notifications


@lru_cache(maxsize=1)
def alert_service() -> IAlertService:
    return DiscordAlertService()

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


# Toast use-cases
@lru_cache(maxsize=None)
def toast_success() -> ToastSuccess:
    return ToastSuccess(svc=notification_service())


@lru_cache(maxsize=None)
def toast_info() -> ToastInfo:
    return ToastInfo(svc=notification_service())


@lru_cache(maxsize=None)
def toast_warning() -> ToastWarning:
    return ToastWarning(svc=notification_service())


@lru_cache(maxsize=None)
def toast_error() -> ToastError:
    return ToastError(svc=notification_service())


# Hotkeys config use-cases
@lru_cache(maxsize=1)
def hotkeys_repo() -> FileHotkeysConfigRepository:
    return FileHotkeysConfigRepository()


@lru_cache(maxsize=None)
def get_hotkeys_config() -> GetHotkeysConfig:
    return GetHotkeysConfig(repo=hotkeys_repo())


@lru_cache(maxsize=None)
def save_hotkeys_config() -> SaveHotkeysConfig:
    return SaveHotkeysConfig(repo=hotkeys_repo())
