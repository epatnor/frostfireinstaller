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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gdk, GdkPixbuf, GLib, Gtk, Pango  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, distro, health, proton, recommend  # noqa: E402
from .helpers import data_file, run_async  # noqa: E402


def _kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


def _installer_state(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError:
        return "saknas, laddas ner vid nästa start"
    return f"{size / 1024**2:.1f} MB, nedladdad och cachad"


# Material Symbols glyphs (subset of the variable font, see data/fonts).
MATERIAL = {
    "download": "\uf090",
    "play": "\ue037",
    "build": "\uf8cd",
    "stop": "\ue047",
    "refresh": "\ue5d5",
    "delete": "\ue92e",
    "info": "\ue88e",
    "expand": "\ue5cf",
    "collapse": "\ue5ce",
    "check": "\ue5ca",
}

# Banner size: the window is locked to this width (608) and the picture is
# scaled to match at load, so it fills the width and never changes between
# collapsed/expanded. Height is ~20% smaller than the full-width banner.
BANNER_HEIGHT = 198
BANNER_WIDTH = round(BANNER_HEIGHT * 1600 / 521)


def _icon(glyph: str, tone: str | None = None) -> Gtk.Label:
    label = Gtk.Label(label=glyph)
    label.add_css_class("material-icon")
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
    """A Battle.net-style section: uppercase label plus a bordered row panel."""

    def __init__(self, title: str, description: str | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("bn-section")

        heading = Gtk.Label(label=title.upper(), xalign=0)
        heading.add_css_class("section-title")
        self.append(heading)

        if description is not None:
            note = Gtk.Label(label=description, xalign=0)
            note.set_wrap(True)
            note.add_css_class("section-desc")
            self.append(note)

        self.rows = Gtk.ListBox()
        self.rows.set_selection_mode(Gtk.SelectionMode.NONE)
        self.rows.add_css_class("bn-panel")
        self.append(self.rows)

    def add(self, row: Gtk.Widget) -> None:
        self.rows.append(row)


def _toolbar_page(title: str, content: Gtk.Widget) -> Adw.ToolbarView:
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    view.add_top_bar(header)
    view.set_content(content)
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

        button = _button("Visa", primary=warn)
        button.set_tooltip_text("Visa rekommendationer och kommandon")
        button.connect("clicked", lambda *_: on_show())
        self.append(button)


class ClientRow(Adw.ActionRow):
    """Client state with the repair action in the same row."""

    def __init__(self, on_repair: Callable[[Gtk.Button], None]) -> None:
        super().__init__(title="Battle.net")
        self.add_prefix(_icon(MATERIAL["build"], "ice"))
        button = _button("Reparera", tooltip="Stoppa, rensa CEF/cache och starta om")
        button.connect("clicked", lambda *_: on_repair(button))
        self.add_suffix(button)
        self.refresh()

    def refresh(self) -> None:
        installed = battlenet.installed(Config.load())
        self.set_subtitle(
            "Klienten är installerad" if installed else "Klienten är inte installerad"
        )


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

        self.icon = _icon(MATERIAL["play"])
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
            state, tone = "Startat", "status-on"
        elif installed:
            state, tone = "Stoppat", "status-off"
        else:
            state, tone = "Ej installerat", "status-missing"

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
            self.label.set_label("Stoppa")
            self.button.set_tooltip_text("Stoppar Battle.net")
            self.button.add_css_class("bn-btn")
        elif installed:
            self.label.set_label("Starta")
            self.button.set_tooltip_text("Startar Battle.net")
            self.button.add_css_class("bn-btn-primary")
        else:
            self.label.set_label("Installera")
            self.button.set_tooltip_text("Installerar Battle.net och startar klienten")
            self.button.add_css_class("bn-btn-primary")

    def _on_clicked(self, button: Gtk.Button) -> None:
        if health.running():
            health.kill_all()
            _refresh_root(self)
            self._toast("Stoppade Battle.net")
            return

        root = self.get_root()
        button.set_sensitive(False)
        report = _reporter(root)
        report("Förbereder ...")
        self._toast("Startar Battle.net ...")

        def work() -> None:
            config = Config.load()
            service.launch(config, service.ensure(config, on_progress=report))

        def done(_result: object) -> None:
            button.set_sensitive(True)
            _clear_activity(root)
            _refresh_root(self)
            self._toast("Startar Battle.net")

        def error(exc: Exception) -> None:
            button.set_sensitive(True)
            _clear_activity(root)
            self._toast(f"Fel: {exc}")

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
        self.proton.set_label(build.name if build else "saknas")
        self.proton.remove_css_class("config-warn")
        self.proton.set_tooltip_text(str(build) if build else "Ingen Proton hittad")
        if build is None:
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
    sections = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    sections.add_css_class("bn-sections")

    def action(
        title: str,
        subtitle: str,
        label: str,
        callback: object,
        primary: bool = False,
        danger: bool = False,
        icon: str | None = None,
        tone: str | None = None,
        options: list[Gtk.Widget] | None = None,
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        if icon is not None:
            row.add_prefix(_icon(icon, tone))
        for widget in options or []:
            row.add_suffix(widget)
        button = _button(label, primary=primary, danger=danger)
        button.connect("clicked", lambda *_: callback(button))  # type: ignore[operator]
        row.add_suffix(button)
        return row

    # --- Maintenance (ice: preserve and keep running) --------------------
    maintenance = Section("Installation & underhåll")
    client_row = ClientRow(lambda b: _repair(window, b))
    maintenance.add(client_row)
    sections.append(maintenance)

    # --- Destructive (fire: reinstall / remove) --------------------------
    destructive = Section("Återställ & ta bort")

    keep_games = Adw.SwitchRow(
        title="Behåll spel",
        subtitle="Behåll installerade spel vid återinstallation eller borttagning",
    )
    keep_games.set_active(True)
    destructive.add(keep_games)

    drop_installer = Gtk.CheckButton(label="Även installeraren")
    drop_installer.set_valign(Gtk.Align.CENTER)
    drop_installer.set_tooltip_text(
        "Raderar nedladdad Battle.net-Setup.exe – nästa start laddar ner den igen"
    )

    destructive.add(
        action(
            "Återinstallera Battle.net",
            "Tar bort klienten och installerar om",
            "Återinstallera",
            lambda b: _reinstall(window, b, keep_games),
            icon=MATERIAL["refresh"],
            tone="fire",
        )
    )
    destructive.add(
        action(
            "Ta bort Battle.net",
            "Tar bort klienten (spelen behålls om växeln är på)",
            "Ta bort",
            lambda b: _remove(window, b, keep_games, drop_installer),
            danger=True,
            icon=MATERIAL["delete"],
            tone="fire",
            options=[drop_installer],
        )
    )
    sections.append(destructive)

    # --- Performance -----------------------------------------------------
    performance = Section(
        "Prestanda",
        "Gäller spelen du startar från Battle.net (samma Wine-session), inte bara launchern.",
    )
    performance.add(
        _switch(
            config,
            "MangoHud",
            "FPS/GPU-overlay",
            "mangohud",
            "mangohud",
            "Visar FPS, frame time, GPU/CPU-last och temperatur ovanpå spelet. "
            "Påverkar inte prestandan, bara diagnostik. Följer med ner i spelen "
            "eftersom de kör i samma Wine-session.",
        )
    )
    performance.add(
        _switch(
            config,
            "GameMode",
            "Optimera systemet under spel",
            "gamemode",
            "gamemode",
            "Justerar systemet tillfälligt medan Battle.net och spelen kör: "
            "CPU-governor till performance och mindre bakgrundsstök. Kan ge några "
            "procent jämnare FPS. Kräver paketet gamemode.",
        )
    )
    performance.add(
        _switch(
            config,
            "Gamescope",
            "Nästlad compositor (kan hjälpa på Wayland)",
            "gamescope",
            "gamescope",
            "Kör Battle.net och spelen i en nästlad compositor. Kan skala "
            "upplösning, köra FSR-uppskalning och låsa FPS, samt lösa "
            "Wayland-fönsterproblem. Låt vara av om allt fungerar.",
        )
    )
    sections.append(performance)

    # --- Runner ----------------------------------------------------------
    runners = Section("Runner", "Vilken Proton som används. Sparas i config.toml.")
    current = proton.find(config.proton_name)
    builds = proton.all_builds()
    if not builds:
        runners.add(
            Adw.ActionRow(title="Inga Proton-byggen hittades", subtitle="Installera via ProtonPlus")
        )
    group: Gtk.CheckButton | None = None
    for candidate in builds:
        row = Adw.ActionRow(title=candidate.name, subtitle=str(candidate))
        radio = Gtk.CheckButton()
        radio.set_valign(Gtk.Align.CENTER)
        radio.set_tooltip_text(f"Använd {candidate.name}")
        if group is None:
            group = radio
        else:
            radio.set_group(group)
        radio.set_active(candidate == current)
        radio.connect(
            "toggled",
            lambda button, name=candidate.name: (
                _pick_runner(window, name) if button.get_active() else None
            ),
        )
        row.add_prefix(radio)
        runners.add(row)
    sections.append(runners)

    # --- Graphics (advanced) --------------------------------------------
    graphics = Section(
        "Grafik",
        "Vilket grafikkort spelen använder. Sparas i config.toml. Reversibelt – byt när som helst.",
    )
    preference = recommend.gpu_preference(config)
    integrated = recommend.integrated_gpu_name() or "AMD"
    gpu_options = (
        ("auto", "Auto", "Spelet får välja (NVIDIA på den här maskinen)"),
        ("nvidia", "NVIDIA", 'Tvingar DXVK_FILTER_DEVICE_NAME = "NVIDIA"'),
        (
            "integrated",
            f"Integrerad ({integrated})",
            "Samma kort som skärmen. Felsökningsläge om NVIDIA-vägen ger GPU-häng.",
        ),
    )
    gpu_group: Gtk.CheckButton | None = None
    for value, title, subtitle in gpu_options:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        radio = Gtk.CheckButton()
        radio.set_valign(Gtk.Align.CENTER)
        radio.set_tooltip_text(f"Använd {title}")
        if gpu_group is None:
            gpu_group = radio
        else:
            radio.set_group(gpu_group)
        radio.set_active(value == preference)
        radio.connect(
            "toggled",
            lambda button, val=value: _pick_gpu(window, val) if button.get_active() else None,
        )
        row.add_prefix(radio)
        graphics.add(row)
    sections.append(graphics)

    # --- Paths (advanced) ------------------------------------------------
    paths = Section("Sökvägar", "Var saker ligger. Installeraren cachas och återanvänds.")
    installer_row = Adw.ActionRow(title="Installerare")
    open_button = _button("Öppna mapp", tooltip="Öppna mappen där installeraren cachas")
    open_button.connect("clicked", lambda *_: _open_folder(config.bnet_dir))
    installer_row.add_suffix(open_button)
    paths.add(installer_row)

    def refresh_installer() -> None:
        installer_row.set_subtitle(f"{config.installer}, {_installer_state(config.installer)}")

    refresh_installer()
    paths.add(_kv("Config", str(config.config_file)))

    log_row = Adw.ActionRow(title="Loggar", subtitle=str(config.log_dir))
    log_button = _button("Visa", tooltip="Körnings- och installationsloggar")
    log_button.connect("clicked", lambda *_: _show_logs(window))
    log_row.add_suffix(log_button)
    paths.add(log_row)
    sections.append(paths)

    # --- Diagnostics -----------------------------------------------------
    diagnostics = Section("Diagnostik", "Kontrollerar drivrutin, runner, utrymme med mera.")
    diag_row = Adw.ActionRow(
        title="Systemkontroll", subtitle="Visa status för alla kända fallgropar"
    )
    diag_button = _button("Kör", tooltip="Kör systemkontrollen")
    diag_button.connect(
        "clicked", lambda *_: _show_recommendations(window, recommend.report(Config.load()))
    )
    diag_row.add_suffix(diag_button)
    diagnostics.add(diag_row)
    sections.append(diagnostics)

    # --- About -----------------------------------------------------------
    about = Section("Om")
    row = Adw.ActionRow(title="Frostfire Installer")
    row.add_prefix(_icon(MATERIAL["info"]))
    button = _button("Om")
    button.connect("clicked", lambda *_: _show_about(window))
    row.add_suffix(button)
    about.add(row)
    sections.append(about)

    # --- Hide maintenance/destructive when there is no client ------------
    def refresh_sections() -> None:
        installed = battlenet.installed(Config.load())
        maintenance.set_visible(installed)
        destructive.set_visible(installed)

    refresh_sections()

    # --- Advanced content: the maintenance/destructive/… sections -------
    config_strip = ConfigStrip(config)

    scroller = Gtk.ScrolledWindow(vexpand=True)
    scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroller.set_propagate_natural_width(False)
    scroller.set_child(sections)
    scroller.set_visible(False)

    # --- Footer expander (fixed, right under the Battle.net band) --------
    footer = Gtk.Button()
    footer.add_css_class("bn-footer")
    footer.set_hexpand(True)
    footer_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    footer_content.set_hexpand(True)
    footer_label = Gtk.Label(label="Visa avancerat", xalign=0)
    footer_spacer = Gtk.Box()
    footer_spacer.set_hexpand(True)
    footer_icon = _icon(MATERIAL["expand"])
    footer_content.append(footer_label)
    footer_content.append(footer_spacer)
    footer_content.append(footer_icon)
    footer.set_child(footer_content)

    expanded = {"open": False}

    def toggle_advanced(*_args: object) -> None:
        expanded["open"] = not expanded["open"]
        scroller.set_visible(expanded["open"])
        footer_label.set_label("Dölj avancerat" if expanded["open"] else "Visa avancerat")
        footer_icon.set_label(MATERIAL["collapse"] if expanded["open"] else MATERIAL["expand"])
        # Only the height changes; the width is locked by the window.
        window.set_default_size(608, 770 if expanded["open"] else 350)  # type: ignore[attr-defined]
        window.queue_resize()  # type: ignore[attr-defined]

    footer.connect("clicked", toggle_advanced)

    # --- Column: banner + run controls, advanced content below -----------
    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    banner = data_file("header", "frostfire_installer_header.png")
    if banner is not None:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(banner), BANNER_WIDTH, BANNER_HEIGHT, True
        )
        picture = Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
        picture.set_content_fit(Gtk.ContentFit.FILL)
        picture.set_size_request(BANNER_WIDTH, BANNER_HEIGHT)
        picture.set_hexpand(True)
        picture.set_valign(Gtk.Align.START)
        column.append(picture)
    column.append(_system_strip())
    column.append(config_strip)
    run_bar = RunBar()
    column.append(run_bar)

    recommendations = recommend.collect(config)
    warns = [item for item in recommendations if item.level == "warn"]
    if warns:
        report_items = recommend.report(config)
        rec_bar = RecommendationBar(warns, lambda: _show_recommendations(window, report_items))
        column.append(rec_bar)

    activity_bar = ActivityBar()
    column.append(activity_bar)
    column.append(footer)
    column.append(scroller)

    if hasattr(window, "register_state"):
        window.register_state(client_row.refresh)  # type: ignore[attr-defined]
        window.register_state(config_strip.refresh)  # type: ignore[attr-defined]
        window.register_state(run_bar.refresh)  # type: ignore[attr-defined]
        window.register_state(refresh_sections)  # type: ignore[attr-defined]
        window.register_state(refresh_installer)  # type: ignore[attr-defined]
    if hasattr(window, "register_activity"):
        window.register_activity(activity_bar)  # type: ignore[attr-defined]
    return _toolbar_page("Frostfire Installer", column)


# --- Handlers ------------------------------------------------------------
def _repair(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)
    report = _reporter(window)
    window.set_activity("Reparerar ...")  # type: ignore[attr-defined]
    window.toast("Reparerar ...")  # type: ignore[attr-defined]

    def work() -> None:
        config = Config.load()
        health.remediate(config)
        service.launch(config, service.ensure(config, on_progress=report))

    def done(_result: object) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        _refresh_root(window)
        window.toast("Reparerat och startat")  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _reinstall(window: Adw.ApplicationWindow, button: Gtk.Button, keep: Adw.SwitchRow) -> None:
    button.set_sensitive(False)
    keep_games = keep.get_active()
    report = _reporter(window)
    window.set_activity("Återinstallerar Battle.net ...")  # type: ignore[attr-defined]
    window.toast("Återinstallerar Battle.net ...")  # type: ignore[attr-defined]

    def work() -> str:
        config = Config.load()
        build = proton.find(config.proton_name)
        if build is None:
            raise RuntimeError("Ingen Proton hittad")
        return str(battlenet.reinstall(config, build, keep_games=keep_games, on_progress=report))

    def done(_log_path: str) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        _refresh_root(window)
        window.toast("Återinstallerat" + (" (spel behållna)" if keep_games else ""))  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _remove(
    window: Adw.ApplicationWindow,
    button: Gtk.Button,
    keep: Adw.SwitchRow,
    drop: Gtk.CheckButton,
) -> None:
    button.set_sensitive(False)
    keep_games = keep.get_active()
    remove_installer = drop.get_active()
    report = _reporter(window)
    window.set_activity("Tar bort Battle.net ...")  # type: ignore[attr-defined]
    window.toast("Tar bort Battle.net ...")  # type: ignore[attr-defined]

    def work() -> None:
        battlenet.remove(
            Config.load(),
            keep_games=keep_games,
            remove_installer=remove_installer,
            on_progress=report,
        )

    def done(_result: object) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        _refresh_root(window)
        window.toast("Battle.net borttaget" + (" (spel behållna)" if keep_games else ""))  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        _clear_activity(window)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    _refresh_root(window)
    window.toast(f"Runner satt till {name}")  # type: ignore[attr-defined]


def _pick_gpu(window: Adw.ApplicationWindow, preference: str) -> None:
    try:
        service.set_gpu_preference(preference)
    except (OSError, ValueError) as exc:
        window.toast(f"Misslyckades: {exc}")  # type: ignore[attr-defined]
        return
    _refresh_root(window)
    window.toast("Grafikval sparat – starta om Battle.net och spelet.")  # type: ignore[attr-defined]


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
    button.add_css_class("bn-btn-flat")
    button.set_valign(Gtk.Align.CENTER)
    button.set_popover(popover)
    return button


def _switch(
    config: Config,
    title: str,
    subtitle: str,
    key: str,
    tool: str,
    help_text: str,
) -> Adw.SwitchRow:
    row = Adw.SwitchRow(title=title, subtitle=subtitle)
    row.set_active(bool(getattr(config.performance, key)))
    row.add_suffix(_help_button(help_text))

    if shutil.which(tool) is None:
        row.set_sensitive(False)
        row.set_subtitle(f"{subtitle} – {tool} är inte installerat")
        return row

    def on_active(row: Adw.SwitchRow, _pspec: object) -> None:
        cfg = Config.load()
        setattr(cfg.performance, key, row.get_active())
        cfg.save()

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

    dropdown = Gtk.DropDown.new_from_strings(names or ["(inga loggar)"])
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
    dialog.set_title("Loggar")
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
    button = _button("Kopiera")
    button.set_tooltip_text("Kopiera kommandot till urklipp")

    def copy(*_args: object) -> None:
        _copy_to_clipboard(command)
        button.set_label("Kopierat")

    button.connect("clicked", copy)
    row.append(entry)
    row.append(button)
    return row


def _persistenced_control(window: Adw.ApplicationWindow) -> Gtk.Widget:
    """Reversible in-app mitigation: keep the GPU initialised (nvidia-persistenced)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    active = recommend.persistenced_state() == "active"
    button = _button(
        "Inaktivera GPU-persistens" if active else "Aktivera GPU-persistens",
        primary=not active,
    )
    note = Gtk.Label(
        label="Reversibelt – kör igen för att stänga av. Kräver din lösenordsbekräftelse.",
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
    note.set_label("Väntar på godkännande ...")

    def work() -> None:
        service.set_persistenced(enable)

    def done(_result: object) -> None:
        button.set_sensitive(True)
        button.set_label("Inaktivera GPU-persistens" if enable else "Aktivera GPU-persistens")
        note.set_label("Klart – starta om spelet och testa." if enable else "Avstängt.")

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        note.set_label(f"Misslyckades: {exc}")

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
    dialog.set_title("Rekommendationer")
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
