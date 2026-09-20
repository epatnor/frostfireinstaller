"""Content pages for the main window."""

from __future__ import annotations

import shutil

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, distro, profiles, proton  # noqa: E402
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


# --- Library -------------------------------------------------------------
def _game_card(profile: profiles.GameProfile) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.add_css_class("card")
    box.set_size_request(180, 210)
    for margin in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{margin}")(6)

    cover = data_file("covers", f"{profile.id}.png")
    if cover is not None:
        picture = Gtk.Picture.new_for_filename(str(cover))
        picture.set_content_fit(Gtk.ContentFit.COVER)
        picture.set_size_request(168, 104)
        frame = Gtk.Box()
        frame.add_css_class("cover-frame")
        frame.set_overflow(Gtk.Overflow.HIDDEN)
        frame.append(picture)
        box.append(frame)
    else:
        icon = Gtk.Image.new_from_icon_name("applications-games-symbolic")
        icon.set_pixel_size(56)
        icon.set_margin_top(12)
        box.append(icon)

    name = Gtk.Label(label=profile.name)
    name.set_wrap(True)
    name.set_justify(Gtk.Justification.CENTER)
    name.add_css_class("heading")
    box.append(name)

    subtitle = Gtk.Label(label=profile.anti_cheat or "Battle.net")
    subtitle.add_css_class("dim-label")
    subtitle.set_wrap(True)
    box.append(subtitle)
    return box


def build_home(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for margin in ("top", "bottom", "start", "end"):
        getattr(content, f"set_margin_{margin}")(18)

    group = Adw.PreferencesGroup()
    group.set_title("frostylauncher")
    group.set_description(
        "Stabil och kompatibel Battle.net-installation via umu + Proton. "
        "Spelen startar du i Blizzards launcher."
    )
    row = Adw.ActionRow(title="Battle.net", subtitle="Blizzard-launchern")
    launch = Gtk.Button(label="Starta")
    launch.add_css_class("suggested-action")
    launch.set_valign(Gtk.Align.CENTER)
    launch.connect("clicked", lambda *_: _on_launch(window, launch))
    row.add_suffix(launch)
    group.add(row)
    content.append(group)

    heading = Gtk.Label(label="Kompatibilitet", xalign=0)
    heading.add_css_class("heading")
    content.append(heading)

    flow = Gtk.FlowBox()
    flow.set_selection_mode(Gtk.SelectionMode.NONE)
    flow.set_max_children_per_line(6)
    flow.set_min_children_per_line(2)
    flow.set_row_spacing(12)
    flow.set_column_spacing(12)
    flow.set_homogeneous(True)
    for profile in profiles.load_all().values():
        flow.append(_game_card(profile))
    content.append(_scrolled(flow))
    return _toolbar_page("Hem", content)


def _on_launch(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)
    window.toast("Förbereder och startar Battle.net ...")  # type: ignore[attr-defined]

    def work() -> None:
        config = Config.load()
        build = service.ensure(config)
        service.launch(config, build)

    def done(_result: object) -> None:
        button.set_sensitive(True)
        window.toast("Klart")  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


# --- Install -------------------------------------------------------------
def build_install(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    page = Adw.PreferencesPage()

    status = Adw.PreferencesGroup(title="Status")
    status.add(
        _kv("Battle.net", "Installerat" if battlenet.installed(config) else "Ej installerat")
    )
    status.add(_kv("Prefix", str(config.prefix)))
    status.add(_kv("Proton", str(proton.find(config.proton_name) or "saknas")))
    status.add(_kv("umu-run", shutil.which("umu-run") or "saknas"))
    page.add(status)

    actions = Adw.PreferencesGroup(title="Åtgärder")
    row = Adw.ActionRow(
        title="Installera / verifiera", subtitle="Idempotent – gör bara det som saknas"
    )
    button = Gtk.Button(label="Kör")
    button.add_css_class("suggested-action")
    button.set_valign(Gtk.Align.CENTER)
    button.connect("clicked", lambda *_: _on_ensure(window, button))
    row.add_suffix(button)
    actions.add(row)
    page.add(actions)

    return _toolbar_page("Installera", page)


def _kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


def _on_ensure(window: Adw.ApplicationWindow, button: Gtk.Button) -> None:
    button.set_sensitive(False)
    window.toast("Verifierar/installerar ...")  # type: ignore[attr-defined]

    def work() -> str:
        config = Config.load()
        build = service.ensure(config)
        return str(build)

    def done(build: str) -> None:
        button.set_sensitive(True)
        window.toast(f"Klart – Proton: {build}")  # type: ignore[attr-defined]

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        window.toast(f"Fel: {exc}")  # type: ignore[attr-defined]

    run_async(work, done, error)


# --- Runners -------------------------------------------------------------
def build_runners(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    page = Adw.PreferencesPage()

    group = Adw.PreferencesGroup(title="Proton-byggen")
    group.set_description("Välj vilken runner som används. Sparas i config.toml.")

    current = proton.find(config.proton_name)
    builds = proton.all_builds()
    if not builds:
        group.add(
            Adw.ActionRow(title="Inga Proton-byggen hittades", subtitle="Installera via ProtonPlus")
        )
    for build in builds:
        row = Adw.ActionRow(title=build.name, subtitle=str(build))
        if build == current:
            row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        button = Gtk.Button(label="Använd")
        button.set_valign(Gtk.Align.CENTER)
        button.connect("clicked", lambda _b, name=build.name: _on_pick_runner(window, name))
        row.add_suffix(button)
        group.add(row)
    page.add(group)
    return _toolbar_page("Runners", page)


def _on_pick_runner(window: Adw.ApplicationWindow, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    window.toast(f"Runner satt till {name}")  # type: ignore[attr-defined]


# --- Performance ---------------------------------------------------------
def build_performance(window: Adw.ApplicationWindow) -> Adw.ToolbarView:
    config = Config.load()
    page = Adw.PreferencesPage()

    group = Adw.PreferencesGroup(title="Prestanda")
    group.set_description("Tillämpas när Battle.net startas via frostylauncher.")

    def switch(title: str, subtitle: str, value: bool, key: str) -> Adw.SwitchRow:
        row = Adw.SwitchRow(title=title, subtitle=subtitle)
        row.set_active(value)

        def on_active(row: Adw.SwitchRow, _pspec: object) -> None:
            cfg = Config.load()
            setattr(cfg.performance, key, row.get_active())
            cfg.save()

        row.connect("notify::active", on_active)
        return row

    group.add(
        switch(
            "MangoHud",
            "FPS/GPU-overlay (kräver MangoHud)",
            config.performance.mangohud,
            "mangohud",
        )
    )
    group.add(
        switch(
            "GameMode",
            "Optimera systemet under spel (Feral GameMode)",
            config.performance.gamemode,
            "gamemode",
        )
    )
    group.add(
        switch(
            "Gamescope",
            "Kör i en nästlad compositor (kan hjälpa på Wayland)",
            config.performance.gamescope,
            "gamescope",
        )
    )
    page.add(group)

    stack = Adw.PreferencesGroup(title="Grafikstack")
    stack.add(_kv("DXVK", "Levereras av Proton (DX9/10/11 → Vulkan)"))
    stack.add(_kv("VKD3D-Proton", "Levereras av Proton (DX12 → Vulkan)"))
    stack.add(_kv("NTSync", "Används automatiskt om kärnan stödjer det"))
    page.add(stack)

    return _toolbar_page("Prestanda", page)


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

    paths = Adw.PreferencesGroup(title="Sökvägar")
    paths.add(_kv("Prefix", str(config.prefix)))
    paths.add(_kv("Installerare", str(config.installer)))
    paths.add(_kv("Config", str(config.config_dir / "config.toml")))
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


def _show_about(window: Adw.ApplicationWindow) -> None:
    from .. import __version__

    dialog = Adw.AboutDialog(
        application_name="frostylauncher",
        application_icon="applications-games-symbolic",
        version=__version__,
        developer_name="frostylauncher contributors",
        comments="Install and launch Blizzard games on Linux via umu + Proton.",
        license_type=Gtk.License.MIT_X11,
    )
    dialog.present(window)
