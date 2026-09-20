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


def _gpu() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.stdout.strip().splitlines()
    return lines[0] if lines else None


def detect() -> HostInfo:
    return HostInfo(
        distro=_os_release(),
        atomic=shutil.which("rpm-ostree") is not None,
        session=os.environ.get("XDG_SESSION_TYPE", "unknown"),
        desktop=os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        kernel=platform.release(),
        gpu=_gpu(),
    )
