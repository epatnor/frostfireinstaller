"""Single-column content for the main window.

Layout: window header bar (top) -> Frostfire banner -> all features as rows.

Scope: a Battle.net installer helper. Games are started from Blizzard's own
launcher, not here.

The visual language (flat bordered panels, thin separators, small radii,
gradient buttons, uppercase section labels) is modelled on the Battle.net
launcher, but uses our own frost/fire palette.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, distro, health, proton, recommend  # noqa: E402
from .helpers import data_file, run_async  # noqa: E402

# Desktop-file id used to address our own taskbar/dock entry.
APP_DESKTOP_URI = "application://io.github.epatnor.frostfireinstaller.desktop"


def set_running_badge(visible: bool) -> None:
    """Show or clear a badge on the app's taskbar icon (Unity Launcher API).

    KDE Plasma (and GNOME with a suitable extension) listen for this signal, so
    the icon keeps showing that Battle.net is up even when both windows are
    minimised - including after a suspend/resume.
    """
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        properties = {
            "count": GLib.Variant("x", 1 if visible else 0),
            "count-visible": GLib.Variant("b", visible),
        }
        bus.emit_signal(
            None,
            "/com/canonical/Unity/LauncherEntry",
            "com.canonical.Unity.LauncherEntry",
            "Update",
            GLib.Variant("(sa{sv})", (APP_DESKTOP_URI, properties)),
        )
    except GLib.Error:
        pass


def _kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


def _installer_state(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError:
        return "missing, will download on next start"
    return f"{size / 1024**2:.1f} MB, downloaded and cached"


# Material Symbols glyphs (subset of the variable font, see data/fonts).
MATERIAL = {
    "download": "\uf090",
    "play": "\ue037",
    "build": "\uf8cd",
    "stop": "\ue047",
    "refresh": "\ue5d5",
    "delete": "\ue92e",
    "info": "\ue88e",
    "check": "\ue5ca",
    "settings": "\ue8b8",
}

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


def _icon(glyph: str, tone: str | None = None, filled: bool = False) -> Gtk.Label:
    label = Gtk.Label(label=glyph)
    label.add_css_class("material-icon-filled" if filled else "material-icon")
    if tone is not None:
        label.add_css_class(f"icon-{tone}")
    return label


def _button(
    label: str,
    *,
    primary: bool = False,
    danger: bool = False,
    tooltip: str | None = None,
) -> Gtk.Button:
    button = Gtk.Button(label=label)
    button.set_valign(Gtk.Align.CENTER)
    if danger:
        button.add_css_class("bn-btn-danger")
    elif primary:
        button.add_css_class("bn-btn-primary")
    else:
        button.add_css_class("bn-btn")
    if tooltip is not None:
        button.set_tooltip_text(tooltip)
    return button


def _open_folder(path: Path) -> None:
    """Open a folder in the desktop file manager."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607
    except OSError:
        pass


class Section(Gtk.Box):
    """A card: a bordered panel whose first row is the header, then the rows."""

    def __init__(self, title: str, description: str | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("bn-section")

        self.rows = Gtk.ListBox()
        self.rows.set_selection_mode(Gtk.SelectionMode.NONE)
        self.rows.set_vexpand(True)
        self.rows.add_css_class("bn-panel")

        head = Gtk.ListBoxRow()
        head.set_activatable(False)
        head.set_selectable(False)
        head.set_focusable(False)
        head.add_css_class("card-head")
        head_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("card-title")
        head_box.append(heading)
        if description is not None:
            note = Gtk.Label(label=description, xalign=0)
            note.set_wrap(True)
            note.add_css_class("card-desc")
            head_box.append(note)
        head.set_child(head_box)
        self.rows.append(head)

        self.append(self.rows)

    def add(self, row: Gtk.Widget) -> None:
        self.rows.append(row)


def _toolbar_page(title: str, content: Gtk.Widget) -> Adw.ToolbarView:
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    title_widget = Adw.WindowTitle(title=title)
    header.set_title_widget(title_widget)
    view.add_top_bar(header)
    view.set_content(content)
    view.title_widget = title_widget  # type: ignore[attr-defined]
    return view


def _refresh_root(widget: Gtk.Widget) -> None:
    """Ask the window to refresh every widget that shows client state."""
    root = widget.get_root()
    if root is not None and hasattr(root, "refresh_state"):
        root.refresh_state()  # type: ignore[attr-defined]


def _reporter(root: Gtk.Widget | None) -> Callable[[str], None]:
    """Return a thread-safe progress reporter for background work."""

    def report(message: str) -> None:
        if root is not None and hasattr(root, "set_activity"):
            GLib.idle_add(root.set_activity, message)  # type: ignore[attr-defined]

    return report


def _clear_activity(root: Gtk.Widget | None) -> None:
    if root is not None and hasattr(root, "clear_activity"):
        root.clear_activity()  # type: ignore[attr-defined]


class ActivityBar(Gtk.Box):
    """Thin strip that shows the operation currently running (spinner + text)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add_css_class("activity-bar")
        self.spinner = Gtk.Spinner()
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.label = Gtk.Label(xalign=0)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.append(self.spinner)
        self.append(self.label)
        self.set_visible(False)

    def show(self, text: str) -> None:
        self.label.set_label(text)
        self.spinner.start()
        self.set_visible(True)

    def hide(self) -> None:
        self.spinner.stop()
        self.set_visible(False)


class RecommendationBar(Gtk.Box):
    """Strip that surfaces a recommendation; opens a dialog with copy-ready steps."""

    def __init__(self, items: list[recommend.Recommendation], on_show: Callable[[], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add_css_class("recommend-bar")
        warn = any(item.level == "warn" for item in items)
        if not warn:
            self.add_css_class("info")
        self.append(_icon(MATERIAL["info"], "fire" if warn else "ice"))

        label = Gtk.Label(label=items[0].title, xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_hexpand(True)
        self.append(label)

        button = _button("View", primary=warn)
        button.set_tooltip_text("Show recommendations and commands")
        button.connect("clicked", lambda *_: on_show())
        self.append(button)


class ClientRow(Adw.ActionRow):
    """Client state with the repair action in the same row."""

    def __init__(self, on_repair: Callable[[Gtk.Button], None]) -> None:
        super().__init__(title="Client")
        self.add_prefix(_icon(MATERIAL["build"], "ice"))
        self.button = _button("Repair", tooltip="Stop, clear CEF/cache and restart")
        self.button.connect("clicked", lambda *_: on_repair(self.button))
        self.add_suffix(self.button)
        self.refresh()

    def refresh(self) -> None:
        installed = battlenet.installed(Config.load())
        self.set_subtitle("The client is installed" if installed else "The client is not installed")


class RunBar(Gtk.Box):
    """Standalone Battle.net start/stop control (not part of any card)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("run-bar")

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

        self.icon = _icon(MATERIAL["play"], filled=True)
        self.label = Gtk.Label()
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content.append(self.icon)
        content.append(self.label)

        self.button = _button("", primary=True)
        self.button.set_child(content)
        self.button.connect("clicked", self._on_clicked)
        self.append(self.button)

        self.refresh()

    def _toast(self, message: str) -> None:
        root = self.get_root()
        if root is not None and hasattr(root, "toast"):
            root.toast(message)  # type: ignore[attr-defined]

    def refresh(self) -> None:
        config = Config.load()
        running = health.running()
        installed = battlenet.installed(config)

        if running:
            state, tone = "Running", "status-on"
        elif installed:
            state, tone = "Stopped", "status-off"
        else:
            state, tone = "Not installed", "status-missing"

        self.status.set_label(state)
        for name in ("status-on", "status-off", "status-missing"):
            self.status.remove_css_class(name)
        self.status.add_css_class(tone)

        if running:
            glyph = MATERIAL["stop"]
        else:
            glyph = MATERIAL["play"] if installed else MATERIAL["download"]
        self.icon.set_label(glyph)
        self.icon.remove_css_class("icon-red")
        self.icon.remove_css_class("icon-green")
        self.icon.remove_css_class("icon-white")
        self.icon.add_css_class("icon-red" if running else "icon-white")

        self.button.remove_css_class("bn-btn")
        self.button.remove_css_class("bn-btn-primary")
        self.button.remove_css_class("bn-btn-danger")

        if running:
            self.label.set_label("Stop")
            self.button.set_tooltip_text("Stops Battle.net")
            self.button.add_css_class("bn-btn")
        elif installed:
            self.label.set_label("Start")
            self.button.set_tooltip_text("Starts Battle.net")
            self.button.add_css_class("bn-btn-primary")
        else:
            self.label.set_label("Install")
            self.button.set_tooltip_text("Installs Battle.net and starts the client")
            self.button.add_css_class("bn-btn-primary")

    def trigger(self) -> None:
        """Run the same action as clicking the button (used by the tray icon)."""
        if self.button.get_sensitive():
            self.button.emit("clicked")

    def _on_clicked(self, button: Gtk.Button) -> None:
        if health.running():
            health.kill_all()
            _refresh_root(self)
            self._toast("Stopped Battle.net")
            return

        root = self.get_root()
        button.set_sensitive(False)
        report = _reporter(root)
        report("Preparing ...")
        self._toast("Starting Battle.net ...")

        def work() -> None:
            config = Config.load()
            service.launch(config, service.ensure(config, on_progress=report))

        def done(_result: object) -> None:
            button.set_sensitive(True)
            _clear_activity(root)
            _refresh_root(self)
            self._toast("Starting Battle.net")

        def error(exc: Exception) -> None:
            button.set_sensitive(True)
            _clear_activity(root)
            self._toast(f"Error: {exc}")

        run_async(work, done, error)


def _label(text: str) -> Gtk.Label:
    return Gtk.Label(label=text, xalign=0)


class ConfigStrip(Gtk.Box):
    """Narrow band: how the app is configured (runner and prefix)."""

    def __init__(self, config: Config) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.add_css_class("config-strip")
        self._config = config

        self.proton = _label("")
        self.prefix = _label(str(config.prefix).replace(str(Path.home()), "~", 1))
        self.prefix.set_ellipsize(Pango.EllipsizeMode.END)
        self.prefix.set_hexpand(True)
        self.prefix.set_halign(Gtk.Align.START)
        self.prefix.set_tooltip_text(str(config.prefix))

        self.append(_info_column_inline("Proton", self.proton))
        self.append(_info_column_inline("Prefix", self.prefix))
        self.refresh()

    def refresh(self) -> None:
        build = proton.find(self._config.proton_name)
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


def _info_column_inline(key: str, value: Gtk.Widget) -> Gtk.Widget:
    item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    key_label = Gtk.Label(label=key, xalign=0)
    key_label.add_css_class("info-key")
    item.append(key_label)
    item.append(value)
    return item


def _system_strip() -> Gtk.Widget:
    """One-line system summary below the banner (app details live in the run bar)."""
    host = distro.detect()
    strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
    strip.add_css_class("info-strip")

    items = (
        ("Distro", f"{host.distro}, {host.kernel}"),
        ("Session", f"{host.session}, {host.desktop}"),
        ("GPU", host.gpu or "-"),
    )
    for index, (key, value) in enumerate(items):
        item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        key_label = Gtk.Label(label=key, xalign=0)
        key_label.add_css_class("info-key")
        value_label = Gtk.Label(label=value, xalign=0)
        value_label.set_ellipsize(Pango.EllipsizeMode.END)
        value_label.set_tooltip_text(value)
        if index == len(items) - 1:
            item.set_hexpand(True)
            value_label.set_hexpand(True)
            value_label.set_halign(Gtk.Align.START)
        item.append(key_label)
        item.append(value_label)
        strip.append(item)
    return strip


def build_main(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    config_strip = ConfigStrip(config)

    # Banner: full window width, height from the image's own aspect ratio.
    banner = data_file("header", "frostfire_installer_header.png")
    banner_height = _banner_height(banner)
    window_height = _CHROME_HEIGHT + banner_height

    # --- Footer button: opens the settings window ------------------------
    settings_button = Gtk.Button()
    settings_button.add_css_class("bn-footer")
    settings_button.set_hexpand(True)
    settings_button.set_tooltip_text("Open settings")
    footer_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    footer_content.set_hexpand(True)
    footer_label = Gtk.Label(label="Settings", xalign=0)
    footer_spacer = Gtk.Box()
    footer_spacer.set_hexpand(True)
    footer_icon = _icon(MATERIAL["settings"], filled=True)
    footer_content.append(footer_label)
    footer_content.append(footer_spacer)
    footer_content.append(footer_icon)
    settings_button.set_child(footer_content)
    settings_button.connect("clicked", lambda *_: _open_settings(window))

    # --- Column: banner + run controls + settings entry ------------------
    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    if banner is not None:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(banner), WINDOW_WIDTH, banner_height, True
        )
        # A DrawingArea has no natural size beyond its request, so the banner
        # stays exactly this tall and never rescales when the window grows.
        area = Gtk.DrawingArea()
        area.set_size_request(WINDOW_WIDTH, banner_height)
        area.set_hexpand(True)
        area.set_vexpand(False)
        area.set_valign(Gtk.Align.START)
        area.set_draw_func(_draw_banner, pixbuf)
        column.append(area)
    column.append(_system_strip())
    column.append(config_strip)
    run_bar = RunBar()
    if hasattr(window, "set_run_bar"):
        window.set_run_bar(run_bar)  # type: ignore[attr-defined]
    column.append(run_bar)

    recommendations = recommend.collect(config)
    warns = [item for item in recommendations if item.level == "warn"]
    if warns:
        report_items = recommend.report(config)
        rec_bar = RecommendationBar(warns, lambda: _show_recommendations(window, report_items))
        column.append(rec_bar)

    activity_bar = ActivityBar()
    column.append(activity_bar)
    column.append(settings_button)

    if hasattr(window, "register_state"):
        window.register_state(config_strip.refresh)  # type: ignore[attr-defined]
        window.register_state(run_bar.refresh)  # type: ignore[attr-defined]
    if hasattr(window, "register_activity"):
        window.register_activity(activity_bar)  # type: ignore[attr-defined]
    window.set_default_size(WINDOW_WIDTH, window_height)  # type: ignore[attr-defined]
    view = _toolbar_page("Frostfire Installer", column)
    if hasattr(window, "set_title_widget"):
        window.set_title_widget(view.title_widget)  # type: ignore[attr-defined]
    return view


def _open_settings(window: Adw.ApplicationWindow) -> None:
    """Open (or re-focus) the standalone settings window."""
    from .settings import SettingsWindow

    existing = getattr(window, "_settings_window", None)
    if existing is not None:
        existing.present()
        return
    settings = SettingsWindow(window)
    window._settings_window = settings  # type: ignore[attr-defined]
    settings.present()


# --- Handlers ------------------------------------------------------------
def _run_action(
    window: Adw.ApplicationWindow,
    button: Gtk.Button,
    busy: str,
    work: Callable[[Callable[[str], None]], Any],
    finished: Callable[[Any], str],
) -> None:
    """Run *work* off the GTK thread with the activity strip and toasts around it.

    *work* receives a thread-safe progress reporter; *finished* turns its result
    into the success toast.
    """
    win: Any = window
    button.set_sensitive(False)
    report = _reporter(window)
    win.set_activity(busy)
    win.toast(busy)

    def done(result: Any) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        _refresh_root(window)
        win.toast(finished(result))

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        win.toast(f"Error: {exc}")

    run_async(lambda: work(report), done, error)


def _repair(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    def work(report: Callable[[str], None]) -> None:
        config = Config.load()
        health.remediate(config)
        service.launch(config, service.ensure(config, on_progress=report))

    _run_action(window, button, "Repairing ...", work, lambda _: "Repaired and started")


def _reinstall(
    window: Adw.ApplicationWindow,
    button: Gtk.Button,
    keep_games: Gtk.CheckButton,
    keep_installer: Gtk.CheckButton,
) -> None:
    games = keep_games.get_active()
    remove_installer = not keep_installer.get_active()

    def work(report: Callable[[str], None]) -> None:
        config = Config.load()
        build = proton.find(config.proton_name)
        if build is None:
            raise RuntimeError("No Proton found")
        battlenet.reinstall(
            config,
            build,
            keep_games=games,
            remove_installer=remove_installer,
            on_progress=report,
        )

    _run_action(
        window,
        button,
        "Reinstalling Battle.net ...",
        work,
        lambda _: "Reinstalled" + (" (games kept)" if games else ""),
    )


def _remove(
    window: Adw.ApplicationWindow,
    button: Gtk.Button,
    keep_games: Gtk.CheckButton,
    keep_installer: Gtk.CheckButton,
) -> None:
    games = keep_games.get_active()
    remove_installer = not keep_installer.get_active()

    def work(report: Callable[[str], None]) -> None:
        battlenet.remove(
            Config.load(),
            keep_games=games,
            remove_installer=remove_installer,
            on_progress=report,
        )

    _run_action(
        window,
        button,
        "Removing Battle.net ...",
        work,
        lambda _: "Battle.net removed" + (" (games kept)" if games else ""),
    )


def _pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    _refresh_root(window)
    window.toast(f"Runner set to {name}")  # type: ignore[attr-defined]


def _pick_gpu(window: Adw.ApplicationWindow, preference: str) -> None:
    try:
        service.set_gpu_preference(preference)
    except (OSError, ValueError) as exc:
        window.toast(f"Failed: {exc}")  # type: ignore[attr-defined]
        return
    _refresh_root(window)
    window.toast("Graphics choice saved - restart Battle.net and the game.")  # type: ignore[attr-defined]


def _help_button(text: str) -> Gtk.Widget:
    label = Gtk.Label(label=text)
    label.set_wrap(True)
    label.set_max_width_chars(42)
    label.set_margin_top(10)
    label.set_margin_bottom(10)
    label.set_margin_start(10)
    label.set_margin_end(10)

    popover = Gtk.Popover()
    popover.set_child(label)

    button = Gtk.MenuButton()
    button.set_icon_name("help-about-symbolic")
    button.add_css_class("help-button")
    button.set_valign(Gtk.Align.CENTER)
    button.set_popover(popover)
    return button


def _gamescope_is_risky() -> bool:
    """True when nesting gamescope here is known to risk a strobing screen.

    NVIDIA's proprietary driver on a Wayland session is the combination that
    bites: presentation between gamescope and the outer compositor can collapse
    and flash the whole display. That is a photosensitivity hazard, not a
    cosmetic glitch, so it is called out on the switch itself rather than left
    for the user to discover.
    """
    version, _is_open = recommend.nvidia_driver_info()
    return version is not None and distro.detect().session == "Wayland"


def _switch(
    config: Config,
    title: str,
    key: str,
    tool: str,
    help_text: str,
    extra: Gtk.Widget | None = None,
    on_toggle: Callable[[bool], None] | None = None,
) -> Adw.SwitchRow:
    missing = shutil.which(tool) is None
    if missing:
        help_text = f"WARNING: {tool} is not installed.\n\n{help_text}"

    row = Adw.SwitchRow(title=title)
    row.set_active(bool(getattr(config.performance, key)))
    if missing:
        row.add_css_class("row-inactive")
    if extra is not None:
        row.add_suffix(extra)
    help_button = _help_button(help_text)
    if missing:
        help_button.add_css_class("help-warn")
    row.add_suffix(help_button)

    def on_active(row: Adw.SwitchRow, _pspec: object) -> None:
        if missing and row.get_active():
            row.set_active(False)
            root = row.get_root()
            if root is not None and hasattr(root, "toast"):
                root.toast(f"{tool} is not installed")  # type: ignore[attr-defined]
            return
        cfg = Config.load()
        setattr(cfg.performance, key, row.get_active())
        cfg.save()
        if on_toggle is not None:
            on_toggle(row.get_active())

    row.connect("notify::active", on_active)
    return row


def _show_logs(window: Adw.ApplicationWindow) -> None:
    config = Config.load()
    logs = (
        sorted(config.log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if config.log_dir.is_dir()
        else []
    )
    names = [path.name for path in logs]

    dropdown = Gtk.DropDown.new_from_strings(names or ["(no logs)"])
    view = Gtk.TextView()
    view.set_monospace(True)
    view.set_editable(False)
    buffer = view.get_buffer()

    def show() -> None:
        index = dropdown.get_selected()
        if logs and 0 <= index < len(logs):
            text = logs[index].read_text(encoding="utf-8", errors="ignore")
            buffer.set_text(text[-50000:])

    dropdown.connect("notify::selected", lambda *_: show())
    show()

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    for margin in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{margin}")(12)
    box.append(dropdown)
    scroller = Gtk.ScrolledWindow(vexpand=True)
    scroller.set_child(view)
    box.append(scroller)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(Adw.HeaderBar())
    toolbar.set_content(box)

    dialog = Adw.Dialog()
    dialog.set_title("Logs")
    dialog.set_content_width(820)
    dialog.set_content_height(600)
    dialog.set_child(toolbar)
    dialog.present(window)


def _copy_to_clipboard(text: str) -> None:
    display = Gdk.Display.get_default()
    if display is not None:
        display.get_clipboard().set(text)


def _command_row(command: str) -> Gtk.Widget:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    entry = Gtk.Entry()
    entry.set_text(command)
    entry.set_editable(False)
    entry.set_hexpand(True)
    entry.add_css_class("monospace")
    button = _button("Copy")
    button.set_tooltip_text("Copy the command to the clipboard")

    def copy(*_args: object) -> None:
        _copy_to_clipboard(command)
        button.set_label("Copied")

    button.connect("clicked", copy)
    row.append(entry)
    row.append(button)
    return row


def _persistenced_control(window: Adw.ApplicationWindow) -> Gtk.Widget:
    """Reversible in-app mitigation: keep the GPU initialised (nvidia-persistenced)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    active = recommend.persistenced_state() == "active"
    button = _button(
        "Disable GPU persistence" if active else "Enable GPU persistence",
        primary=not active,
    )
    note = Gtk.Label(
        label="Reversible - run again to turn it off. Requires your password confirmation.",
        xalign=0,
    )
    note.set_wrap(True)
    note.add_css_class("section-desc")
    button.connect("clicked", lambda *_: _toggle_persistenced(window, button, note))
    box.append(button)
    box.append(note)
    return box


def _toggle_persistenced(
    window: Adw.ApplicationWindow, button: Gtk.Button, note: Gtk.Label
) -> None:
    enable = recommend.persistenced_state() != "active"
    button.set_sensitive(False)
    note.set_label("Waiting for authorisation ...")

    def work() -> None:
        service.set_persistenced(enable)

    def done(_result: object) -> None:
        button.set_sensitive(True)
        button.set_label("Disable GPU persistence" if enable else "Enable GPU persistence")
        note.set_label("Done - restart the game and test." if enable else "Turned off.")

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        note.set_label(f"Failed: {exc}")

    run_async(work, done, error)


def _show_recommendations(
    window: Adw.ApplicationWindow, items: list[recommend.Recommendation]
) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    for margin in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{margin}")(16)

    for item in items:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        glyph, tone = {
            "warn": (MATERIAL["info"], "fire"),
            "info": (MATERIAL["info"], "ice"),
            "ok": (MATERIAL["check"], "green"),
        }.get(item.level, (MATERIAL["info"], None))
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head.append(_icon(glyph, tone))
        title = Gtk.Label(xalign=0)
        title.set_markup(f"<b>{GLib.markup_escape_text(item.title)}</b>")
        title.set_wrap(True)
        head.append(title)
        card.append(head)

        if item.detail:
            detail = Gtk.Label(label=item.detail, xalign=0)
            detail.set_wrap(True)
            card.append(detail)

        if item.action:
            action = Gtk.Label(label=item.action, xalign=0)
            action.set_wrap(True)
            action.add_css_class("section-desc")
            card.append(action)

        for command in item.commands:
            card.append(_command_row(command))

        if item.action_id == "persistenced":
            card.append(_persistenced_control(window))
        box.append(card)

    scroller = Gtk.ScrolledWindow(vexpand=True)
    scroller.set_child(box)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(Adw.HeaderBar())
    toolbar.set_content(scroller)

    dialog = Adw.Dialog()
    dialog.set_title("Recommendations")
    dialog.set_content_width(620)
    dialog.set_content_height(540)
    dialog.set_child(toolbar)
    dialog.present(window)


def _show_about(window: Adw.ApplicationWindow) -> None:
    from .. import __version__

    dialog = Adw.AboutDialog(
        application_name="Frostfire Installer",
        application_icon="applications-games-symbolic",
        version=__version__,
        developer_name="frostfireinstaller contributors",
        comments="A Battle.net installer helper for Linux (umu-launcher + Proton).",
        license_type=Gtk.License.MIT_X11,
    )
    dialog.present(window)
