from __future__ import annotations

import platform
import re
import shutil
import subprocess
from typing import List

from .dshow_enum import list_dshow_devices, list_dshow_devices_detailed


def list_video_devices() -> list[str]:
    if platform.system().lower() != "windows":
        return []

    dshow = list_dshow_devices()
    if dshow:
        return dshow

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return []
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-f", "dshow", "-list_devices", "true", "-i", "dummy"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = proc.stderr or proc.stdout or ""
        devices: List[str] = []
        in_video_section = False
        for line in out.splitlines():
            if "DirectShow video devices" in line:
                in_video_section = True
                continue
            if in_video_section and "DirectShow audio devices" in line:
                break
            if in_video_section:
                m = re.search(r'\"(.+?)\"', line)
                if m:
                    devices.append(m.group(1))
        return devices
    except Exception:
        return []


def list_video_devices_detailed() -> dict:
    if platform.system().lower() != "windows":
        return {"devices": [], "method": "none"}
    det = list_dshow_devices_detailed()
    if det:
        return {"devices": det, "method": "dshow-com"}
    return {"devices": [], "method": "none"}
