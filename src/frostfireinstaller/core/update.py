"""Check GitHub Releases for a newer version and update an isolated install.

The check only needs the public Releases API (no token). The in-place update
installs the release wheel into the running environment with pip, which works
for a pipx or virtualenv install that owns its environment. A system or distro
install is owned by the package manager and is left for it to update.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from importlib import util as importlib_util
from pathlib import Path
from typing import Any

from .. import __version__
from ..logsetup import get_logger
from .progress import Progress, emit

log = get_logger()

REPO = "epatnor/frostfireinstaller"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": f"frostfireinstaller/{__version__}",
}
_TIMEOUT = 15


@dataclass(frozen=True, slots=True)
class Release:
    version: str
    url: str
    wheel_url: str | None
    notes: str


def parse_version(text: str) -> tuple[int, ...]:
    """Turn ``v0.2.15`` / ``0.2.15-rc1`` into a comparable tuple of ints."""
    core = text.strip().lstrip("vV").split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for piece in core.split("."):
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts)


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
        return json.load(response)


def latest() -> Release:
    """Fetch the latest GitHub release."""
    data = _get_json(RELEASES_API)
    tag = str(data.get("tag_name", "")).lstrip("vV")
    assets = data.get("assets", [])
    wheel = next(
        (
            str(asset.get("browser_download_url"))
            for asset in assets
            if str(asset.get("name", "")).endswith(".whl")
        ),
        None,
    )
    return Release(
        version=tag,
        url=str(data.get("html_url") or RELEASES_PAGE),
        wheel_url=wheel,
        notes=str(data.get("body") or ""),
    )


def check() -> Release | None:
    """Return the newest release when it is newer than the running version."""
    release = latest()
    if not release.version:
        return None
    if parse_version(release.version) > parse_version(__version__):
        return release
    return None


def auto_check_enabled() -> bool:
    """Automatic checks can be turned off (offline or metered machines)."""
    return os.environ.get("FROSTFIREINSTALLER_NO_UPDATE_CHECK") not in ("1", "true", "yes")


def can_self_update() -> bool:
    """True when the app runs from an environment it can install into.

    Only an isolated venv (pipx or a plain virtualenv) qualifies; a system-wide
    or distro install is owned by the package manager and is left alone.
    """
    if sys.prefix == sys.base_prefix:
        return False
    if importlib_util.find_spec("pip") is None:
        return False
    return os.access(sys.prefix, os.W_OK)


def _download(url: str, dest: Path, on_progress: Progress | None) -> Path:
    request = urllib.request.Request(url, headers=_HEADERS)
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        dest.open(  # noqa: S310
            "wb"
        ) as fh,
    ):
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(1 << 20):
            fh.write(chunk)
            done += len(chunk)
            if total:
                emit(on_progress, f"Downloading the update ... {done * 100 // total}%")
    return dest


def _install(wheel: Path, on_progress: Progress | None) -> None:
    emit(on_progress, "Installing the update ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "--no-input", str(wheel)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "pip could not install the update")


def self_update(on_progress: Progress | None = None) -> str:
    """Download and install the latest release wheel into this environment.

    Returns the installed version. The running process keeps the old code; the
    new version takes effect on the next start.
    """
    release = latest()
    if parse_version(release.version) <= parse_version(__version__):
        return __version__
    if not release.wheel_url:
        raise RuntimeError("The latest release has no wheel attached")
    if not can_self_update():
        raise RuntimeError("This install cannot update itself; use your package manager")
    emit(on_progress, f"Downloading frostfireinstaller {release.version} ...")
    with tempfile.TemporaryDirectory(prefix="frostfire-update-") as tmp:
        wheel = _download(release.wheel_url, Path(tmp) / Path(release.wheel_url).name, on_progress)
        _install(wheel, on_progress)
    emit(on_progress, f"Updated to {release.version} - restart the app")
    return release.version
