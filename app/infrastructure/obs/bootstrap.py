from __future__ import annotations

from typing import Iterable

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
