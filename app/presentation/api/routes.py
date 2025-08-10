from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.container import (
    get_obs_version,
    list_scenes,
    set_scene as uc_set_scene,
    take_screenshot as uc_take_screenshot,
    start_stream as uc_start_stream,
    stop_stream as uc_stop_stream,
)
from app.utils.screenshot import build_screenshot_path

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/obs/version")
async def obs_version() -> dict:
    try:
        return await get_obs_version()()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/obs/scenes")
async def obs_scenes() -> dict:
    try:
        scenes = await list_scenes()()
        return {"scenes": scenes}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/scene/{scene_name}")
async def set_scene(scene_name: str) -> dict:
    try:
        await uc_set_scene()(scene_name)
        return {"ok": True, "scene": scene_name}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/screenshot")
async def take_screenshot(
    source_name: str,
    image_file_path: str,
    image_format: str = "png",
    image_width: int | None = None,
    image_height: int | None = None,
    image_compression_quality: int = 100,
    image_input_update: str | None = None,
) -> dict:
    try:
        return await uc_take_screenshot()(
            source_name=source_name,
            image_file_path=image_file_path,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height,
            image_compression_quality=image_compression_quality,
            image_input_update=image_input_update,
        )
    except Exception as exc:  # noqa: BLE001
        s = str(exc)
        if "702" in s or "render screenshot" in s.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. 소스명이 정확한지, 소스가 현재 활성/렌더 상태인지 확인. "
                    "필요하면 width/height 지정 혹은 다른 포맷을 시도하세요."
                ),
            )
        if "imageWidth" in s and "minimum" in s:
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. width/height 최소값(>=8)을 지정하세요. 예: image_width=1920&image_height=1080"
                ),
            )
        if "code 600" in s or "directory for your file path does not exist" in s.lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. 저장 경로의 디렉토리가 존재하지 않습니다. 전체 경로가 유효한지 확인하세요."
                ),
            )
        raise HTTPException(status_code=500, detail=str(exc))


# Dedicated helpers

@router.post("/obs/screenshot/front")
async def screenshot_front(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_before_front",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_front", image_format=image_format)
    return await take_screenshot(
        source_name="cam_front",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/side")
async def screenshot_side(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_before_side",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_side", image_format=image_format)
    return await take_screenshot(
        source_name="cam_side",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )


@router.post("/obs/screenshot/rear")
async def screenshot_rear(
    image_file_path: str | None = None,
    image_format: str = "png",
    image_width: int | None = 1080,
    image_height: int | None = 1920,
    image_compression_quality: int = 100,
    image_input_update: str | None = "img_before_rear",
) -> dict:
    if not image_file_path:
        image_file_path = build_screenshot_path("cam_rear", image_format=image_format)
    return await take_screenshot(
        source_name="cam_rear",
        image_file_path=image_file_path,
        image_format=image_format,
        image_width=image_width,
        image_height=image_height,
        image_compression_quality=image_compression_quality,
        image_input_update=image_input_update,
    )
