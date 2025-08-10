from fastapi import APIRouter, HTTPException

from .obs_client import obs_manager


router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/obs/version")
async def obs_version() -> dict:
    try:
        return await obs_manager.get_version()
    except Exception as exc:  # noqa: BLE001 - surface to client for now
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/obs/scenes")
async def obs_scenes() -> dict:
    try:
        scenes = await obs_manager.get_scenes()
        return {"scenes": scenes}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/scene/{scene_name}")
async def set_scene(scene_name: str) -> dict:
    try:
        await obs_manager.set_current_scene(scene_name)
        return {"ok": True}
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
        saved = await obs_manager.save_source_screenshot(
            source_name=source_name,
            image_file_path=image_file_path,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height,
            image_compression_quality=image_compression_quality,
        )
        if image_input_update:
            await obs_manager.update_image_source_file(image_input_update, saved)
        return {"path": saved, "updated_input": image_input_update or None}
    except Exception as exc:  # noqa: BLE001
        if "702" in str(exc) or "render screenshot" in str(exc).lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. 소스명이 정확한지, 소스가 현재 활성/렌더 상태인지 확인. "
                    "필요하면 width/height 지정 혹은 다른 포맷을 시도하세요."
                ),
            )
        if "imageWidth" in str(exc) and "minimum" in str(exc):
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. width/height 최소값(>=8)을 지정하세요. 예: image_width=1920&image_height=1080"
                ),
            )
        if "code 600" in str(exc) or "directory for your file path does not exist" in str(exc).lower():
            raise HTTPException(
                status_code=400,
                detail=(
                    "스크린샷 실패. 저장 경로의 디렉토리가 존재하지 않습니다. 전체 경로가 유효한지 확인하세요."
                ),
            )
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/stream/start")
async def start_stream() -> dict:
    try:
        await obs_manager.start_streaming()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/obs/stream/stop")
async def stop_stream() -> dict:
    try:
        await obs_manager.stop_streaming()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

