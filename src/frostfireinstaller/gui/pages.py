"""Single-column content for the main window.

Layout: window header bar (top) -> Frostfire banner -> all features as rows.

Scope: a Battle.net installer helper. Games are started from Blizzard's own
launcher, not here.
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


def _kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


def _toolbar_page(title: str, content: Gtk.Widget) -> Adw.ToolbarView:
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title=title))
    view.add_top_bar(header)
    view.set_content(content)
    return view


def build_main(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    page = Adw.PreferencesPage()

    # --- Status (compact) ------------------------------------------------
    status = Adw.PreferencesGroup(title="Status")
    state = "Installerat" if battlenet.installed(config) else "Ej installerat"
    if health.running():
        state += " · körs"
    status.add(_kv("Battle.net", state))
    build = proton.find(config.proton_name)
    status.add(_kv("Proton", build.name if build else "saknas"))
    status.add(_kv("Prefix", str(config.prefix)))
    page.add(status)

    # --- Maintenance (ice: preserve and keep running) --------------------
    maintenance = Adw.PreferencesGroup(title="Installation &amp; underhåll")
    maintenance.set_description("Is – bevara och hålla igång.")

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

    maintenance.add(
        action(
            "Installera / verifiera",
            "Idempotent – gör bara det som saknas",
            "Kör",
            lambda b: _ensure(window, b),
            suggested=True,
        )
    )
    maintenance.add(
        action(
            "Starta Battle.net",
            "Startar Blizzard-launchern",
            "Starta",
            lambda b: _launch(window, b),
        )
    )
    maintenance.add(
        action(
            "Reparera",
            "Stoppa, rensa CEF/cache och starta om",
            "Reparera",
            lambda b: _repair(window, b),
        )
    )
    maintenance.add(
        action("Stoppa", "Dödar alla Battle.net-processer", "Stoppa", lambda b: _kill(window, b))
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
            "Kör",
            lambda b: _reinstall(window, b, keep_games),
        )
    )
    destructive.add(
        action(
            "Ta bort Battle.net",
            "Tar bort klienten (spelen behålls om växeln är på)",
            "Ta bort",
            lambda b: _remove(window, b, keep_games),
        )
    )
    page.add(destructive)

    # --- Performance -----------------------------------------------------
    performance = Adw.PreferencesGroup(title="Prestanda")
    performance.set_description("Tillämpas när Battle.net startas via frostfireinstaller.")
    performance.add(_switch(config, "MangoHud", "FPS/GPU-overlay (kräver MangoHud)", "mangohud"))
    performance.add(_switch(config, "GameMode", "Optimera systemet under spel", "gamemode"))
    performance.add(
        _switch(config, "Gamescope", "Nästlad compositor (kan hjälpa på Wayland)", "gamescope")
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
        )
    )
    page.add(logs)

    # --- Paths -----------------------------------------------------------
    paths = Adw.PreferencesGroup(title="Sökvägar")
    paths.add(_kv("Installerare", str(config.installer)))
    paths.add(_kv("Config", str(config.config_file)))
    paths.add(_kv("Loggar", str(config.log_dir)))
    page.add(paths)

    # --- Diagnostics -----------------------------------------------------
    host = distro.detect()
    diagnostics = Adw.PreferencesGroup(title="Diagnostik")
    diagnostics.add(_kv("Distro", host.distro))
    diagnostics.add(_kv("Session", f"{host.session} · {host.desktop}"))
    diagnostics.add(_kv("Kernel", host.kernel))
    diagnostics.add(_kv("GPU", host.gpu or "-"))
    page.add(diagnostics)

    # --- About -----------------------------------------------------------
    about = Adw.PreferencesGroup(title="Om")
    row = Adw.ActionRow(title="Frostfire Installer")
    button = Gtk.Button(label="Om")
    button.set_valign(Gtk.Align.CENTER)
    button.connect("clicked", lambda *_: _show_about(window))
    row.add_suffix(button)
    about.add(row)
    page.add(about)

    # --- Advanced: hidden by default to keep the app simple --------------
    advanced = [performance, runners, paths, diagnostics, about]
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
    page.set_vexpand(True)
    column.append(page)
    return _toolbar_page("Frostfire Installer", column)


# --- Handlers ------------------------------------------------------------
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


def _kill(window: Adw.ApplicationWindow, _button: Gtk.Button) -> None:
    health.kill_all()
    window.toast("Stoppade Battle.net")  # type: ignore[attr-defined]


def _pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    window.toast(f"Runner satt till {name}")  # type: ignore[attr-defined]


def _switch(config: Config, title: str, subtitle: str, key: str) -> Adw.SwitchRow:
    row = Adw.SwitchRow(title=title, subtitle=subtitle)
    row.set_active(bool(getattr(config.performance, key)))

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
