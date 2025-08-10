from __future__ import annotations

from typing import List, Dict


def list_dshow_devices() -> list[str]:
    try:
        import comtypes.client  # type: ignore
        from comtypes.gen import DirectShowLib as dsl  # type: ignore
    except Exception:
        return []

    try:
        sys_dev_enum = comtypes.client.CreateObject(dsl.CreateDevEnum)
        enum_cat = sys_dev_enum.CreateClassEnumerator(dsl.VideoInputDeviceCategory, 0)
        if not enum_cat:
            return []
        devices: List[str] = []
        monikers = enum_cat
        while True:
            moniker = monikers.Next()
            if not moniker:
                break
            try:
                prop_bag = moniker.BindToStorage(None, None, dsl.IPropertyBag._iid_)
                name = prop_bag.Read("FriendlyName")
                if name:
                    devices.append(str(name))
            except Exception:
                pass
        return devices
    except Exception:
        return []


def list_dshow_devices_detailed() -> list[Dict[str, str]]:
    try:
        import comtypes.client  # type: ignore
        from comtypes.gen import DirectShowLib as dsl  # type: ignore
        from comtypes import GUID  # type: ignore
    except Exception:
        return []

    try:
        sys_dev_enum = comtypes.client.CreateObject(dsl.CreateDevEnum)
        enum_cat = sys_dev_enum.CreateClassEnumerator(dsl.VideoInputDeviceCategory, 0)
        if not enum_cat:
            return []
        items: list[Dict[str, str]] = []
        monikers = enum_cat
        while True:
            moniker = monikers.Next()
            if not moniker:
                break
            try:
                prop_bag = moniker.BindToStorage(None, None, dsl.IPropertyBag._iid_)
                name = prop_bag.Read("FriendlyName")
                display = moniker.GetDisplayName(None, None)
                items.append({"name": str(name or ""), "path": str(display or "")})
            except Exception:
                continue
        return items
    except Exception:
        return []
