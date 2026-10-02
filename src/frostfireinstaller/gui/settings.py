"""Settings window.

The advanced options live in their own resizable window. Every row keeps only
the controls; the per-option explanations are tucked behind the "(i)" buttons,
while each card carries a one-line description. The cards stay compact and line
up as a grid (equal heights, two columns that collapse to one on a narrow
window).
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ..config import Config  # noqa: E402
from ..core import distro, gpu, proton, recommend, sysinfo  # noqa: E402
from . import actions, dialogs  # noqa: E402
from .helpers import run_async  # noqa: E402
from .state import ClientState  # noqa: E402
from .widgets import (  # noqa: E402
    MATERIAL,
    ActivityBar,
    Section,
    button,
    help_button,
    icon,
    installer_state,
    kv,
    open_folder,
    toolbar_page,
)

if TYPE_CHECKING:
    from .window import MainWindow

Refresher = Callable[[ClientState], None]

_MANGO_HELP = (
    "Shows FPS, frame time, GPU/CPU load and temperature on top of the game. "
    "Does not affect performance, only diagnostics. Follows into the games "
    "because they run in the same Wine session."
)
_GAMEMODE_HELP = (
    "Temporarily tunes the system while Battle.net and the games run: CPU "
    "governor to performance and less background churn. Can give a few percent "
    "smoother FPS. Requires the gamemode package."
)
_GAMESCOPE_HELP = (
    "Runs Battle.net and the games in a nested compositor. Can scale resolution, "
    "apply FSR upscaling and cap FPS, and fix Wayland window issues. Leave it off "
    "if everything works."
)
_GAMESCOPE_RISKY_HELP = (
    "WARNING - this machine is NVIDIA on Wayland. Nesting gamescope inside a "
    "Wayland session on the proprietary NVIDIA driver is a known-bad combination: "
    "presentation between gamescope and the outer compositor can collapse and make "
    "the whole screen strobe. If you are sensitive to flashing light, do not "
    "enable this. Should it happen, close the game with Alt+F4 and run "
    "'pkill -f gamescope'."
)
_FORCE_FULLSCREEN_HELP = (
    "Passes --force-windows-fullscreen to gamescope so the game window is always "
    "the nested display size. Helps it survive screen blanking or the compositor "
    "resizing the gamescope window after a monitor sleep. Makes the NVIDIA on "
    "Wayland flicker worse."
)
_INHIBIT_HELP = (
    "Holds an idle/suspend lock until the Wine session ends, not just while the "
    "launcher runs - Battle.net is usually closed once the game is up. A monitor "
    "sleeping mid-game is a common cause of the game window coming back at the "
    "wrong size or on the wrong screen."
)


def _monitor_for(widget: Gtk.Widget) -> Gdk.Monitor | None:
    """The monitor the widget is on, else the first one.

    ``Gdk.Display.get_primary_monitor`` does not exist on the Wayland display,
    so ask the surface first and fall back to the monitor list.
    """
    display = widget.get_display()
    if display is None:
        return None
    surface = widget.get_surface()
    if surface is not None:
        monitor = display.get_monitor_at_surface(surface)
        if monitor is not None:
            return monitor
    monitors = display.get_monitors()
    if monitors is not None and monitors.get_n_items() > 0:
        return monitors.get_item(0)
    return None


def _monitor_height(monitor: Gdk.Monitor) -> int | None:
    """Usable height of a monitor.

    The Wayland backend exposes ``get_geometry`` but not ``get_workarea``, so
    prefer the work area when present and fall back to the full geometry.
    """
    for name in ("get_workarea", "get_geometry"):
        getter = getattr(monitor, name, None)
        if getter is None:
            continue
        rect = getter()
        if rect is not None:
            return rect.height
    return None


def gamescope_is_risky() -> bool:
    """True when nesting gamescope here is known to risk a strobing screen.

    NVIDIA's proprietary driver on a Wayland session is the combination that
    bites: presentation between gamescope and the outer compositor can collapse
    and flash the whole display. That is a photosensitivity hazard, not a
    cosmetic glitch, so it is called out on the switch itself rather than left
    for the user to discover.
    """
    version, _is_open = gpu.nvidia_driver_info()
    return version is not None and distro.session() == "Wayland"


class SettingsWindow(Adw.Window):
    """A standalone, resizable window holding every advanced option.

    Its state widgets register with the main window, so one refresh updates both
    windows. Every control also re-syncs from ``config.toml`` on refresh, so a
    value changed on disk never leaves a switch drawing the old position (and a
    click on it re-saving the stale value).
    """

    def __init__(self, parent: MainWindow) -> None:
        super().__init__()
        self._parent = parent
        self._refreshers: list[Refresher] = []
        self._grid: Gtk.Widget | None = None
        self.set_title("Settings")
        self.set_default_size(920, 660)
        self.set_resizable(True)
        self.set_transient_for(parent)

        self._activity = ActivityBar()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self._activity)
        content.append(self._build_content(Config.load()))

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(toolbar_page("Settings", content)[0])
        self.set_content(self.toasts)
        self._fit_height()
        self.connect("close-request", self._on_close)
        self.connect("notify::is-active", self._on_focus)
        parent.refresh_state()

    def _fit_height(self) -> None:
        """Open tall enough to show every card, if the screen has room."""
        if self._grid is None:
            return
        width = 920
        natural = self._grid.measure(Gtk.Orientation.VERTICAL, width - 60)[1]
        target = natural + 96  # header bar + section margins
        monitor = _monitor_for(self._parent)
        if monitor is not None:
            height = _monitor_height(monitor)
            if height is not None:
                target = min(target, height - 40)
        self.set_default_size(width, target)

    def _register(self, refresher: Refresher) -> None:
        self._refreshers.append(refresher)
        self._parent.register_state(refresher)

    def _on_focus(self, *_args: object) -> None:
        if self.is_active():
            self.refresh_state()

    def _on_close(self, *_args: object) -> bool:
        for refresher in self._refreshers:
            self._parent.unregister_state(refresher)
        self._parent.settings_closed()
        return False

    # --- Surface ----------------------------------------------------------
    def refresh_state(self) -> None:
        self._parent.refresh_state()

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))

    def set_activity(self, message: str) -> None:
        self._activity.show(message)
        self._parent.set_activity(message)

    def clear_activity(self) -> None:
        self._activity.hide()
        self._parent.clear_activity()

    # --- rows -------------------------------------------------------------
    def _switch(
        self,
        config: Config,
        title: str,
        key: str,
        tool: str,
        help_text: str,
        extra: Gtk.Widget | None = None,
        on_toggle: Callable[[bool], None] | None = None,
    ) -> Adw.SwitchRow:
        """A performance toggle saved to ``[performance] <key>``."""
        missing = shutil.which(tool) is None
        if missing:
            help_text = f"WARNING: {tool} is not installed.\n\n{help_text}"

        row = Adw.SwitchRow(title=title)
        row.set_active(bool(getattr(config.performance, key)))
        if missing:
            row.add_css_class("row-inactive")
        if extra is not None:
            row.add_suffix(extra)
        help_widget = help_button(help_text)
        if missing:
            help_widget.add_css_class("help-warn")
        row.add_suffix(help_widget)

        def on_active(row: Adw.SwitchRow, _pspec: object) -> None:
            if missing and row.get_active():
                row.set_active(False)
                self.toast(f"{tool} is not installed")
                return
            cfg = Config.load()
            setattr(cfg.performance, key, row.get_active())
            cfg.save()
            if on_toggle is not None:
                on_toggle(row.get_active())

        handler = row.connect("notify::active", on_active)

        def sync(state: ClientState) -> None:
            value = bool(getattr(state.config.performance, key))
            if row.get_active() != value:
                _set_quietly(row, handler, value)
                if on_toggle is not None:
                    on_toggle(value)

        self._register(sync)
        return row

    # --- content ----------------------------------------------------------
    def _build_content(self, config: Config) -> Gtk.Widget:
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for column in (left, right):
            column.set_hexpand(True)
            column.set_homogeneous(True)
            column.add_css_class("settings-column")
        # All action buttons share the width of the widest one ("Open folder").
        buttons = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        def action_row(
            title: str,
            label: str,
            callback: Callable[[Gtk.Button], None],
            help_text: str | None = None,
            danger: bool = False,
            glyph: str | None = None,
            tone: str | None = None,
        ) -> Adw.ActionRow:
            row = Adw.ActionRow(title=title)
            if glyph is not None:
                row.add_prefix(icon(glyph, tone))
            widget = button(label, danger=danger)
            buttons.add_widget(widget)
            widget.connect("clicked", lambda *_: callback(widget))
            row.add_suffix(widget)
            if help_text is not None:
                row.add_suffix(help_button(help_text))
            return row

        left.append(self._battlenet_card(action_row))
        left.append(self._performance_card(config))
        left.append(self._runner_card(config))
        right.append(self._graphics_card(config))
        right.append(self._paths_card(config, buttons))
        right.append(self._more_card(action_row))

        # Two equal-height columns make a grid; both columns are homogeneous, so
        # every card gets the same height. libadwaita flips it to a single column
        # below the breakpoint.
        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        columns.set_homogeneous(True)
        columns.add_css_class("bn-sections")
        columns.append(left)
        columns.append(right)
        self._grid = columns

        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 700px"))
        breakpoint.add_setter(columns, "orientation", Gtk.Orientation.VERTICAL)
        breakpoint.add_setter(columns, "homogeneous", False)
        breakpoint.add_setter(left, "homogeneous", False)
        breakpoint.add_setter(right, "homogeneous", False)
        self.add_breakpoint(breakpoint)

        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_width(False)
        scroller.set_child(columns)
        return scroller

    def _battlenet_card(self, action_row: Callable[..., Adw.ActionRow]) -> Section:
        card = Section("Battle.net", "Install, repair, reset or remove the client.")
        keep_games = Gtk.CheckButton(label="Games")
        keep_installer = Gtk.CheckButton(label="Installer")
        for check in (keep_games, keep_installer):
            check.set_valign(Gtk.Align.CENTER)
            check.set_active(True)

        client_row = action_row(
            "Client",
            "Repair",
            lambda b: actions.repair(self, b),
            help_text="The Battle.net client. Repair stops it, clears the CEF cache and "
            "starts it again.",
            glyph=MATERIAL["build"],
            tone="ice",
        )
        reinstall_row = action_row(
            "Reinstall",
            "Reinstall",
            lambda b: actions.reinstall(
                self, b, keep_games.get_active(), keep_installer.get_active()
            ),
            help_text="Removes the client and installs it again.",
            glyph=MATERIAL["refresh"],
            tone="fire",
        )
        remove_row = action_row(
            "Remove",
            "Remove",
            lambda b: actions.remove(self, b, keep_games.get_active(), keep_installer.get_active()),
            help_text="Removes the client.",
            danger=True,
            glyph=MATERIAL["delete"],
            tone="fire",
        )
        keep_row = Adw.ActionRow(title="Keep")
        keep_row.add_suffix(keep_games)
        keep_row.add_suffix(keep_installer)
        keep_row.add_suffix(
            help_button(
                "Keep installed games and/or the cached installer when reinstalling or removing."
            )
        )
        for row in (client_row, reinstall_row, remove_row, keep_row):
            card.add(row)

        def refresh(state: ClientState) -> None:
            client_row.set_subtitle(
                "The client is installed" if state.installed else "The client is not installed"
            )
            # Nothing to reset or remove without a client (the run bar offers Install).
            for row in (reinstall_row, remove_row, keep_row):
                row.set_visible(state.installed)

        self._register(refresh)
        return card

    def _performance_card(self, config: Config) -> Section:
        card = Section("Performance", "Toggles that follow into the games you start.")
        card.add(self._switch(config, "MangoHud", "mangohud", "mangohud", _MANGO_HELP))
        card.add(self._switch(config, "GameMode", "gamemode", "gamemode", _GAMEMODE_HELP))

        force = Gtk.CheckButton(label="Force fullscreen")
        force.set_valign(Gtk.Align.CENTER)
        force.set_active(bool(config.performance.gamescope_force_fullscreen))
        force.set_sensitive(bool(config.performance.gamescope))
        force.set_tooltip_text(_FORCE_FULLSCREEN_HELP)

        def save_force(check: Gtk.CheckButton) -> None:
            cfg = Config.load()
            cfg.performance.gamescope_force_fullscreen = check.get_active()
            cfg.save()

        force_handler = force.connect("toggled", save_force)
        self._register(
            lambda state: _set_quietly(
                force, force_handler, bool(state.config.performance.gamescope_force_fullscreen)
            )
        )
        gamescope_help = _GAMESCOPE_RISKY_HELP if gamescope_is_risky() else _GAMESCOPE_HELP
        card.add(
            self._switch(
                config,
                "Gamescope",
                "gamescope",
                "gamescope",
                gamescope_help,
                extra=force,
                on_toggle=force.set_sensitive,
            )
        )
        card.add(
            self._switch(config, "Keep awake", "inhibit_idle", "systemd-inhibit", _INHIBIT_HELP)
        )
        return card

    def _runner_card(self, config: Config) -> Section:
        card = Section("Runner", "Which Proton build the games use.")
        builds = proton.all_builds()
        if builds:
            candidates = list(builds)
        elif shutil.which("umu-run"):
            candidates = [Path(name) for name in proton.CODENAMES]
        else:
            candidates = []

        if candidates:
            row = Adw.ActionRow(title="Proton runner")
            dropdown = Gtk.DropDown(model=Gtk.StringList.new([c.name for c in candidates]))
            dropdown.set_valign(Gtk.Align.CENTER)
            dropdown.add_css_class("runner-dropdown")
            dropdown.set_tooltip_text("Choose the Proton build")

            def on_runner(widget: Gtk.DropDown, _pspec: object) -> None:
                index = widget.get_selected()
                if 0 <= index < len(candidates):
                    actions.pick_runner(self, candidates[index].name)

            def selected(state: ClientState) -> int:
                current = proton.find(state.config.proton_name)
                return next((i for i, c in enumerate(candidates) if c == current), 0)

            dropdown.set_selected(selected(ClientState(config, False, False)))
            handler = dropdown.connect("notify::selected", on_runner)

            def sync(state: ClientState) -> None:
                index = selected(state)
                if dropdown.get_selected() != index:
                    dropdown.handler_block(handler)
                    dropdown.set_selected(index)
                    dropdown.handler_unblock(handler)

            self._register(sync)
            row.add_suffix(dropdown)
            row.add_suffix(
                help_button(
                    "Codenames (UMU-Proton, GE-Proton) are downloaded by umu-launcher "
                    "on first launch. Saved in config.toml."
                )
            )
            card.add(row)
        else:
            card.add(
                Adw.ActionRow(
                    title="No Proton builds found",
                    subtitle="Install umu-launcher (auto-download) or a build via ProtonPlus",
                )
            )

        # Host summary: lspci/lsblk/dmidecode can take a moment, so fill it in later.
        rows = {name: Adw.ActionRow(title=name, subtitle="...") for name in ("CPU", "Memory")}
        rows["Disks"] = Adw.ActionRow(title="Disks", subtitle="...")
        for row in rows.values():
            card.add(row)

        def read() -> dict[str, str]:
            return {
                "CPU": sysinfo.cpu(),
                "Memory": sysinfo.memory(),
                "Disks": " · ".join(sysinfo.disks()) or "unknown",
            }

        def fill(values: dict[str, str]) -> None:
            for name, value in values.items():
                rows[name].set_subtitle(value)

        run_async(read, fill)
        return card

    def _graphics_card(self, config: Config) -> Section:
        card = Section(
            "Graphics",
            "Which GPU the games use. Only the GPUs found on this machine are listed.",
        )
        options: list[tuple[str, str, str]] = [
            ("auto", "Auto", "Let the game choose, without forcing a GPU.")
        ]
        if gpu.nvidia_driver_info()[0] is not None:
            options.append(
                (
                    "nvidia",
                    "Dedicated",
                    'Forces DXVK_FILTER_DEVICE_NAME = "NVIDIA" (the dedicated GPU).',
                )
            )
        integrated = gpu.integrated_gpu_name()
        if integrated:
            options.append(
                (
                    "integrated",
                    "Integrated",
                    f"Same GPU as the screen ({integrated}, detected automatically). "
                    "Troubleshooting mode if the NVIDIA path causes GPU hangs.",
                )
            )

        def preference(state_config: Config) -> str:
            value = gpu.gpu_preference(state_config)
            return value if any(value == option for option, _, _ in options) else "auto"

        current = preference(config)
        radios: list[tuple[str, Gtk.CheckButton, int]] = []
        group: Gtk.CheckButton | None = None
        for value, title, help_text in options:
            row = Adw.ActionRow(title=title)
            radio = Gtk.CheckButton()
            radio.set_valign(Gtk.Align.CENTER)
            radio.set_tooltip_text(f"Use {title}")
            if group is None:
                group = radio
            else:
                radio.set_group(group)
            radio.set_active(value == current)
            handler = radio.connect(
                "toggled",
                lambda widget, val=value: (
                    actions.pick_gpu(self, val) if widget.get_active() else None
                ),
            )
            radios.append((value, radio, handler))
            row.add_prefix(radio)
            row.add_suffix(help_button(help_text))
            card.add(row)

        def sync(state: ClientState) -> None:
            wanted = preference(state.config)
            for _value, radio, handler in radios:
                radio.handler_block(handler)
            for value, radio, _handler in radios:
                radio.set_active(value == wanted)
            for _value, radio, handler in radios:
                radio.handler_unblock(handler)

        self._register(sync)

        gpus_row = Adw.ActionRow(title="GPU", subtitle="...")
        card.add(gpus_row)
        run_async(
            lambda: " · ".join(sysinfo.gpus()) or "unknown",
            gpus_row.set_subtitle,
        )
        return card

    def _paths_card(self, config: Config, buttons: Gtk.SizeGroup) -> Section:
        card = Section("Paths", "Where the installer, config and logs live.")
        installer_row = Adw.ActionRow(title="Installer")
        open_button = button("Open folder", tooltip="Open the folder where the installer is cached")
        buttons.add_widget(open_button)
        open_button.connect("clicked", lambda *_: open_folder(Config.load().bnet_dir))
        installer_row.add_suffix(open_button)
        card.add(installer_row)
        self._register(
            lambda state: installer_row.set_subtitle(
                f"{state.config.installer.name}, {installer_state(state.config.installer)}"
            )
        )
        card.add(kv("Config", str(config.config_file)))

        log_row = Adw.ActionRow(title="Logs", subtitle=str(config.log_dir))
        log_button = button("View", tooltip="Run and installation logs")
        buttons.add_widget(log_button)
        log_button.connect("clicked", lambda *_: dialogs.show_logs(self))
        log_row.add_suffix(log_button)
        card.add(log_row)
        return card

    def _more_card(self, action_row: Callable[..., Adw.ActionRow]) -> Section:
        card = Section("Diagnostics & about", "Check the system or read about the app.")

        def run_check(widget: Gtk.Button) -> None:
            widget.set_sensitive(False)

            def done(items: list[recommend.Recommendation]) -> None:
                widget.set_sensitive(True)
                dialogs.show_recommendations(self, items)

            def error(exc: Exception) -> None:
                widget.set_sensitive(True)
                self.toast(f"Error: {exc}")

            run_async(lambda: recommend.report(Config.load()), done, error)

        card.add(action_row("System check", "Run", run_check))
        card.add(
            action_row(
                "Frostfire Installer",
                "About",
                lambda _b: dialogs.show_about(self),
                glyph=MATERIAL["info"],
            )
        )
        return card


def _set_quietly(widget: Gtk.Widget, handler: int, value: bool) -> None:
    """Set a toggle without firing its save handler."""
    if widget.get_active() == value:
        return
    widget.handler_block(handler)
    widget.set_active(value)
    widget.handler_unblock(handler)
