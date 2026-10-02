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

APP_ID = "io.github.epatnor.frostfireinstaller"

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
    background-color: #00030a;
    color: #eaf9ff;
    padding: 8px 16px;
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
    padding: 8px 16px;
    border-top: 1px solid rgba(120, 200, 255, 0.10);
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    font-size: 0.86em;
}}
.config-warn {{
    color: #ff7a2f;
}}

.run-bar {{
    background-color: #061520;
    padding: 14px 16px;
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
    color: #ff8f6b;
    background-color: rgba(246, 97, 81, 0.15);
}}
.status-missing {{
    color: #ffb079;
    background-color: rgba(255, 122, 47, 0.14);
}}

.activity-bar {{
    background-color: #07141f;
    color: #cfe9f7;
    padding: 8px 16px;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    font-size: 0.9em;
}}
.activity-bar spinner {{
    color: #63c2ff;
}}

.recommend-bar {{
    background-color: rgba(255, 122, 47, 0.14);
    color: #ffd9b3;
    padding: 8px 16px;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    font-size: 0.86em;
}}

button.bn-footer {{
    background-color: #00030a;
    background-image: none;
    border: none;
    border-bottom: 1px solid rgba(120, 200, 255, 0.10);
    border-radius: 0;
    box-shadow: none;
    padding: 0 16px;
    min-height: 40px;
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
    margin-bottom: 14px;
}}
.bn-panel .card-head {{
    padding: 7px 14px 6px 14px;
    min-height: 0;
    background-color: rgba(120, 200, 255, 0.04);
}}
.bn-panel .card-head:hover {{
    background-color: rgba(120, 200, 255, 0.04);
}}
.card-title {{
    font-size: 0.95em;
    font-weight: 700;
    color: #dcefff;
}}
.card-desc {{
    font-size: 0.78em;
    color: rgba(234, 249, 255, 0.5);
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
    padding: 0 14px;
    min-height: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.055);
}}
.bn-panel row > box.header {{
    min-height: 38px;
    margin: 0;
    padding: 2px 0;
}}
.bn-panel row:last-child {{
    border-bottom: none;
}}
.bn-panel row:hover {{
    background-color: rgba(120, 200, 255, 0.035);
}}
row.row-inactive .title {{
    color: rgba(234, 249, 255, 0.40);
}}
row.row-inactive .subtitle {{
    color: rgba(234, 249, 255, 0.28);
}}

button.bn-btn,
button.bn-btn-primary,
button.bn-btn-danger {{
    border-radius: 3px;
    min-height: 26px;
    padding: 0 12px;
    font-weight: 600;
    font-size: 0.9em;
    box-shadow: none;
    text-shadow: none;
}}
menubutton.help-button {{
    min-width: 0;
    min-height: 0;
    padding: 0;
    margin: 0;
    border: none;
    background: none;
    background-image: none;
    box-shadow: none;
}}
menubutton.help-button > button {{
    min-width: 24px;
    min-height: 24px;
    padding: 0;
    border: none;
    background: none;
    background-image: none;
    box-shadow: none;
    color: #9fc6dd;
    -gtk-icon-size: 19px;
}}
menubutton.help-button > button:hover {{
    color: #eaf9ff;
}}
menubutton.help-button.help-warn > button {{
    color: #ff7a2f;
}}
menubutton.help-button.help-warn > button:hover {{
    color: #ffd9b3;
}}
.runner-dropdown {{
    border: 1px solid rgba(120, 200, 255, 0.22);
    border-radius: 3px;
    background-color: rgba(120, 200, 255, 0.05);
    min-height: 26px;
}}
.runner-dropdown button {{
    border: none;
    background: none;
    background-image: none;
    box-shadow: none;
    min-height: 26px;
    padding: 0 4px 0 10px;
    color: #d9edfa;
    font-weight: 400;
    font-size: 0.9em;
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
    background-image: linear-gradient(to bottom, #cf5418, #a8400e);
    color: #ffffff;
    border: 1px solid #ff8f45;
}}
button.bn-btn-danger:hover {{
    background-image: linear-gradient(to bottom, #dd5f20, #b8460f);
}}

.material-icon {{
    font-family: "Material Symbols Outlined";
    font-size: 24px;
}}
.material-icon-filled {{
    font-family: "Material Symbols Filled";
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
        self._tray: object | None = None
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

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
        self._ensure_tray(window)

    def _ensure_tray(self, window: MainWindow) -> None:
        """Create the StatusNotifierItem tray icon once."""
        if self._tray is not None:
            return
        from .tray import TrayIcon

        self._tray = TrayIcon(
            app_id=APP_ID,
            on_activate=window.present,
            on_toggle=window.toggle_battlenet,
            on_quit=self.quit,
        )
        window.set_tray(self._tray)

    def _on_shutdown(self, *_args: object) -> None:
        if self._tray is not None:
            self._tray.close()  # type: ignore[attr-defined]
            self._tray = None
