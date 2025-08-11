from __future__ import annotations

from typing import Optional, List, Dict, Tuple
import platform

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


async def _recreate_input_with_device(input_name: str, device_moniker_or_name: str) -> None:
    client = await obs_manager.connect()
    remove = getattr(client, "remove_input", None)
    add = getattr(client, "create_input", None)
    if add is None:
        return
    # Remove existing if possible to avoid name collision
    if remove is not None:
        try:
            await obs_manager._to_thread(remove, input_name)
        except Exception:
            pass
    scene_name = await _pick_scene_for_new_input()
    settings: dict = {}
    if _looks_like_moniker(device_moniker_or_name):
        settings = {"device_id": device_moniker_or_name}
    else:
        settings = {"device_name": device_moniker_or_name}
    await obs_manager._to_thread(add, scene_name, input_name, DSHOW_KIND, settings, False)


async def _ensure_input_exists(input_name: str, kind: str = DSHOW_KIND) -> None:
    client = await obs_manager.connect()
    get_list = getattr(client, "get_input_list", None)
    add = getattr(client, "create_input", None)
    remove = getattr(client, "remove_input", None)
    if get_list is None or add is None:
        return
    lst = await obs_manager._to_thread(get_list)
    inputs = getattr(lst, "inputs", [])
    target = None
    for i in inputs:
        name = i.get("inputName") or i.get("name")
        if name == input_name:
            target = i
            break
    if target is not None:
        existing_kind = target.get("inputKind") or target.get("kind") or target.get("input_kind")
        if existing_kind == kind:
            return
        # Recreate with desired kind if mismatched
        if remove is not None:
            try:
                await obs_manager._to_thread(remove, input_name)
            except Exception:
                pass
    scene_name = await _pick_scene_for_new_input()
    await obs_manager._to_thread(add, scene_name, input_name, kind, {}, False)


async def _get_input_settings(input_name: str) -> dict:
    client = await obs_manager.connect()
    get_settings = getattr(client, "get_input_settings", None)
    if get_settings is None:
        return {}
    resp = await obs_manager._to_thread(get_settings, input_name)
    return getattr(resp, "inputSettings", None) or getattr(resp, "datain", {}).get("inputSettings", {})


def _looks_like_moniker(value: str) -> bool:
    v = str(value or "")
    return (
        "@device:pnp" in v
        or "#vid_" in v.lower()
        or "#pid_" in v.lower()
        or ("\\\\?\\" in v)  # Windows PnP path escape
    )


def _resolve_local_dshow_moniker_by_label(user_label: str) -> Optional[str]:
    if platform.system().lower() != "windows":
        return None
    try:
        from app.infrastructure.devices.dshow_enum import list_dshow_devices_detailed
    except Exception:
        return None

    try:
        det = list_dshow_devices_detailed()
    except Exception:
        det = []

    import re

    def normalize(s: str) -> str:
        base = re.sub(r"\s*\([^)]*\)\s*$", "", s or "")
        return re.sub(r"\s+", " ", base).strip().lower()

    tokens: list[str] = []
    for m in re.finditer(r"\(([0-9a-fA-F]{3,8})\)", str(user_label)):
        tok = m.group(1).lower()
        tokens.append(tok)
        if re.fullmatch(r"[0-9]{3,8}", tok):
            try:
                dec = int(tok, 10)
                hx = f"{dec:04x}"
                if hx not in tokens:
                    tokens.append(hx)
            except Exception:
                pass

    # 1) token-in-path match first
    if tokens:
        for d in det or []:
            path = str(d.get("path") or "").lower()
            if path and any(tok in path for tok in tokens):
                return str(d.get("path"))

    # 2) normalized friendly-name exact
    uv = normalize(str(user_label))
    for d in det or []:
        nm = str(d.get("name") or "")
        if nm and normalize(nm) == uv:
            return str(d.get("path"))

    # 3) contains
    for d in det or []:
        nm = str(d.get("name") or "")
        if not nm:
            continue
        nn = normalize(nm)
        if uv and (uv in nn or nn in uv):
            return str(d.get("path"))

    return None


async def list_dshow_devices_via_obs(input_name: str = "cam_front") -> list[dict]:
    # 안정성을 위해 OBS PropertyItems API 사용을 피한다(code 600 회피)
    # 로컬 DirectShow COM 열거 결과를 name/value(=moniker path)로 반환
    try:
        from app.infrastructure.devices.dshow_enum import list_dshow_devices_detailed  # lazy import

        det = list_dshow_devices_detailed()
        items: list[dict] = []
        for d in det or []:
            name = d.get("name")
            path = d.get("path")
            if name and path:
                items.append({"name": str(name), "value": str(path)})
        return items
    except Exception:
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
    # Short-circuit: if caller already passed a moniker/path, use it as-is
    if _looks_like_moniker(user_value):
        return str(user_value)

    # Prefer local mapping on Windows to avoid OBS property list API flakiness
    local_moniker = _resolve_local_dshow_moniker_by_label(user_value)
    if local_moniker:
        return local_moniker

    # As a fallback, try via OBS property list (may fail with code 600 on some builds)
    items = await list_dshow_devices_via_obs(input_name)

    # 1) exact match on OBS raw value
    for it in items:
        if str(it.get("value")) == str(user_value):
            return str(user_value)

    # 2) if user label contains an identifier in parentheses (e.g., "(1bcf)" or "(3564)"),
    #    try to match that token within the OBS device value (moniker often contains vid/pid).
    #    For decimal tokens (e.g., 3564), also try the zero-padded 4-digit hex form (e.g., 0x0DEC -> "0dec").
    import re

    tokens: list[str] = []
    for m in re.finditer(r"\(([0-9a-fA-F]{3,8})\)", str(user_value)):
        tok = m.group(1).lower()
        tokens.append(tok)
        # if purely decimal and length 3-8, also push hex variant
        if re.fullmatch(r"[0-9]{3,8}", tok):
            try:
                dec = int(tok, 10)
                hx = f"{dec:04x}"
                if hx not in tokens:
                    tokens.append(hx)
            except Exception:
                pass
    if tokens:
        for it in items:
            v = str(it.get("value") or "").lower()
            if any(tok in v for tok in tokens):
                return str(it.get("value"))

    # 3) normalize and try matching against item names (browser/OS may append identifiers like " (1bcf)")
    def normalize_label(s: str) -> str:
        base = re.sub(r"\s*\([^)]*\)\s*$", "", s or "")  # drop trailing parenthesis group
        return re.sub(r"\s+", " ", base).strip().lower()

    uv_norm = normalize_label(str(user_value))
    for it in items:
        name = str(it.get("name") or "")
        if not name:
            continue
        if normalize_label(name) == uv_norm:
            return str(it.get("value"))

    # 4) fuzzy contains match as last resort
    for it in items:
        name = str(it.get("name") or "")
        if not name:
            continue
        n_norm = normalize_label(name)
        if uv_norm and (uv_norm in n_norm or n_norm in uv_norm):
            return str(it.get("value"))

    # 5) fall back to original; OBS may still accept friendly names on some platforms
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
        # Strip trailing parenthesis token from resolved if it leaked through
        import re as _re
        if resolved and _re.search(r"\([^)]*\)$", str(resolved)):
            cleaned = _re.sub(r"\s*\([^)]*\)\s*$", "", str(resolved)).strip()
            if cleaned:
                resolved = cleaned
        # Apply with strong preference for moniker id first, then name
        import re as _re2
        friendly = _re2.sub(r"\s*\([^)]*\)\s*$", "", str(resolved)).strip()

        payloads = []
        if _looks_like_moniker(resolved):
            # First, try with pure moniker values
            payloads.extend([
                {"device_id": resolved},
                {"video_device_id": resolved},
            ])
            # If we have a friendly name, also try pairing it with moniker
            if friendly:
                payloads.extend([
                    {"device_id": resolved, "device_name": friendly},
                    {"video_device_id": resolved, "device_name": friendly},
                ])

        # Always include a stripped friendly name attempt as well
        if friendly:
            payloads.extend([
                {"device_name": friendly},
                {"video_device": friendly},
            ])

        for overlay in (True, False):
            for payload in payloads:
                try:
                    await obs_manager._to_thread(set_settings, input_name, payload, overlay)
                    out[pos] = resolved
                    return
                except Exception:
                    continue
        # As last resort, recreate the input with initial settings
        try:
            await _recreate_input_with_device(input_name, resolved)
            out[pos] = resolved
            return
        except Exception:
            pass
        raise RuntimeError(f"Failed to set device for {input_name}: {device_value}")

    if front is not None:
        await _apply("front", front)
    if side is not None:
        await _apply("side", side)
    if rear is not None:
        await _apply("rear", rear)

    return out
