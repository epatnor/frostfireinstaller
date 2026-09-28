"""Host detection: distro, atomic, session, GPU."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class HostInfo:
    distro: str
    atomic: bool
    session: str
    desktop: str
    kernel: str
    gpu: str | None


def _os_release() -> str:
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


def _nvidia() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.stdout.strip().splitlines()
    if not lines:
        return None
    name, _, driver = lines[0].partition(",")
    clean = name.strip().removeprefix("NVIDIA ").removesuffix(" Laptop GPU")
    return f"{clean} ({driver.strip()})" if driver.strip() else clean


def _pci() -> str | None:
    if not shutil.which("lspci"):
        return None
    try:
        out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    markers = ("VGA compatible controller", "3D controller", "Display controller")
    for line in out.stdout.splitlines():
        if any(marker in line for marker in markers):
            name = line.split(": ", 1)[-1]
            for prefix in ("Advanced Micro Devices, Inc. [AMD/ATI] ", "Intel Corporation "):
                name = name.removeprefix(prefix)
            return name
    return None


def _gpu() -> str | None:
    return _nvidia() or _pci()


def _session() -> str:
    raw = os.environ.get("XDG_SESSION_TYPE", "unknown")
    return {"wayland": "Wayland", "x11": "X11", "tty": "TTY"}.get(raw.lower(), raw)


def detect() -> HostInfo:
    return HostInfo(
        distro=_os_release(),
        atomic=shutil.which("rpm-ostree") is not None,
        session=_session(),
        desktop=os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        kernel=platform.release(),
        gpu=_gpu(),
    )
