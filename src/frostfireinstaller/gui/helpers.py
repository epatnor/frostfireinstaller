"""Small GUI helpers: background work (and re-export of ``data_file``)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from gi.repository import GLib  # noqa: E402

from ..resources import data_file  # noqa: E402, F401


def run_async(
    func: Callable[[], Any],
    on_done: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    """Run *func* in a thread and post the result back to the GTK main loop."""

    def worker() -> None:
        try:
            result = func()
        except Exception as exc:  # noqa: BLE001
            if on_error is not None:
                GLib.idle_add(on_error, exc)
        else:
            if on_done is not None:
                GLib.idle_add(on_done, result)

    threading.Thread(target=worker, daemon=True).start()
