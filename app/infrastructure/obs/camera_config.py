from __future__ import annotations

from typing import Optional, List, Dict, Tuple

from app.obs_client import obs_manager

CAM_INPUTS = {
    "front": "cam_front",
    "side": "cam_side",
    "rear": "cam_rear",
}

DSHOW_KIND = "dshow_input"


async def _pick_scene_for_new_input() -> str:
    scenes = await obs_manager.get_scenes()
    for preferred in ("Home", "LiveFront", "LiveSide", "LiveRear"):
        if any((s.get("sceneName") or s.get("name")) == preferred for s in scenes):
            return preferred
    if scenes:
        name = scenes[0].get("sceneName") or scenes[0].get("name") or "Home"
        return str(name)
    return "Home"


async def _ensure_input_exists(input_name: str, kind: str = DSHOW_KIND) -> None:
    client = await obs_manager.connect()
    get_list = getattr(client, "get_input_list", None)
    add = getattr(client, "create_input", None)
    if get_list is None or add is None:
        return
    lst = await obs_manager._to_thread(get_list)
    inputs = getattr(lst, "inputs", [])
    names = {i.get("inputName") or i.get("name") for i in inputs}
    if input_name in names:
        return
    scene_name = await _pick_scene_for_new_input()
    await obs_manager._to_thread(add, scene_name, input_name, kind, {}, False)


async def _get_input_settings(input_name: str) -> dict:
    client = await obs_manager.connect()
    get_settings = getattr(client, "get_input_settings", None)
    if get_settings is None:
        return {}
    resp = await obs_manager._to_thread(get_settings, input_name)
    return getattr(resp, "inputSettings", None) or getattr(resp, "datain", {}).get("inputSettings", {})


async def list_dshow_devices_via_obs(input_name: str = "cam_front") -> list[dict]:
    await _ensure_input_exists(input_name, DSHOW_KIND)
    client = await obs_manager.connect()
    fn = getattr(client, "get_input_properties_list_property_items", None)
    if fn is None:
        return []
    try:
        resp = await obs_manager._to_thread(fn, input_name, "video_device_id")
        lst = getattr(resp, "propertyItems", None) or getattr(resp, "datain", {}).get("propertyItems", [])
        items: list[dict] = []
        for it in lst or []:
            name = it.get("itemName") or it.get("name")
            value = it.get("itemValue") or it.get("value")
            if name is None or value is None:
                continue
            items.append({"name": str(name), "value": str(value)})
        return items
    except Exception:
        # code 600 등은 빈 목록 반환
        return []


def _extract_device_from_settings(settings: dict) -> Optional[str]:
    for key in ("video_device_id", "device_id", "device_name", "video_device"):
        val = settings.get(key)
        if val:
            return str(val)
    return None


async def get_camera_config() -> dict:
    client = await obs_manager.connect()
    get_list = getattr(client, "get_input_list", None)
    names = set()
    if get_list is not None:
        lst = await obs_manager._to_thread(get_list)
        names = {i.get("inputName") or i.get("name") for i in getattr(lst, "inputs", [])}
    result = {"front": None, "side": None, "rear": None}
    for key, input_name in CAM_INPUTS.items():
        if names and input_name not in names:
            continue
        settings = await _get_input_settings(input_name)
        result[key] = _extract_device_from_settings(settings or {})
    return result


async def _resolve_to_obs_value(input_name: str, user_value: str) -> str:
    items = await list_dshow_devices_via_obs(input_name)
    for it in items:
        if str(it.get("value")) == str(user_value):
            return str(user_value)
    for it in items:
        if str(it.get("name")) == str(user_value):
            return str(it.get("value"))
    return user_value


async def set_camera_config(front: Optional[str] = None, side: Optional[str] = None, rear: Optional[str] = None) -> dict:
    client = await obs_manager.connect()
    set_settings = getattr(client, "set_input_settings", None)
    if set_settings is None:
        raise RuntimeError("OBS client does not support set_input_settings")

    out: Dict[str, Optional[str]] = {}

    async def _apply(pos: str, device_value: Optional[str]):
        if device_value is None:
            out[pos] = None
            return
        input_name = CAM_INPUTS[pos]
        await _ensure_input_exists(input_name)
        resolved = await _resolve_to_obs_value(input_name, device_value)
        for overlay in (True, False):
            for key in ("video_device_id", "device_id", "video_device", "device_name"):
                try:
                    await obs_manager._to_thread(set_settings, input_name, {key: resolved}, overlay)
                    out[pos] = resolved
                    return
                except Exception:
                    continue
        raise RuntimeError(f"Failed to set device for {input_name}: {device_value}")

    if front is not None:
        await _apply("front", front)
    if side is not None:
        await _apply("side", side)
    if rear is not None:
        await _apply("rear", rear)

    return out
