from __future__ import annotations

from app.domain.ports.obs_service import IObsService
from app.obs_client import obs_manager


class ObsService(IObsService):
    async def get_version(self) -> dict:
        return await obs_manager.get_version()

    async def get_scenes(self) -> list[dict]:
        return await obs_manager.get_scenes()

    async def set_current_scene(self, scene_name: str) -> None:
        await obs_manager.set_current_scene(scene_name)

    async def save_source_screenshot(
        self,
        source_name: str,
        image_file_path: str,
        image_format: str = "png",
        image_width: int | None = None,
        image_height: int | None = None,
        image_compression_quality: int = 100,
    ) -> str:
        return await obs_manager.save_source_screenshot(
            source_name=source_name,
            image_file_path=image_file_path,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height,
            image_compression_quality=image_compression_quality,
        )

    async def set_input_settings(self, input_name: str, input_settings: dict, overlay: bool = False) -> None:
        await obs_manager.set_input_settings(input_name, input_settings, overlay)

    async def update_image_source_file(self, image_input_name: str, new_file_path: str) -> None:
        await obs_manager.update_image_source_file(image_input_name, new_file_path)

    async def start_streaming(self) -> None:
        await obs_manager.start_streaming()

    async def stop_streaming(self) -> None:
        await obs_manager.stop_streaming()

    async def get_stream_status(self) -> dict:
        return await obs_manager.get_stream_status()

    async def toggle_streaming(self) -> None:
        await obs_manager.toggle_streaming()
