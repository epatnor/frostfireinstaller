"""Host detection: distro, atomic, session, GPU."""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass

from . import gpu


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


def _gpu() -> str | None:
    if summary := gpu.nvidia_summary():
        return summary
    names = gpu.pci_gpus()
    return names[0] if names else None


def session() -> str:
    raw = os.environ.get("XDG_SESSION_TYPE", "unknown")
    return {"wayland": "Wayland", "x11": "X11", "tty": "TTY"}.get(raw.lower(), raw)


def detect() -> HostInfo:
    return HostInfo(
        distro=_os_release(),
        atomic=shutil.which("rpm-ostree") is not None,
        session=session(),
        desktop=os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        kernel=platform.release(),
        gpu=_gpu(),
    )
