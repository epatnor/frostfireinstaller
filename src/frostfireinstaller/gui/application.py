"""The Adw.Application."""

from __future__ import annotations

import ctypes
import os
from importlib import resources

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .window import MainWindow  # noqa: E402

APP_ID = "io.github.frostfireinstaller"

# Bundled font used in the info strip (overridable for testing).
INFO_FONT = os.environ.get("FROSTFIRE_INFO_FONT", "Saira")

_CSS = f"""
.info-strip {{
    background-color: #00070f;
    color: #eaf9ff;
    padding: 12px 18px;
    font-family: "{INFO_FONT}", sans-serif;
    font-size: 1em;
}}
.info-title {{
    color: #8fd8ff;
    margin-bottom: 4px;
}}
.info-key {{
    opacity: 0.65;
}}
.material-icon {{
    font-family: "Material Symbols Outlined";
    font-size: 18px;
}}
"""


def _register_fonts() -> None:
    """Register bundled fonts with fontconfig so Pango can use them."""
    try:
        fonts = resources.files("frostfireinstaller.data").joinpath("fonts")
        fontconfig = ctypes.CDLL("libfontconfig.so.1")
    except (ModuleNotFoundError, OSError, TypeError):
        return
    fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
    fontconfig.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
    config = fontconfig.FcConfigGetCurrent()
    for entry in fonts.iterdir():
        if entry.name.endswith(".ttf"):
            fontconfig.FcConfigAppFontAddFile(config, str(entry).encode())


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
