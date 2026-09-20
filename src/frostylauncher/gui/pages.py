"""Content pages for the main window.

Scope: a Battle.net installer helper. Install / verify / repair the launcher.
Games are started from Blizzard's own launcher, not here.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, distro, health, proton  # noqa: E402
from .helpers import data_file, run_async  # noqa: E402


def _toolbar_page(title: str, content: Gtk.Widget) -> Adw.ToolbarView:
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    view.add_top_bar(header)
    view.set_content(content)
    return view


def _scrolled(child: Gtk.Widget) -> Gtk.ScrolledWindow:
    scroller = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
    scroller.set_child(child)
    return scroller


def _kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


# --- Home ----------------------------------------------------------------
def build_home(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    page = Adw.PreferencesPage()

    status = Adw.PreferencesGroup(title="Status")
    status.add(
        _kv("Battle.net", "Installerat" if battlenet.installed(config) else "Ej installerat")
    )
    status.add(_kv("Prefix", str(config.prefix)))
    status.add(_kv("Proton", str(proton.find(config.proton_name) or "saknas")))
    status.add(_kv("Körs", "ja" if health.running() else "nej"))
    page.add(status)

    actions = Adw.PreferencesGroup(title="Åtgärder")

    def action(
        title: str,
        subtitle: str,
        label: str,
        callback: object,
        suggested: bool = False,
    ) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        button = Gtk.Button(label=label)
        button.set_valign(Gtk.Align.CENTER)
        if suggested:
            button.add_css_class("suggested-action")
        button.connect("clicked", lambda *_: callback(button))  # type: ignore[operator]
        row.add_suffix(button)
        return row

    actions.add(
        action(
            "Installera / verifiera",
            "Idempotent – gör bara det som saknas",
            "Kör",
            lambda b: _ensure(window, b),
            suggested=True,
        )
    )
    actions.add(
        action(
            "Starta Battle.net",
            "Startar Blizzard-launchern",
            "Starta",
            lambda b: _launch(window, b),
        )
    )
    actions.add(
        action(
            "Reparera",
            "Stoppa, rensa CEF/cache och starta om",
            "Reparera",
            lambda b: _repair(window, b),
        )
    )

    keep_games = Adw.SwitchRow(
        title="Behåll spel",
        subtitle="Behåll installerade spel vid återinstallation eller borttagning",
    )
    keep_games.set_active(True)
    actions.add(keep_games)
    actions.add(
        action(
            "Återinstallera Battle.net",
            "Tar bort klienten och installerar om",
            "Kör",
            lambda b: _reinstall(window, b, keep_games),
        )
    )
    actions.add(
        action(
            "Ta bort Battle.net",
            "Tar bort klienten (spelen behålls om växeln är på)",
            "Ta bort",
            lambda b: _remove(window, b, keep_games),
        )
    )
    actions.add(
        action("Stoppa", "Dödar alla Battle.net-processer", "Stoppa", lambda b: _kill(window, b))
    )
    page.add(actions)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    banner = data_file("header", "frostfire_installer_header_1.png")
    if banner is not None:
        picture = Gtk.Picture.new_for_filename(str(banner))
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        picture.set_size_request(-1, 170)
        picture.set_margin_top(12)
        picture.set_margin_bottom(6)
        picture.set_margin_start(18)
        picture.set_margin_end(18)
        content.append(picture)
    page.set_vexpand(True)
    content.append(page)
    return _toolbar_page("Hem", content)


def _ensure(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)
    window.toast("Verifierar/installerar ...")  # type: ignore[attr-defined]

    def work() -> str:
        return str(service.ensure(Config.load()))

    def done(build: str) -> None:
        button.set_sensitive(True)
        window.toast(f"Klart – Proton: {build}")  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


def _launch(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)

    def work() -> None:
        config = Config.load()
        service.launch(config, service.ensure(config))

    def done(_result: object) -> None:
        button.set_sensitive(True)
        window.toast("Startar Battle.net")  # type: ignore[attr-defined]

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


def _kill(window: Adw.ApplicationWindow, _button: Gtk.Button) -> None:
    health.kill_all()
    window.toast("Stoppade Battle.net")  # type: ignore[attr-defined]


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


# --- Logs ----------------------------------------------------------------
def build_logs(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    for margin in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{margin}")(12)

    logs = (
        sorted(config.log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if config.log_dir.is_dir()
        else []
    )
    names = [path.name for path in logs]
    dropdown = Gtk.DropDown.new_from_strings(names or ["(inga loggar)"])
    box.append(dropdown)

    view = Gtk.TextView()
    view.set_monospace(True)
    view.set_editable(False)
    buffer = view.get_buffer()
    box.append(_scrolled(view))

    def show() -> None:
        index = dropdown.get_selected()
        if logs and 0 <= index < len(logs):
            text = logs[index].read_text(encoding="utf-8", errors="ignore")
            buffer.set_text(text[-20000:])

    dropdown.connect("notify::selected", lambda *_: show())
    show()
    return _toolbar_page("Loggar", box)


# --- Settings ------------------------------------------------------------
def build_settings(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    host = distro.detect()
    page = Adw.PreferencesPage()

    runners = Adw.PreferencesGroup(title="Runner")
    runners.set_description("Vilken Proton som används. Sparas i config.toml.")
    current = proton.find(config.proton_name)
    builds = proton.all_builds()
    if not builds:
        runners.add(
            Adw.ActionRow(title="Inga Proton-byggen hittades", subtitle="Installera via ProtonPlus")
        )
    for build in builds:
        row = Adw.ActionRow(title=build.name, subtitle=str(build))
        if build == current:
            row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        button = Gtk.Button(label="Använd")
        button.set_valign(Gtk.Align.CENTER)
        button.connect("clicked", lambda _b, name=build.name: _pick_runner(window, name))
        row.add_suffix(button)
        runners.add(row)
    page.add(runners)

    performance = Adw.PreferencesGroup(title="Prestanda")
    performance.set_description("Tillämpas när Battle.net startas via frostylauncher.")
    performance.add(_switch(config, "MangoHud", "FPS/GPU-overlay (kräver MangoHud)", "mangohud"))
    performance.add(_switch(config, "GameMode", "Optimera systemet under spel", "gamemode"))
    performance.add(
        _switch(config, "Gamescope", "Nästlad compositor (kan hjälpa på Wayland)", "gamescope")
    )
    page.add(performance)

    paths = Adw.PreferencesGroup(title="Sökvägar")
    paths.add(_kv("Prefix", str(config.prefix)))
    paths.add(_kv("Installerare", str(config.installer)))
    paths.add(_kv("Config", str(config.config_file)))
    paths.add(_kv("Loggar", str(config.log_dir)))
    page.add(paths)

    diagnostics = Adw.PreferencesGroup(title="Diagnostik")
    diagnostics.add(_kv("Distro", host.distro))
    diagnostics.add(_kv("Atomic", "ja" if host.atomic else "nej"))
    diagnostics.add(_kv("Session", host.session))
    diagnostics.add(_kv("Desktop", host.desktop))
    diagnostics.add(_kv("Kernel", host.kernel))
    diagnostics.add(_kv("GPU", host.gpu or "-"))
    page.add(diagnostics)

    about = Adw.PreferencesGroup(title="Om")
    row = Adw.ActionRow(title="frostylauncher")
    button = Gtk.Button(label="Om")
    button.set_valign(Gtk.Align.CENTER)
    button.connect("clicked", lambda *_: _show_about(window))
    row.add_suffix(button)
    about.add(row)
    page.add(about)

    return _toolbar_page("Inställningar", page)


def _switch(config: Config, title: str, subtitle: str, key: str) -> Adw.SwitchRow:
    row = Adw.SwitchRow(title=title, subtitle=subtitle)
    row.set_active(bool(getattr(config.performance, key)))

    def on_active(row: Adw.SwitchRow, _pspec: object) -> None:
        cfg = Config.load()
        setattr(cfg.performance, key, row.get_active())
        cfg.save()

    row.connect("notify::active", on_active)
    return row


def _pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    window.toast(f"Runner satt till {name}")  # type: ignore[attr-defined]


def _show_about(window: Adw.ApplicationWindow) -> None:
    from .. import __version__

    dialog = Adw.AboutDialog(
        application_name="frostylauncher",
        application_icon="applications-games-symbolic",
        version=__version__,
        developer_name="frostylauncher contributors",
        comments="A Battle.net installer helper for Linux (umu-launcher + Proton).",
        license_type=Gtk.License.MIT_X11,
    )
    dialog.present(window)
