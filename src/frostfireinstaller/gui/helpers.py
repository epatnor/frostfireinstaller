"""Small GUI helpers: background work and bundled asset lookup."""

from __future__ import annotations

import threading
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402


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


def data_file(*parts: str) -> Path | None:
    """Return a path to a bundled data file (icons, covers), or None."""
    try:
        base = resources.files("frostfireinstaller.data")
    except (ModuleNotFoundError, TypeError):
        return None
    target = base.joinpath(*parts)
    try:
        return Path(str(target)) if target.is_file() else None
    except (FileNotFoundError, OSError):
        return None


def make_icon(pixel_size: int = 48) -> Gtk.Widget:
    """Return the app icon as a Gtk.Image, falling back to a themed icon."""
    svg = data_file("icons", "frostfireinstaller.svg")
    if svg is not None:
        image = Gtk.Image.new_from_file(str(svg))
        image.set_pixel_size(pixel_size)
        return image
    image = Gtk.Image.new_from_icon_name("applications-games-symbolic")
    image.set_pixel_size(pixel_size)
    return image
