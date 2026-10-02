"""A short hardware summary for the Settings window.

Everything here is best-effort and read-only; where the data is only available
to root (memory type/speed via dmidecode) we simply omit it rather than asking
for privileges.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import gpu
from .proc import capture


def _run(command: list[str]) -> str:
    return capture(command) or ""


def _cpu_model() -> str:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return ""


def _cpu_nominal_khz() -> int:
    """The CPU's advertised (static) clock, not the live dynamic frequency."""
    try:
        return int(Path("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read_text())
    except (OSError, ValueError):
        return 0


def cpu() -> str:
    """CPU model plus its advertised clock (static, so it does not drift)."""
    model = _cpu_model() or "CPU"
    khz = _cpu_nominal_khz()
    return f"{model} ({khz / 1_000_000:.1f} GHz)" if khz else model


def _memory_dmi() -> str:
    """Memory type/speed from dmidecode, when it is readable (root)."""
    if not shutil.which("dmidecode"):
        return ""
    kinds: set[str] = set()
    speeds: set[str] = set()
    for line in _run(["dmidecode", "-t", "memory"]).splitlines():
        value = line.strip()
        if value.startswith("Type:") and "Unknown" not in value:
            kinds.add(value.split(":", 1)[1].strip())
        elif value.startswith("Speed:") and "Unknown" not in value:
            speeds.add(value.split(":", 1)[1].strip())
    parts = []
    if kinds:
        parts.append("/".join(sorted(kinds)))
    if speeds:
        parts.append("/".join(sorted(speeds)))
    return " ".join(parts)


def memory() -> str:
    """Total RAM, plus type/speed when dmidecode can read it."""
    total = ""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                gib = int(line.split()[1]) / 1024 / 1024
                total = f"{gib:.0f} GB"
                break
    except (OSError, ValueError):
        pass
    detail = _memory_dmi()
    if total and detail:
        return f"{total} {detail}"
    return total or "unknown"


def gpus() -> list[str]:
    """The display controllers, one per GPU."""
    return gpu.pci_gpus()


def disks() -> list[str]:
    """Physical disks: model, size and SSD/HDD (loop/zram/optical skipped)."""
    output = _run(["lsblk", "-dP", "-o", "NAME,SIZE,MODEL,ROTA,TYPE"])
    found: list[str] = []
    for line in output.splitlines():
        fields = dict(re.findall(r'(\w+)="([^"]*)"', line))
        name = fields.get("NAME", "")
        if fields.get("TYPE") != "disk" or name.startswith(("zram", "loop", "sr")):
            continue
        model = fields.get("MODEL", "").strip() or name
        kind = "HDD" if fields.get("ROTA") == "1" else "SSD"
        size = fields.get("SIZE", "").strip()
        found.append(f"{model} ({size}, {kind})" if size else f"{model} ({kind})")
    return found
