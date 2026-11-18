"""Locate Proton builds in the usual ``compatibilitytools.d`` directories."""

from __future__ import annotations

import re
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


def build_version(build: Path) -> str | None:
    """The release a build reports in its ``version`` file (e.g. ``GE-Proton11-5``).

    Proton writes ``<timestamp> <release>``; aliases such as ProtonPlus's
    "Proton-GE Latest" only reveal their real release this way.
    """
    try:
        parts = (build / "version").read_text(encoding="utf-8", errors="replace").split()
    except OSError:
        return None
    return parts[1] if len(parts) >= 2 else None


def label(build: Path) -> str:
    """Directory name, plus the real release when the name does not show it."""
    version = build_version(build)
    if version and version not in build.name:
        return f"{build.name} ({version})"
    return build.name


def _family_rank(name: str) -> int:
    for rank, family in enumerate(PREFERRED):
        if name.startswith(family):
            return rank
    return len(PREFERRED)


def _numbers(name: str) -> tuple[int, ...]:
    name = re.sub(r"x86_64|aarch64", "", name)
    return tuple(int(part) for part in re.findall(r"\d+", name))


def _newest_first(builds: list[Path]) -> list[Path]:
    """Preferred family first, then newest release first (11-12 before 11-7)."""
    release = {b: build_version(b) or b.name for b in builds}
    by_name = sorted(builds, key=lambda b: b.name)
    by_version = sorted(by_name, key=lambda b: _numbers(release[b]), reverse=True)
    return sorted(by_version, key=lambda b: _family_rank(release[b]))


def _safe_name(name: str) -> bool:
    """Reject anything that is not a plain directory name (no traversal)."""
    return bool(name) and "/" not in name and "\\" not in name and name not in {".", ".."}


def find(proton_name: str | None = None) -> Path | None:
    """Return the path to a Proton build, or ``None``.

    If *proton_name* is given, an exact directory match is preferred; a known
    codename (e.g. ``UMU-Proton``) is returned as-is so umu-launcher can download
    it on first launch. Otherwise the newest build is picked, preferring
    GE-Proton, then UMU-Proton, then Proton.
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
            matches = [c for c in directory.glob(f"{family}*") if c.is_dir()]
            if matches:
                return _newest_first(matches)[0]
    return None


def all_builds() -> list[Path]:
    """Every detected Proton build, deduplicated by real path, newest first."""
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
    return _newest_first(list(seen.values()))
