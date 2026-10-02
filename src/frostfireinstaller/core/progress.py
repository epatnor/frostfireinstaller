"""Progress reporting shared by long-running operations."""

from __future__ import annotations

from collections.abc import Callable

from ..logsetup import get_logger

log = get_logger()

Progress = Callable[[str], None]


def emit(on_progress: Progress | None, message: str) -> None:
    """Report a human-readable step; never let a UI callback break the work."""
    if on_progress is None:
        return
    try:
        on_progress(message)
    except Exception:  # noqa: BLE001
        log.debug("progress callback failed", exc_info=True)
