"""Single-column content for the main window.

Layout: header bar -> banner -> system strip -> config band -> Battle.net band
-> (warnings) -> activity strip -> Settings footer.

Scope: a Battle.net installer helper. Games are started from Blizzard's own
launcher, not here.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gdk, GdkPixbuf, GLib, Gtk, Pango  # noqa: E402

from ..config import Config  # noqa: E402
from ..core import distro, health, proton, recommend  # noqa: E402
from . import actions, dialogs  # noqa: E402
from .helpers import data_file, run_async  # noqa: E402
from .state import ClientState  # noqa: E402
from .widgets import MATERIAL, ActivityBar, Surface, button, icon, toolbar_page  # noqa: E402

if TYPE_CHECKING:
    from .window import MainWindow

# The window is locked to this width and the banner fills it. The banner height
# is derived from the image's aspect ratio, so any header renders undistorted;
# the window height is banner + the fixed chrome below it. The advanced options
# live in their own window (see gui/settings.py).
WINDOW_WIDTH = 608
DEFAULT_BANNER_HEIGHT = 198
_CHROME_HEIGHT = 350 - DEFAULT_BANNER_HEIGHT  # window minus banner


def _banner_height(banner: Path | None) -> int:
    """Height for a full-width banner that matches the image's aspect ratio."""
    if banner is None:
        return DEFAULT_BANNER_HEIGHT
    try:
        _format, width, height = GdkPixbuf.Pixbuf.get_file_info(str(banner))
    except (GLib.Error, OSError, TypeError):
        return DEFAULT_BANNER_HEIGHT
    if not width or not height:
        return DEFAULT_BANNER_HEIGHT
    return max(140, min(360, round(WINDOW_WIDTH * height / width)))


def _draw_banner(
    _area: Gtk.DrawingArea, cr: Any, width: int, height: int, pixbuf: GdkPixbuf.Pixbuf
) -> None:
    """Paint the banner pixbuf to fill the drawing area exactly."""
    pix_w, pix_h = pixbuf.get_width(), pixbuf.get_height()
    if not pix_w or not pix_h or width <= 0 or height <= 0:
        return
    cr.save()
    cr.scale(width / pix_w, height / pix_h)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
    cr.paint()
    cr.restore()


def _banner(path: Path, height: int) -> Gtk.Widget:
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), WINDOW_WIDTH, height, True)
    # A DrawingArea has no natural size beyond its request, so the banner
    # stays exactly this tall and never rescales when the window grows.
    area = Gtk.DrawingArea()
    area.set_size_request(WINDOW_WIDTH, height)
    area.set_hexpand(True)
    area.set_vexpand(False)
    area.set_valign(Gtk.Align.START)
    area.set_draw_func(_draw_banner, pixbuf)
    return area


def _info_item(key: str, value: Gtk.Label, expand: bool = False) -> Gtk.Widget:
    item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    key_label = Gtk.Label(label=key, xalign=0)
    key_label.add_css_class("info-key")
    item.append(key_label)
    item.append(value)
    if expand:
        item.set_hexpand(True)
        value.set_hexpand(True)
        value.set_halign(Gtk.Align.START)
    return item


def _system_strip() -> Gtk.Widget:
    """One-line system summary below the banner.

    Host detection runs ``nvidia-smi``/``lspci``, so it fills in after the
    window is up instead of delaying it.
    """
    strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
    strip.add_css_class("info-strip")
    values: list[Gtk.Label] = []
    for index, key in enumerate(("Distro", "Session", "GPU")):
        value = Gtk.Label(label="...", xalign=0)
        value.set_ellipsize(Pango.EllipsizeMode.END)
        values.append(value)
        strip.append(_info_item(key, value, expand=index == 2))

    def fill(host: distro.HostInfo) -> None:
        texts = (
            f"{host.distro}, {host.kernel}",
            f"{host.session}, {host.desktop}",
            host.gpu or "-",
        )
        for label, text in zip(values, texts, strict=True):
            label.set_label(text)
            label.set_tooltip_text(text)

    run_async(distro.detect, fill)
    return strip


class ConfigStrip(Gtk.Box):
    """Narrow band: how the app is configured (runner and prefix)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.add_css_class("config-strip")
        self.proton = Gtk.Label(xalign=0)
        self.prefix = Gtk.Label(xalign=0)
        self.prefix.set_ellipsize(Pango.EllipsizeMode.END)
        self.append(_info_item("Proton", self.proton))
        self.append(_info_item("Prefix", self.prefix, expand=True))

    def refresh(self, state: ClientState) -> None:
        prefix = state.config.prefix
        self.prefix.set_label(str(prefix).replace(str(Path.home()), "~", 1))
        self.prefix.set_tooltip_text(str(prefix))

        build = proton.find(state.config.proton_name)
        self.proton.remove_css_class("config-warn")
        if build:
            self.proton.set_label(build.name)
            self.proton.set_tooltip_text(str(build))
        elif shutil.which("umu-run"):
            self.proton.set_label(f"auto ({proton.DEFAULT_CODENAME})")
            self.proton.set_tooltip_text(
                "No local Proton build; umu-launcher will download it on first launch"
            )
        else:
            self.proton.set_label("missing")
            self.proton.set_tooltip_text("No Proton found")
            self.proton.add_css_class("config-warn")


# (pill text, pill class, glyph, button label, tooltip, primary) per state.
_RUNNING = ("Running", "status-on", "stop", "Stop", "Stops Battle.net", False)
_STOPPED = ("Stopped", "status-off", "play", "Start", "Starts Battle.net", True)
_MISSING = (
    "Not installed",
    "status-missing",
    "download",
    "Install",
    "Installs Battle.net and starts the client",
    True,
)


class RunBar(Gtk.Box):
    """Battle.net state and the one action button: Install / Start / Stop."""

    def __init__(self, surface: Surface) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("run-bar")
        self._surface = surface

        text = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        text.set_valign(Gtk.Align.CENTER)
        title = Gtk.Label(label="Battle.net", xalign=0)
        title.add_css_class("heading")
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status-pill")
        self.status.set_valign(Gtk.Align.CENTER)
        text.append(title)
        text.append(self.status)
        self.append(text)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.append(spacer)

        self.icon = icon(MATERIAL["play"], filled=True)
        self.label = Gtk.Label()
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content.append(self.icon)
        content.append(self.label)
        self.button = button("", primary=True)
        self.button.set_child(content)
        self.button.connect("clicked", self._on_clicked)
        self.append(self.button)

    def refresh(self, state: ClientState) -> None:
        if state.running:
            look = _RUNNING
        else:
            look = _STOPPED if state.installed else _MISSING
        pill, tone, glyph, label, tooltip, primary = look

        self.status.set_label(pill)
        for name in ("status-on", "status-off", "status-missing"):
            self.status.remove_css_class(name)
        self.status.add_css_class(tone)

        self.icon.set_label(MATERIAL[glyph])
        for name in ("icon-red", "icon-white"):
            self.icon.remove_css_class(name)
        self.icon.add_css_class("icon-red" if state.running else "icon-white")

        self.label.set_label(label)
        self.button.set_tooltip_text(tooltip)
        for name in ("bn-btn", "bn-btn-primary"):
            self.button.remove_css_class(name)
        self.button.add_css_class("bn-btn-primary" if primary else "bn-btn")

    def trigger(self) -> None:
        """Run the same action as clicking the button (used by the tray icon)."""
        if self.button.get_sensitive():
            self.button.emit("clicked")

    def _on_clicked(self, clicked: Gtk.Button) -> None:
        if health.running():
            health.kill_all()
            self._surface.refresh_state()
            self._surface.toast("Stopped Battle.net")
            return
        actions.start(self._surface, clicked)


class _RecommendationBar(Gtk.Box):
    """Strip that surfaces the system check's warnings; opens the full report."""

    def __init__(self, title: str, on_show: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add_css_class("recommend-bar")
        self.append(icon(MATERIAL["info"], "fire"))
        label = Gtk.Label(label=title, xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_hexpand(True)
        self.append(label)
        view = button("View", primary=True, tooltip="Show recommendations and commands")
        view.connect("clicked", lambda *_: on_show())
        self.append(view)


def _recommendation_slot(window: MainWindow) -> Gtk.Widget:
    """Runs the system check in the background; shows a strip only on warnings.

    The check calls ``vulkaninfo``, ``journalctl`` and friends (seconds each), so
    it must never run before the window is shown.
    """
    slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    def show(items: list[recommend.Recommendation]) -> None:
        warns = [item for item in items if item.level == "warn"]
        if warns:
            on_show = lambda: dialogs.show_recommendations(window, items)  # noqa: E731
            slot.append(_RecommendationBar(warns[0].title, on_show))

    run_async(lambda: recommend.report(Config.load()), show)
    return slot


def _settings_footer(window: MainWindow) -> Gtk.Button:
    footer = Gtk.Button()
    footer.add_css_class("bn-footer")
    footer.set_hexpand(True)
    footer.set_tooltip_text("Open settings")
    content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    content.set_hexpand(True)
    spacer = Gtk.Box()
    spacer.set_hexpand(True)
    content.append(Gtk.Label(label="Settings", xalign=0))
    content.append(spacer)
    content.append(icon(MATERIAL["settings"], filled=True))
    footer.set_child(content)
    footer.connect("clicked", lambda *_: window.open_settings())
    return footer


def build_main(window: MainWindow) -> Adw.ToolbarView:
    """Build the column and wire its live parts into *window*."""
    banner = data_file("header", "frostfire_installer_header.png")
    banner_height = _banner_height(banner)

    config_strip = ConfigStrip()
    run_bar = RunBar(window)
    activity = ActivityBar()

    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    if banner is not None:
        column.append(_banner(banner, banner_height))
    column.append(_system_strip())
    column.append(config_strip)
    column.append(run_bar)
    column.append(_recommendation_slot(window))
    column.append(activity)
    column.append(_settings_footer(window))

    view, title = toolbar_page("Frostfire Installer", column)
    window.attach(title=title, run_bar=run_bar, activity=activity)
    window.register_state(config_strip.refresh)
    window.register_state(run_bar.refresh)
    window.set_default_size(WINDOW_WIDTH, _CHROME_HEIGHT + banner_height)
    return view
