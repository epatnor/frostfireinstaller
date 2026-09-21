"""Single-column content for the main window.

Layout: window header bar (top) -> Frostfire banner -> all features as rows.

Scope: a Battle.net installer helper. Games are started from Blizzard's own
launcher, not here.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, distro, health, proton  # noqa: E402
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


def _refresh_root(widget: Gtk.Widget) -> None:
    """Ask the window to refresh every widget that shows client state."""
    root = widget.get_root()
    if root is not None and hasattr(root, "refresh_state"):
        root.refresh_state()  # type: ignore[attr-defined]


class ClientRow(Adw.ActionRow):
    """Client state with the repair action in the same row."""

    def __init__(self, on_repair: Callable[[Gtk.Button], None]) -> None:
        super().__init__(title="Battle.net")
        self.add_prefix(_icon(MATERIAL["build"], "ice"))
        button = Gtk.Button(label="Reparera")
        button.set_valign(Gtk.Align.CENTER)
        button.set_tooltip_text("Stoppa, rensa CEF/cache och starta om")
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
        config = Config.load()
        running = health.running()
        installed = battlenet.installed(config)

        if running:
            state = "Startat"
        elif installed:
            state = "Stoppat"
        else:
            state = "Ej installerat"
        self.status.set_label(state)
        self.status.remove_css_class("run-status-on")
        self.status.remove_css_class("run-status-off")
        self.status.add_css_class("run-status-on" if running else "run-status-off")

        if running:
            glyph = MATERIAL["stop"]
        else:
            glyph = MATERIAL["play"] if installed else MATERIAL["download"]
        self.icon.set_label(glyph)
        self.icon.remove_css_class("icon-red")
        self.icon.remove_css_class("icon-green")
        self.icon.add_css_class("icon-red" if running else "icon-green")

        if running:
            self.label.set_label("Stoppa")
            self.button.set_tooltip_text("Stoppar Battle.net")
            self.button.remove_css_class("suggested-action")
        elif installed:
            self.label.set_label("Starta")
            self.button.set_tooltip_text("Startar Battle.net")
            self.button.add_css_class("suggested-action")
        else:
            self.label.set_label("Installera")
            self.button.set_tooltip_text("Installerar Battle.net och startar klienten")
            self.button.add_css_class("suggested-action")

    def _on_clicked(self, button: Gtk.Button) -> None:
        if health.running():
            health.kill_all()
            _refresh_root(self)
            self._toast("Stoppade Battle.net")
            return

        button.set_sensitive(False)
        self._toast("Startar Battle.net ...")

        def work() -> None:
            config = Config.load()
            service.launch(config, service.ensure(config))

        def done(_result: object) -> None:
            button.set_sensitive(True)
            _refresh_root(self)
            self._toast("Startar Battle.net")

        def error(exc: Exception) -> None:
            button.set_sensitive(True)
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
    strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
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
        options: list[Gtk.Widget] | None = None,
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        if icon is not None:
            row.add_prefix(_icon(icon, tone))
        for widget in options or []:
            row.add_suffix(widget)
        button = Gtk.Button(label=label)
        button.set_valign(Gtk.Align.CENTER)
        if suggested:
            button.add_css_class("suggested-action")
        button.connect("clicked", lambda *_: callback(button))  # type: ignore[operator]
        row.add_suffix(button)
        return row

    client_row = ClientRow(lambda b: _repair(window, b))
    maintenance.add(client_row)
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
            icon=MATERIAL["delete"],
            tone="fire",
            options=[drop_installer],
        )
    )
    page.add(destructive)

    # --- Advanced switch (stays put above the groups it reveals) ---------
    advanced: list[Adw.PreferencesGroup] = []
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
    advanced.append(performance)

    # --- Runner ----------------------------------------------------------
    runners = Adw.PreferencesGroup(title="Runner")
    runners.set_description("Vilken Proton som används. Sparas i config.toml.")
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
    page.add(runners)
    advanced.append(runners)

    # --- Paths (advanced) ------------------------------------------------
    paths = Adw.PreferencesGroup(title="Sökvägar")
    paths.set_description("Var saker ligger. Installeraren cachas och återanvänds.")
    paths.add(_kv("Installerare", f"{config.installer}, {_installer_state(config.installer)}"))
    paths.add(_kv("Config", str(config.config_file)))

    log_row = Adw.ActionRow(title="Loggar", subtitle=str(config.log_dir))
    log_button = Gtk.Button(label="Visa")
    log_button.set_valign(Gtk.Align.CENTER)
    log_button.set_tooltip_text("Körnings- och installationsloggar")
    log_button.connect("clicked", lambda *_: _show_logs(window))
    log_row.add_suffix(log_button)
    paths.add(log_row)
    page.add(paths)
    advanced.append(paths)

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
    advanced.append(about)

    # --- Advanced: hidden by default to keep the app simple --------------
    for group in advanced:
        group.set_visible(False)

    # --- Column: banner on top, everything else below --------------------
    column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    banner = data_file("header", "frostfire_installer_header.png")
    if banner is not None:
        picture = Gtk.Picture.new_for_filename(str(banner))
        picture.set_content_fit(Gtk.ContentFit.FILL)
        frame = Gtk.AspectFrame(ratio=1600 / 521, obey_child=False)
        frame.set_child(picture)
        frame.set_hexpand(True)
        column.append(frame)
    column.append(_system_strip())
    config_strip = ConfigStrip(config)
    column.append(config_strip)
    run_bar = RunBar()
    column.append(run_bar)
    page.set_vexpand(True)
    column.append(page)

    if hasattr(window, "register_state"):
        window.register_state(client_row.refresh)  # type: ignore[attr-defined]
        window.register_state(config_strip.refresh)  # type: ignore[attr-defined]
        window.register_state(run_bar.refresh)  # type: ignore[attr-defined]
    return _toolbar_page("Frostfire Installer", column)


# --- Handlers ------------------------------------------------------------
def _repair(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)
    window.toast("Reparerar ...")  # type: ignore[attr-defined]

    def work() -> None:
        config = Config.load()
        health.remediate(config)
        service.launch(config, service.ensure(config))

    def done(_result: object) -> None:
        button.set_sensitive(True)
        _refresh_root(window)
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
        _refresh_root(window)
        window.toast("Återinstallerat" + (" (spel behållna)" if keep_games else ""))  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
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
    window.toast("Tar bort Battle.net ...")  # type: ignore[attr-defined]

    def work() -> None:
        battlenet.remove(Config.load(), keep_games=keep_games, remove_installer=remove_installer)

    def done(_result: object) -> None:
        button.set_sensitive(True)
        _refresh_root(window)
        window.toast("Battle.net borttaget" + (" (spel behållna)" if keep_games else ""))  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    _refresh_root(window)
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
