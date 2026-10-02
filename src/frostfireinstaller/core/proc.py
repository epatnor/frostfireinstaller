"""Small subprocess helper shared by the host-detection code."""

from __future__ import annotations

import subprocess


def capture(command: list[str], timeout: float = 8) -> str | None:
    """Run *command* and return its stdout, or ``None`` if it cannot be run."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout
