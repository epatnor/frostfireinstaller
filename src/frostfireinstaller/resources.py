"""Bundled data lookup, shared by the service layer and the GUI."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def data_file(*parts: str) -> Path | None:
    """Return a path to a bundled data file (icons, header), or None."""
    try:
        base = resources.files("frostfireinstaller.data")
    except (ModuleNotFoundError, TypeError):
        return None
    target = base.joinpath(*parts)
    try:
        return Path(str(target)) if target.is_file() else None
    except (FileNotFoundError, OSError):
        return None
