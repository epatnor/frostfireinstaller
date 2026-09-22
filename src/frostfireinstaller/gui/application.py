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

# Bundled font used across the app UI (overridable for testing).
INFO_FONT = os.environ.get("FROSTFIRE_INFO_FONT", "Open Sans")

# Palette and chrome inspired by the Battle.net launcher: flat dark panels,
# 1px separators, small corner radii, blue gradient primary buttons. The
# colours themselves are our own frost/fire scheme.
_CSS = f"""
@define-color accent_bg_color #0b6fd0;
@define-color accent_fg_color #ffffff;
@define-color accent_color #2aa0ff;
@define-color window_bg_color #00070f;
@define-color headerbar_bg_color #040c14;
@define-color card_bg_color #07121d;
@define-color popover_bg_color #081420;

window {{
    background-color: #00070f;
    color: #eaf9ff;
    font-family: "{INFO_FONT}", "Saira", sans-serif;
    font-size: 14px;
}}

headerbar {{
    background-color: #040c14;
    color: #eaf9ff;
    border-bottom: 1px solid rgba(120, 200, 255, 0.12);
    min-height: 44px;
}}

.info-strip {{
    background-color: #00070f;
    color: #eaf9ff;
    padding: 8px 14px;
    font-size: 0.8em;
}}
.info-key {{
    opacity: 0.55;
    font-weight: 600;
    letter-spacing: 0.02em;
}}
.config-strip {{
    background-color: #051320;
    color: #eaf9ff;
    padding: 8px 18px;
    border-top: 1px solid rgba(120, 200, 255, 0.10);
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    font-size: 0.86em;
}}
.config-warn {{
    color: #ff7a2f;
}}

.run-bar {{
    background-color: #061520;
    padding: 14px 18px;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
}}
.run-bar .heading {{
    font-size: 1.06em;
    font-weight: 700;
}}
.status-pill {{
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.74em;
    font-weight: 700;
    letter-spacing: 0.05em;
}}
.status-on {{
    color: #74f0a8;
    background-color: rgba(87, 227, 137, 0.14);
}}
.status-off {{
    color: rgba(234, 249, 255, 0.62);
    background-color: rgba(255, 255, 255, 0.06);
}}
.status-missing {{
    color: #ffb079;
    background-color: rgba(255, 122, 47, 0.14);
}}

.activity-bar {{
    background-color: #07141f;
    color: #cfe9f7;
    padding: 8px 18px;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    font-size: 0.9em;
}}
.activity-bar spinner {{
    color: #63c2ff;
}}

.recommend-bar {{
    background-color: rgba(255, 122, 47, 0.14);
    color: #ffd9b3;
    padding: 8px 14px;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    font-size: 0.86em;
}}
.recommend-bar.info {{
    background-color: rgba(116, 216, 255, 0.10);
    color: #cfe9f7;
}}

button.bn-footer {{
    background-color: #07141f;
    background-image: none;
    border: none;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    border-radius: 0;
    box-shadow: none;
    padding: 0 18px;
    min-height: 44px;
    color: #9fc6dd;
    font-weight: 600;
    font-size: 0.9em;
}}
button.bn-footer:hover,
button.bn-footer:focus,
button.bn-footer:active {{
    background-color: #0d2233;
    background-image: none;
    color: #eaf9ff;
    outline: none;
}}
button.bn-footer .material-icon {{
    font-size: 22px;
}}

.bn-sections {{
    margin: 16px 18px 22px 18px;
}}
.bn-section {{
    margin-bottom: 20px;
}}
.section-title {{
    font-size: 0.74em;
    font-weight: 700;
    letter-spacing: 0.11em;
    color: #7fb6d9;
    margin: 0 2px 8px 2px;
}}
.section-desc {{
    font-size: 0.82em;
    color: rgba(234, 249, 255, 0.5);
    margin: 0 2px 10px 2px;
}}
.bn-panel {{
    background-color: #07121d;
    border: 1px solid rgba(120, 200, 255, 0.12);
    border-radius: 4px;
}}
.bn-panel row {{
    padding: 8px 14px;
    min-height: 44px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.055);
}}
.bn-panel row:last-child {{
    border-bottom: none;
}}
.bn-panel row:hover {{
    background-color: rgba(120, 200, 255, 0.035);
}}

button.bn-btn,
button.bn-btn-primary,
button.bn-btn-danger,
button.bn-btn-flat {{
    border-radius: 3px;
    min-height: 30px;
    padding: 0 14px;
    font-weight: 600;
    font-size: 0.9em;
    box-shadow: none;
    text-shadow: none;
}}
button.bn-btn {{
    background-image: linear-gradient(to bottom, #16232f, #0d1720);
    color: #d9edfa;
    border: 1px solid rgba(120, 200, 255, 0.22);
}}
button.bn-btn:hover {{
    background-image: linear-gradient(to bottom, #1d2e3d, #12202c);
    border-color: rgba(120, 200, 255, 0.38);
}}
button.bn-btn:active {{
    background-image: linear-gradient(to bottom, #0d1720, #16232f);
}}
button.bn-btn-primary {{
    background-image: linear-gradient(to bottom, #1c86e6, #0a5fb8);
    color: #ffffff;
    border: 1px solid #63c2ff;
}}
button.bn-btn-primary:hover {{
    background-image: linear-gradient(to bottom, #2e97f0, #0c6ac6);
    border-color: #8ad2ff;
}}
button.bn-btn-primary:active {{
    background-image: linear-gradient(to bottom, #0a5fb8, #1c86e6);
}}
button.bn-btn-danger {{
    background-image: linear-gradient(to bottom, #ff8f45, #d9591a);
    color: #ffffff;
    border: 1px solid #b3450f;
}}
button.bn-btn-danger:hover {{
    background-image: linear-gradient(to bottom, #ffa15f, #e5641f);
}}
button.bn-btn-flat {{
    background: none;
    background-image: none;
    border: none;
    color: #9fc6dd;
    padding: 0 8px;
}}
button.bn-btn-flat:hover {{
    background-color: rgba(120, 200, 255, 0.08);
    background-image: none;
    color: #eaf9ff;
}}

.material-icon {{
    font-family: "Material Symbols Outlined";
    font-size: 24px;
}}
.icon-ice {{
    color: #74d8ff;
}}
.icon-fire {{
    color: #ff7a2f;
}}
.icon-red {{
    color: #f66151;
}}
.icon-green {{
    color: #57e389;
}}
.icon-white {{
    color: #ffffff;
}}

switch:checked {{
    background-color: #0b6fd0;
}}
switch:checked slider {{
    background-color: #ffffff;
}}

popover > contents {{
    background-color: #081420;
    color: #eaf9ff;
    border: 1px solid rgba(120, 200, 255, 0.14);
    border-radius: 4px;
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


class FrostfireApplication(Adw.Application):
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
