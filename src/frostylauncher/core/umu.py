"""Thin wrapper around the host's ``umu-run``."""

from __future__ import annotations

import os
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
    return env


def spawn(
    config: Config,
    proton: Path,
    exe: str,
    extra_args: list[str] | None = None,
    stdout: IO[Any] | int | None = None,
    stderr: IO[Any] | int | None = None,
) -> subprocess.Popen[bytes]:
    """Launch a Windows executable via umu-run in a new session (detached)."""
    cmd = ["umu-run", exe, *(extra_args or [])]
    return subprocess.Popen(  # noqa: S603
        cmd,
        env=build_env(config, proton),
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )


def run_blocking(
    config: Config, proton: Path, exe: str, extra_args: list[str] | None = None
) -> int:
    cmd = ["umu-run", exe, *(extra_args or [])]
    return subprocess.call(cmd, env=build_env(config, proton))  # noqa: S603
