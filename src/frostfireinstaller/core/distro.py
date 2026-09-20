"""Host detection: distro, atomic, session, GPU."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


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


def _gib(size: int) -> str:
    """Format a byte count as GB (e.g. 4 GB, 11.5 GB)."""
    gib = size / 1024**3
    return f"{gib:.0f} GB" if abs(gib - round(gib)) < 0.05 else f"{gib:.1f} GB"


def _vram_sysfs() -> str | None:
    for path in sorted(Path("/sys/class/drm").glob("card[0-9]*/device/mem_info_vram_total")):
        try:
            total = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if total > 0:
            return _gib(total)
    return None


def _nvidia() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
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
    name, _, rest = lines[0].partition(",")
    memory, _, driver = rest.partition(",")
    clean = name.strip().removeprefix("NVIDIA ").removesuffix(" Laptop GPU")
    parts = [clean]
    amount = memory.split()[0] if memory.split() else ""
    if amount.isdigit() and memory.strip().lower().endswith("mib"):
        parts.append(_gib(int(amount) * 1024**2))
    if driver.strip():
        parts.append(driver.strip())
    return " · ".join(parts)


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
            vram = _vram_sysfs()
            return f"{name} · {vram}" if vram else name
    return None


def _gpu() -> str | None:
    return _nvidia() or _pci()


def detect() -> HostInfo:
    return HostInfo(
        distro=_os_release(),
        atomic=shutil.which("rpm-ostree") is not None,
        session=os.environ.get("XDG_SESSION_TYPE", "unknown"),
        desktop=os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        kernel=platform.release(),
        gpu=_gpu(),
    )
