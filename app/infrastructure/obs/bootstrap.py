from __future__ import annotations

from typing import Iterable
from pathlib import Path
import logging

from app.obs_client import obs_manager


STANDARD_SCENES: list[str] = [
    "Home",
    "ReferenceSearch",
    "LiveFront",
    "LiveSide",
    "LiveRear",
    "Relax",
    "YouTube",
    "Reels",
    "ProcedureBeforeFront",
    "ProcedureBeforeSide",
    "ProcedureBeforeRear",
    "ProcedureAfterFront",
    "ProcedureAfterSide",
    "ProcedureAfterRear",
    "LiveThreeWay",
]

STANDARD_SOURCES: list[str] = [
    "cam_front",
    "cam_side",
    "cam_rear",
    "img_before_front",
    "img_before_side",
    "img_before_rear",
]


async def _list_scene_names() -> set[str]:
    data = await obs_manager.get_scenes()
    names: set[str] = set()
    for s in data:
        name = s.get("sceneName") or s.get("scene_name") or s.get("name")
        if name:
            names.add(str(name))
    return names


async def ensure_scenes_exist(names: Iterable[str]) -> None:
    existing = await _list_scene_names()
    client = await obs_manager.connect()
    for name in names:
        if name in existing:
            continue
        # create empty scene if not exists
        create = getattr(client, "create_scene", None)
        if create is not None:
            await obs_manager._to_thread(create, name)  # type: ignore[attr-defined]


async def ensure_input_exists(input_name: str, kind: str) -> None:
    client = await obs_manager.connect()
    get = getattr(client, "get_input_list", None)
    add = getattr(client, "create_input", None)
    if get is None or add is None:
        return
    inputs = await obs_manager._to_thread(get)
    names = {i.get("inputName") or i.get("input_name") or i.get("name") for i in getattr(inputs, "inputs", [])}
    if input_name in names:
        return
    settings: dict = {}
    if kind == "image_source":
        settings = {"file": ""}
    await obs_manager._to_thread(add, "Home", input_name, kind, settings, False)


async def wire_default_layout() -> None:
    # Minimal: ensure standard scenes exist. Wiring sources to scenes is project-specific; we keep it conservative.
    await ensure_scenes_exist(STANDARD_SCENES)
    # Optionally ensure default inputs exist (commented kinds depend on OS/OBS):
    # await ensure_input_exists("cam_front", "dshow_input")
    # await ensure_input_exists("cam_side", "dshow_input")
    # await ensure_input_exists("cam_rear", "dshow_input")
    # await ensure_input_exists("img_before_front", "image_source")
    # await ensure_input_exists("img_before_side", "image_source")
    # await ensure_input_exists("img_before_rear", "image_source")
    try:
        await _apply_default_asset_images()
    except Exception as exc:
        logging.getLogger(__name__).warning("apply default asset images skipped: %s", exc)


async def _apply_default_asset_images() -> None:
    """
    Ensure specific image inputs point to our repo's assets by default:
      - img_cam_bg -> assets/image/cam-bg.png
      - img_ba_frame -> assets/image/frame-beforeafter.png
      - img_mac_wireframe -> assets/image/mac-wireframe.png

    If inputs are missing, they will be created as image_source under 'Home' scene.
    File paths are resolved relative to repository root to be robust regardless of CWD.
    """
    # Resolve repo root and assets dir robustly
    try:
        repo_root = Path(__file__).resolve().parents[3]
    except Exception:
        repo_root = Path.cwd()
    assets_dir = repo_root / "assets" / "image"
    if not assets_dir.exists():
        # Fallback to CWD relative
        assets_dir = Path("assets") / "image"

    mapping: dict[str, Path] = {
        "img_cam_bg": assets_dir / "cam-bg.png",
        "img_ba_frame": assets_dir / "frame-beforeafter.png",
        "img_mac_wireframe": assets_dir / "mac-wireframe.png",
    }

    client = await obs_manager.connect()
    get_inputs = getattr(client, "get_input_list", None)
    create_input = getattr(client, "create_input", None)
    if get_inputs is None or create_input is None:
        return
    inputs = await obs_manager._to_thread(get_inputs)
    existing = {i.get("inputName") or i.get("input_name") or i.get("name") for i in getattr(inputs, "inputs", [])}

    for input_name, file_path in mapping.items():
        try:
            if not file_path.exists():
                continue
            # Create missing image_source
            if input_name not in existing:
                await obs_manager._to_thread(create_input, "Home", input_name, "image_source", {"file": str(file_path)}, False)
                existing.add(input_name)
            # Update file path
            await obs_manager.set_input_settings(input_name, {"file": str(file_path)}, False)
        except Exception as exc:
            logging.getLogger(__name__).warning("failed to set asset for %s: %s", input_name, exc)
