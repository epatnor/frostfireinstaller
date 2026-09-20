"""The Adw.Application."""

from __future__ import annotations

import ctypes

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .helpers import data_file  # noqa: E402
from .window import MainWindow  # noqa: E402

APP_ID = "io.github.frostfireinstaller"

_CSS = """
.info-strip {
    background-color: #00070f;
    color: #eaf9ff;
    padding: 14px 18px;
    font-family: "Doto", monospace;
    font-size: 1.05em;
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


def _register_fonts() -> None:
    """Register bundled fonts with fontconfig so Pango can use them."""
    font = data_file("fonts", "Doto.ttf")
    if font is None:
        return
    try:
        fontconfig = ctypes.CDLL("libfontconfig.so.1")
    except OSError:
        return
    fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
    fontconfig.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
    fontconfig.FcConfigAppFontAddFile(fontconfig.FcConfigGetCurrent(), str(font).encode())


class FrostyApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self._on_activate)

    def _load_css(self) -> None:
        _register_fonts()
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
