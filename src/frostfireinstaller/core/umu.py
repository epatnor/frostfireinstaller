"""Thin wrapper around the host's ``umu-run``.

Also builds the launch command with optional performance wrappers
(gamemode, gamescope) and the MangoHud environment variable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import IO, Any

from ..config import Config

# Environment required for a reliable Battle.net CEF UI (see docs/architecture.md).
BASE_ENV: dict[str, str] = {
    "WINE_SIMULATE_WRITECOPY": "1",
    "WINEDLLOVERRIDES": "locationapi=d",
}

# Battle.net starts the game and is then usually closed, so the launcher process
# exits long before the play session does. The idle lock therefore rides on the
# wineserver: wait up to two minutes for it to appear, then hold until it is
# gone. If it never appears the sidecar exits on its own rather than leaking a
# lock that would keep the machine awake indefinitely.
_HAS_WINESERVER = 'pgrep -x -u "$(id -u)" wineserver >/dev/null 2>&1'
_INHIBIT_SCRIPT = (
    f"for _ in $(seq 60); do {_HAS_WINESERVER} && break; sleep 2; done; "
    f"while {_HAS_WINESERVER}; do sleep 10; done"
)


def build_env(config: Config, proton: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["WINEPREFIX"] = str(config.prefix)
    env["GAMEID"] = config.gameid
    env["PROTONPATH"] = str(proton)
    env.update(BASE_ENV)
    # With gamescope the overlay must run via ``--mangoapp``; injecting
    # MANGOHUD=1 inside gamescope is a known source of frametime stutter.
    if config.performance.mangohud and not config.performance.gamescope:
        env["MANGOHUD"] = "1"
    # User overrides from [env] (e.g. DXVK_FILTER_DEVICE_NAME) win.
    env.update(config.env)
    return env


def launch_command(config: Config, exe: str, extra_args: list[str] | None = None) -> list[str]:
    """Assemble the command line, applying performance wrappers if enabled."""
    cmd = ["umu-run", exe, *(extra_args or [])]
    perf = config.performance
    if perf.gamescope and shutil.which("gamescope"):
        gamescope = ["gamescope"]
        if perf.gamescope_width > 0 and perf.gamescope_height > 0:
            gamescope += ["-W", str(perf.gamescope_width), "-H", str(perf.gamescope_height)]
        if perf.gamescope_output:
            gamescope += ["-O", perf.gamescope_output]
        if perf.gamescope_grab_cursor:
            gamescope.append("--force-grab-cursor")
        if perf.gamescope_force_fullscreen:
            gamescope.append("--force-windows-fullscreen")
        if perf.mangohud and shutil.which("mangoapp"):
            gamescope.append("--mangoapp")
        cmd = [*gamescope, "-f", "--", *cmd]
    if perf.gamemode and shutil.which("gamemode"):
        cmd = ["gamemode", *cmd]
    return cmd


def inhibit_command() -> list[str] | None:
    """Command for a sidecar that keeps screen and machine awake, or ``None``.

    Two mechanisms have to be covered. ``systemd-inhibit`` blocks logind's own
    idle/suspend actions, while KDE's PowerDevil runs its screen-blanking timer
    off the freedesktop ScreenSaver/PowerManagement interfaces and can still
    fire through a logind lock - ``kde-inhibit`` covers that one. Both are
    applied when present; a missing tool simply drops out.

    This is deliberately *not* a wrapper around the launch command. Wrapping
    ties the lock to the launcher, and Battle.net exits once the game is up -
    which is what let the monitor sleep mid-game and trashed the window
    geometry on wake. It also keeps ``launch_command`` a plain argv list.
    """
    wrapper: list[str] = []
    if shutil.which("systemd-inhibit"):
        wrapper += [
            "systemd-inhibit",
            "--what=idle:sleep",
            "--mode=block",
            "--why=frostfireinstaller game session",
            "--",
        ]
    if shutil.which("kde-inhibit"):
        wrapper += ["kde-inhibit", "--power", "--screenSaver", "--"]
    if not wrapper:
        return None
    return [*wrapper, "sh", "-c", _INHIBIT_SCRIPT]


def spawn(
    config: Config,
    proton: Path,
    exe: str,
    extra_args: list[str] | None = None,
    stdout: IO[Any] | int | None = None,
    stderr: IO[Any] | int | None = None,
) -> subprocess.Popen[bytes]:
    """Launch a Windows executable via umu-run in a new session (detached).

    By default the child's stdio is detached (/dev/null) so it never holds the
    caller's terminal or pipes open.
    """
    if config.performance.inhibit_idle:
        _spawn_inhibitor()
    return subprocess.Popen(  # noqa: S603
        launch_command(config, exe, extra_args),
        env=build_env(config, proton),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL if stdout is None else stdout,
        stderr=subprocess.DEVNULL if stderr is None else stderr,
        start_new_session=True,
    )


def _spawn_inhibitor() -> None:
    """Start the idle-lock sidecar, detached. Best effort - never fatal."""
    cmd = inhibit_command()
    if cmd is None:
        return
    subprocess.Popen(  # noqa: S603
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def run_blocking(
    config: Config, proton: Path, exe: str, extra_args: list[str] | None = None
) -> int:
    return subprocess.call(  # noqa: S603
        launch_command(config, exe, extra_args), env=build_env(config, proton)
    )
