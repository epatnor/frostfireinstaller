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

# Codenames umu-launcher knows how to download by itself (no local build needed).
CODENAMES: tuple[str, ...] = ("UMU-Proton", "GE-Proton")
DEFAULT_CODENAME: str = "UMU-Proton"


def is_codename(name: str | None) -> bool:
    """True if *name* is a codename umu can fetch on its own."""
    return bool(name) and name in CODENAMES


def _safe_name(name: str) -> bool:
    """Reject anything that is not a plain directory name (no traversal)."""
    return bool(name) and "/" not in name and "\\" not in name and name not in {".", ".."}


def find(proton_name: str | None = None) -> Path | None:
    """Return the path to a Proton build, or ``None``.

    If *proton_name* is given, an exact directory match is preferred; a known
    codename (e.g. ``UMU-Proton``) is returned as-is so umu-launcher can download
    it on first launch. Otherwise builds are searched preferring GE-Proton, then
    UMU-Proton, then Proton.
    """
    if proton_name:
        if not _safe_name(proton_name):
            return None
        for directory in SEARCH_DIRS:
            candidate = directory / proton_name
            if candidate.is_dir():
                return candidate
        if is_codename(proton_name):
            return Path(proton_name)
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
    """Return every detected Proton build (deduplicated by real path, sorted)."""
    seen: dict[str, Path] = {}
    for directory in SEARCH_DIRS:
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir()):
            if candidate.is_dir() and (candidate / "proton").exists():
                try:
                    key = str(candidate.resolve())
                except OSError:
                    key = str(candidate)
                seen.setdefault(key, candidate)
    return sorted(seen.values())
