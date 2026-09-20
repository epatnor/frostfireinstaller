"""Locate Proton builds in the usual ``compatibilitytools.d`` directories."""

from __future__ import annotations

from pathlib import Path

SEARCH_DIRS: tuple[Path, ...] = (
    Path.home() / ".local/share/Steam/compatibilitytools.d",
    Path.home() / ".steam/root/compatibilitytools.d",
    Path.home() / ".var/app/com.valvesoftware.Steam/.steam/steam/compatibilitytools.d",
    Path("/usr/share/steam/compatibilitytools.d"),
)

# Preferred build families, in order.
PREFERRED: tuple[str, ...] = ("GE-Proton", "UMU-Proton", "Proton")


def _safe_name(name: str) -> bool:
    """Reject anything that is not a plain directory name (no traversal)."""
    return bool(name) and "/" not in name and "\\" not in name and name not in {".", ".."}


def find(proton_name: str | None = None) -> Path | None:
    """Return the path to a Proton build, or ``None``.

    If *proton_name* is given, only an exact directory match is accepted.
    Otherwise builds are searched preferring GE-Proton, then UMU-Proton, then Proton.
    """
    if proton_name:
        if not _safe_name(proton_name):
            return None
        for directory in SEARCH_DIRS:
            candidate = directory / proton_name
            if candidate.is_dir():
                return candidate
        return None

    for family in PREFERRED:
        for directory in SEARCH_DIRS:
            if not directory.is_dir():
                continue
            for candidate in sorted(directory.glob(f"{family}*")):
                if candidate.is_dir():
                    return candidate
    return None


def all_builds() -> list[Path]:
    """Return every detected Proton build (deduplicated, sorted)."""
    seen: dict[str, Path] = {}
    for directory in SEARCH_DIRS:
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir()):
            if candidate.is_dir() and (candidate / "proton").exists():
                seen[str(candidate)] = candidate
    return sorted(seen.values())
