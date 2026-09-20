"""The Adw.Application."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .window import MainWindow  # noqa: E402

APP_ID = "io.github.frostfireinstaller"

_CSS = """
.info-strip {
    background-color: #0b1c30;
    color: #eaf9ff;
    padding: 14px 18px;
}
.info-title {
    font-weight: bold;
    color: #8fd8ff;
    margin-bottom: 4px;
}
.info-key {
    opacity: 0.65;
}
.info-value {
    font-weight: bold;
}
"""


class FrostyApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self._on_activate)

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _on_activate(self, *_args: object) -> None:
        self._load_css()
        window = self.props.active_window
        if window is None:
            window = MainWindow(application=self)
        window.present()
