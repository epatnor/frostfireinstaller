"""Health checks: detect a hung/faulty client and recover."""

from __future__ import annotations

import os
import shutil
import subprocess
import time

from ..config import Config
from ..logsetup import get_logger

log = get_logger()

# pkill -f patterns (brackets avoid matching our own command line)
_KILL_PATTERNS = ("Battle[.]net", "Agent[.]exe", "umu-ru[n]")


def running() -> bool:
    try:
        out = subprocess.run(
            ["pgrep", "-f", "Battle[.]net.exe"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return bool(out.stdout.strip())


def kill_all() -> None:
    """Stop the client and its helpers (SIGTERM first, then SIGKILL)."""
    for pattern in _KILL_PATTERNS:
        subprocess.run(["pkill", "-f", pattern], check=False)  # noqa: S603, S607
    time.sleep(1)
    for pattern in _KILL_PATTERNS:
        subprocess.run(["pkill", "-9", "-f", pattern], check=False)  # noqa: S603, S607
    log.info("Killed Battle.net processes")


def ui_window_present() -> bool:
    """True if the Battle.net window is on screen — or if we cannot tell.

    Pure Wayland sessions have no usable X window tree, so a failed or
    impossible check must never be read as "the client is broken".
    """
    if not shutil.which("xwininfo") or not os.environ.get("DISPLAY"):
        return True  # cannot tell; assume fine
    try:
        out = subprocess.run(
            ["xwininfo", "-root", "-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return True
    if out.returncode != 0:
        return True  # no X display available; cannot tell
    return "Battle.net Login" in out.stdout or '"Battle.net"' in out.stdout


def wait_for_ui(timeout: int = 40, interval: int = 1) -> bool:
    waited = 0
    while waited < timeout:
        if ui_window_present():
            return True
        time.sleep(interval)
        waited += interval
    return False


def remediate(config: Config) -> None:
    log.warning("Trying to recover a hung client ...")
    kill_all()
    time.sleep(2)
    base = config.prefix / "drive_c/users/steamuser/AppData/Local/Battle.net"
    for sub in ("Cache", "CEF"):
        target = base / sub
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            log.info("Cleared %s", sub)
