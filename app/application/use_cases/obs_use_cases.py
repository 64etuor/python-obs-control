from __future__ import annotations

from dataclasses import dataclass

from app.domain.ports.obs_service import IObsService


@dataclass(slots=True)
class GetObsVersion:
    svc: IObsService

    async def __call__(self) -> dict:
        return await self.svc.get_version()


@dataclass(slots=True)
class ListScenes:
    svc: IObsService

    async def __call__(self) -> list[dict]:
        return await self.svc.get_scenes()


@dataclass(slots=True)
class SetScene:
    svc: IObsService

    async def __call__(self, scene_name: str) -> None:
        await self.svc.set_current_scene(scene_name)


@dataclass(slots=True)
class TakeScreenshot:
    svc: IObsService

    async def __call__(
        self,
        *,
        source_name: str,
        image_file_path: str,
        image_format: str = "png",
        image_width: int | None = None,
        image_height: int | None = None,
        image_compression_quality: int = 100,
        image_input_update: str | None = None,
    ) -> dict:
        saved = await self.svc.save_source_screenshot(
            source_name=source_name,
            image_file_path=image_file_path,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height,
            image_compression_quality=image_compression_quality,
        )
        if image_input_update:
            await self.svc.update_image_source_file(image_input_update, saved)
        return {"path": saved, "updated_input": image_input_update or None}


@dataclass(slots=True)
class StartStream:
    svc: IObsService

    async def __call__(self) -> None:
        await self.svc.start_streaming()


@dataclass(slots=True)
class StopStream:
    svc: IObsService

    async def __call__(self) -> None:
        await self.svc.stop_streaming()


@dataclass(slots=True)
class ToggleStream:
    svc: IObsService

    async def __call__(self) -> None:
        await self.svc.toggle_streaming()
