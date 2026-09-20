"""Single-column content for the main window.

Layout: window header bar (top) -> Frostfire banner -> all features as rows.

Scope: a Battle.net installer helper. Games are started from Blizzard's own
launcher, not here.
"""

from __future__ import annotations

import shutil

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, distro, health, proton  # noqa: E402
from .helpers import data_file, run_async  # noqa: E402


def _kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


# Material Symbols glyphs (subset of the variable font, see data/fonts).
MATERIAL = {
    "download": "\uf090",
    "play": "\ue037",
    "build": "\uf8cd",
    "stop": "\ue047",
    "refresh": "\ue5d5",
    "delete": "\ue92e",
    "log": "\ue873",
    "info": "\ue88e",
}


def _icon(glyph: str, tone: str | None = None) -> Gtk.Widget:
    label = Gtk.Label(label=glyph)
    label.add_css_class("material-icon")
    if tone is not None:
        label.add_css_class(f"icon-{tone}")
    return label


def _toolbar_page(title: str, content: Gtk.Widget) -> Adw.ToolbarView:
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    view.add_top_bar(header)
    view.set_content(content)
    return view


class RunBar(Gtk.Box):
    """Standalone Battle.net start/stop control (not part of any card)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("run-bar")

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_valign(Gtk.Align.CENTER)
        title = Gtk.Label(label="Battle.net", xalign=0)
        title.add_css_class("heading")
        self.status = Gtk.Label(xalign=0)
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

        self.button = Gtk.Button()
        self.button.set_valign(Gtk.Align.CENTER)
        self.button.set_child(content)
        self.button.connect("clicked", self._on_clicked)
        self.append(self.button)

        self.refresh()

    def _toast(self, message: str) -> None:
        root = self.get_root()
        if root is not None and hasattr(root, "toast"):
            root.toast(message)  # type: ignore[attr-defined]

    def refresh(self) -> None:
        running = health.running()

        self.status.set_label("Startat" if running else "Stoppat")
        self.status.remove_css_class("run-status-on")
        self.status.remove_css_class("run-status-off")
        self.status.add_css_class("run-status-on" if running else "run-status-off")

        self.icon.set_label(MATERIAL["stop"] if running else MATERIAL["play"])
        self.icon.remove_css_class("icon-red")
        self.icon.remove_css_class("icon-green")
        self.icon.add_css_class("icon-red" if running else "icon-green")

        self.label.set_label("Stoppa" if running else "Starta")
        if running:
            self.button.remove_css_class("suggested-action")
        else:
            self.button.add_css_class("suggested-action")

    def _on_clicked(self, button: Gtk.Button) -> None:
        if health.running():
            health.kill_all()
            self.refresh()
            self._toast("Stoppade Battle.net")
            return

        button.set_sensitive(False)
        self._toast("Startar Battle.net ...")

        def work() -> None:
            config = Config.load()
            service.launch(config, service.ensure(config))

        def done(_result: object) -> None:
            button.set_sensitive(True)
            self.refresh()
            self._toast("Startar Battle.net")

        def error(exc: Exception) -> None:
            button.set_sensitive(True)
            self._toast(f"Fel: {exc}")

        run_async(work, done, error)


def _info_strip(config: Config) -> Gtk.Widget:
    """Dark info strip below the banner: app + system information."""
    host = distro.detect()
    strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=48)
    strip.add_css_class("info-strip")

    def column(title: str, rows: list[tuple[str, str]]) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_hexpand(True)
        box.set_halign(Gtk.Align.START)
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("info-title")
        box.append(heading)
        for key, value in rows:
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            key_label = Gtk.Label(label=key, xalign=0)
            key_label.add_css_class("info-key")
            value_label = Gtk.Label(label=value, xalign=0)
            line.append(key_label)
            line.append(value_label)
            box.append(line)
        return box

    state = "Installerat" if battlenet.installed(config) else "Ej installerat"
    if health.running():
        state += ", körs"
    build = proton.find(config.proton_name)
    strip.append(
        column(
            "App",
            [
                ("Battle.net", state),
                ("Proton", build.name if build else "saknas"),
                ("Prefix", str(config.prefix)),
            ],
        )
    )
    strip.append(
        column(
            "System",
            [
                ("Distro", f"{host.distro}, {host.kernel}"),
                ("Session", f"{host.session}, {host.desktop}"),
                ("GPU", host.gpu or "-"),
            ],
        )
    )
    return strip


def build_main(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    page = Adw.PreferencesPage()

    # --- Maintenance (ice: preserve and keep running) --------------------
    maintenance = Adw.PreferencesGroup(title="Installation &amp; underhåll")
    maintenance.set_description("Is – bevara och hålla igång.")

    def action(
        title: str,
        subtitle: str,
        label: str,
        callback: object,
        suggested: bool = False,
        icon: str | None = None,
        tone: str | None = None,
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        if icon is not None:
            row.add_prefix(_icon(icon, tone))
        button = Gtk.Button(label=label)
        button.set_valign(Gtk.Align.CENTER)
        if suggested:
            button.add_css_class("suggested-action")
        button.connect("clicked", lambda *_: callback(button))  # type: ignore[operator]
        row.add_suffix(button)
        return row

    installed = battlenet.installed(config)
    install_row: Adw.ActionRow = action(
        "Verifiera Battle.net" if installed else "Installera Battle.net",
        "Klienten är installerad" if installed else "Klienten är inte installerad",
        "Verifiera" if installed else "Installera",
        lambda b: _ensure(window, b, install_row),
        suggested=True,
        icon=MATERIAL["download"],
        tone="ice",
    )
    maintenance.add(install_row)
    maintenance.add(
        action(
            "Reparera",
            "Stoppa, rensa CEF/cache och starta om",
            "Reparera",
            lambda b: _repair(window, b),
            icon=MATERIAL["build"],
            tone="ice",
        )
    )
    page.add(maintenance)

    # --- Destructive (fire: reinstall / remove) --------------------------
    destructive = Adw.PreferencesGroup(title="Återställ &amp; ta bort")
    destructive.set_description("Eld – förstörande åtgärder.")

    keep_games = Adw.SwitchRow(
        title="Behåll spel",
        subtitle="Behåll installerade spel vid återinstallation eller borttagning",
    )
    keep_games.set_active(True)
    destructive.add(keep_games)
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
            lambda b: _remove(window, b, keep_games),
            icon=MATERIAL["delete"],
            tone="fire",
        )
    )
    page.add(destructive)

    # --- Performance -----------------------------------------------------
    performance = Adw.PreferencesGroup(title="Prestanda")
    performance.set_description(
        "Gäller spelen du startar från Battle.net (samma Wine-session), inte bara launchern."
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
    page.add(performance)

    # --- Runner ----------------------------------------------------------
    runners = Adw.PreferencesGroup(title="Runner")
    runners.set_description("Vilken Proton som används. Sparas i config.toml.")
    current = proton.find(config.proton_name)
    builds = proton.all_builds()
    if not builds:
        runners.add(
            Adw.ActionRow(title="Inga Proton-byggen hittades", subtitle="Installera via ProtonPlus")
        )
    for candidate in builds:
        row = Adw.ActionRow(title=candidate.name, subtitle=str(candidate))
        if candidate == current:
            row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        button = Gtk.Button(label="Använd")
        button.set_valign(Gtk.Align.CENTER)
        button.connect("clicked", lambda _b, name=candidate.name: _pick_runner(window, name))
        row.add_suffix(button)
        runners.add(row)
    page.add(runners)

    # --- Logs ------------------------------------------------------------
    logs = Adw.PreferencesGroup(title="Loggar")
    logs.add(
        action(
            "Visa loggar",
            "Körnings- och installationsloggar",
            "Visa",
            lambda _b: _show_logs(window),
            icon=MATERIAL["log"],
        )
    )
    page.add(logs)

    # --- Paths -----------------------------------------------------------
    paths = Adw.PreferencesGroup(title="Sökvägar")
    paths.add(_kv("Installerare", str(config.installer)))
    paths.add(_kv("Config", str(config.config_file)))
    paths.add(_kv("Loggar", str(config.log_dir)))
    page.add(paths)

    # --- About -----------------------------------------------------------
    about = Adw.PreferencesGroup(title="Om")
    row = Adw.ActionRow(title="Frostfire Installer")
    row.add_prefix(_icon(MATERIAL["info"]))
    button = Gtk.Button(label="Om")
    button.set_valign(Gtk.Align.CENTER)
    button.connect("clicked", lambda *_: _show_about(window))
    row.add_suffix(button)
    about.add(row)
    page.add(about)

    # --- Advanced: hidden by default to keep the app simple --------------
    advanced = [performance, runners, paths, about]
    for group in advanced:
        group.set_visible(False)

    advanced_group = Adw.PreferencesGroup(title="Avancerat")
    show_advanced = Adw.SwitchRow(
        title="Visa avancerat",
        subtitle="Prestanda, runner, sökvägar och diagnostik",
    )

    def on_show(row: Adw.SwitchRow, _pspec: object) -> None:
        for group in advanced:
            group.set_visible(row.get_active())

    show_advanced.connect("notify::active", on_show)
    advanced_group.add(show_advanced)
    page.add(advanced_group)

    # --- Column: banner on top, everything else below --------------------
    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    banner = data_file("header", "frostfire_installer_header_1.png")
    if banner is not None:
        picture = Gtk.Picture.new_for_filename(str(banner))
        picture.set_content_fit(Gtk.ContentFit.FILL)
        frame = Gtk.AspectFrame(ratio=1600 / 515, obey_child=False)
        frame.set_child(picture)
        frame.set_hexpand(True)
        column.append(frame)
    column.append(_info_strip(config))
    column.append(RunBar())
    page.set_vexpand(True)
    column.append(page)
    return _toolbar_page("Frostfire Installer", column)


# --- Handlers ------------------------------------------------------------
def _ensure(window: Adw.ApplicationWindow, button: Gtk.Button, row: Adw.ActionRow) -> None:
    button.set_sensitive(False)
    window.toast("Verifierar/installerar ...")  # type: ignore[attr-defined]

    def work() -> str:
        return str(service.ensure(Config.load()))

    def done(build: str) -> None:
        button.set_sensitive(True)
        row.set_title("Verifiera Battle.net")
        row.set_subtitle("Klienten är installerad")
        button.set_label("Verifiera")
        window.toast(f"Klart – Proton: {build}")  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _repair(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)
    window.toast("Reparerar ...")  # type: ignore[attr-defined]

    def work() -> None:
        config = Config.load()
        health.remediate(config)
        service.launch(config, service.ensure(config))

    def done(_result: object) -> None:
        button.set_sensitive(True)
        window.toast("Reparerat och startat")  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _reinstall(window: Adw.ApplicationWindow, button: Gtk.Button, keep: Adw.SwitchRow) -> None:
    button.set_sensitive(False)
    keep_games = keep.get_active()
    window.toast("Återinstallerar Battle.net ...")  # type: ignore[attr-defined]

    def work() -> str:
        config = Config.load()
        build = proton.find(config.proton_name)
        if build is None:
            raise RuntimeError("Ingen Proton hittad")
        return str(battlenet.reinstall(config, build, keep_games=keep_games))

    def done(_log_path: str) -> None:
        button.set_sensitive(True)
        window.toast("Återinstallerat" + (" (spel behållna)" if keep_games else ""))  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _remove(window: Adw.ApplicationWindow, button: Gtk.Button, keep: Adw.SwitchRow) -> None:
    button.set_sensitive(False)
    keep_games = keep.get_active()
    window.toast("Tar bort Battle.net ...")  # type: ignore[attr-defined]

    def work() -> None:
        battlenet.remove(Config.load(), keep_games=keep_games)

    def done(_result: object) -> None:
        button.set_sensitive(True)
        window.toast("Battle.net borttaget" + (" (spel behållna)" if keep_games else ""))  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    window.toast(f"Runner satt till {name}")  # type: ignore[attr-defined]


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
    button.add_css_class("flat")
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
