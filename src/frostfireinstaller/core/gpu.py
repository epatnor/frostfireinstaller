"""GPU, driver and Vulkan detection (read-only, best effort).

Used by the system check (``recommend``), host detection (``distro``), the
hardware summary (``sysinfo``) and the GUI's Graphics card.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..config import Config
from .proc import capture

XID_RE = re.compile(r"NVRM: Xid \(PCI:[0-9a-fA-F:.]+\):\s*(\d+)")
_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")

_32BIT_VULKAN_CANDIDATES = (
    "/usr/lib32/libvulkan.so.1",
    "/usr/lib/i386-linux-gnu/libvulkan.so.1",
    "/lib32/libvulkan.so.1",
    "/usr/lib/libvulkan.so.1",  # Fedora/openSUSE multiarch layout
)

_PCI_MARKERS = ("VGA compatible controller", "3D controller", "Display controller")
_PCI_VENDOR_PREFIXES = (
    "Advanced Micro Devices, Inc. [AMD/ATI] ",
    "Intel Corporation ",
    "NVIDIA Corporation ",
)


# --- enumeration ---------------------------------------------------------
def pci_gpus() -> list[str]:
    """The display controllers from ``lspci``, vendor prefix and revision stripped."""
    if not shutil.which("lspci"):
        return []
    names: list[str] = []
    for line in (capture(["lspci"], 10) or "").splitlines():
        if not any(marker in line for marker in _PCI_MARKERS):
            continue
        name = line.split(": ", 1)[-1]
        for prefix in _PCI_VENDOR_PREFIXES:
            name = name.removeprefix(prefix)
        names.append(re.sub(r"\s*\(rev [0-9a-f]+\)$", "", name).strip())
    return names


def nvidia_summary() -> str | None:
    """``"<model> (<driver>)"`` from ``nvidia-smi``, or ``None`` without NVIDIA."""
    if not shutil.which("nvidia-smi"):
        return None
    query = ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]
    lines = (capture(query, 10) or "").strip().splitlines()
    if not lines:
        return None
    name, _, driver = lines[0].partition(",")
    clean = name.strip().removeprefix("NVIDIA ").removesuffix(" Laptop GPU")
    return f"{clean} ({driver.strip()})" if driver.strip() else clean


def _integrated_vendor() -> str | None:
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*/device/vendor")):
        try:
            vendor = card.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if vendor == "0x1002":
            return "AMD"
        if vendor == "0x8086":
            return "Intel"
    return None


def integrated_gpu_name() -> str | None:
    """A vendor substring for the integrated GPU, for ``DXVK_FILTER_DEVICE_NAME``.

    Deliberately generic (the detected vendor, never a fixed model) so the
    filter matches whatever GPU the current machine actually has.
    """
    vendor = _integrated_vendor()
    return vendor if vendor in {"AMD", "Intel"} else None


def gpu_preference(config: Config) -> str:
    """The configured GPU preference: ``auto``, ``nvidia`` or ``integrated``."""
    value = config.env.get("DXVK_FILTER_DEVICE_NAME", "")
    if not value:
        return "auto"
    return "nvidia" if "nvidia" in value.lower() else "integrated"


def vram_mib() -> int | None:
    """Total video memory in MiB, if it can be determined."""
    if shutil.which("nvidia-smi"):
        query = ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]
        lines = (capture(query, 5) or "").strip().splitlines()
        if lines and lines[0].strip().isdigit():
            return int(lines[0].strip())
    for node in Path("/sys/class/drm").glob("card[0-9]*/device/mem_info_vram_total"):
        try:
            total = int(node.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if total > 0:
            return total // 1024**2
    return None


# --- NVIDIA --------------------------------------------------------------
def nvidia_driver_info() -> tuple[str | None, bool]:
    """Return ``(driver_version, is_open_module)`` (``(None, False)`` if no NVIDIA)."""
    try:
        text = Path("/proc/driver/nvidia/version").read_text(encoding="utf-8")
    except OSError:
        return None, False
    match = _VERSION_RE.search(text)
    return (match.group(1) if match else None), "Open Kernel Module" in text


def kernel_log(limit: int = 300) -> str:
    if not shutil.which("journalctl"):
        return ""
    return capture(["journalctl", "-k", "-b", "-n", str(limit), "--no-pager"], 6) or ""


# --- Vulkan --------------------------------------------------------------
def has_32bit_vulkan() -> bool:
    return any(Path(path).exists() for path in _32BIT_VULKAN_CANDIDATES)


def vulkan_versions_and_names() -> tuple[list[tuple[int, ...]], list[str]]:
    """Parse ``vulkaninfo --summary`` into ``(api_versions, device_names)``."""
    if not shutil.which("vulkaninfo"):
        return [], []
    text = capture(["vulkaninfo", "--summary"], 12)
    if text is None:
        return [], []
    versions = [
        tuple(int(part) for part in match.split("."))
        for match in re.findall(r"apiVersion\s*=\s*(\d+\.\d+(?:\.\d+)?)", text)
    ]
    names = [name.strip() for name in re.findall(r"deviceName\s*=\s*(.+)", text)]
    return versions, names
