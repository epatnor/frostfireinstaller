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


def build_env(config: Config, proton: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["WINEPREFIX"] = str(config.prefix)
    env["GAMEID"] = config.gameid
    env["PROTONPATH"] = str(proton)
    env.update(BASE_ENV)
    if config.performance.mangohud:
        env["MANGOHUD"] = "1"
    return env


def launch_command(config: Config, exe: str, extra_args: list[str] | None = None) -> list[str]:
    """Assemble the command line, applying performance wrappers if enabled."""
    cmd = ["umu-run", exe, *(extra_args or [])]
    if config.performance.gamescope and shutil.which("gamescope"):
        cmd = ["gamescope", "-f", "--", *cmd]
    if config.performance.gamemode and shutil.which("gamemode"):
        cmd = ["gamemode", *cmd]
    return cmd


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
    return subprocess.Popen(  # noqa: S603
        launch_command(config, exe, extra_args),
        env=build_env(config, proton),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL if stdout is None else stdout,
        stderr=subprocess.DEVNULL if stderr is None else stderr,
        start_new_session=True,
    )


def run_blocking(
    config: Config, proton: Path, exe: str, extra_args: list[str] | None = None
) -> int:
    return subprocess.call(  # noqa: S603
        launch_command(config, exe, extra_args), env=build_env(config, proton)
    )
