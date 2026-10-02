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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ..config import Config  # noqa: E402
from ..core import battlenet, gpu, proton, recommend, sysinfo  # noqa: E402
from . import pages  # noqa: E402

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


class SettingsWindow(Adw.Window):
    """A standalone, resizable window holding every advanced option."""

    def __init__(self, parent: Adw.ApplicationWindow) -> None:
        super().__init__()
        self._parent = parent
        self._state_refreshers: list[Callable[[], None]] = []
        self._grid: Gtk.Widget | None = None
        self.set_title("Settings")
        self.set_default_size(920, 660)
        self.set_resizable(True)
        self.set_transient_for(parent)

        self._activity = pages.ActivityBar()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self._activity)
        content.append(self._build_content())

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(pages._toolbar_page("Settings", content))
        self.set_content(self.toasts)
        self._fit_height()
        self.connect("close-request", self._on_close)

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

    # --- surface the main-window handlers expect --------------------------
    def register_state(self, refresher: Callable[[], None]) -> None:
        self._state_refreshers.append(refresher)

    def refresh_state(self) -> None:
        for refresher in self._state_refreshers:
            refresher()
        if hasattr(self._parent, "refresh_state"):
            self._parent.refresh_state()  # type: ignore[attr-defined]

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))

    def set_activity(self, message: str) -> None:
        self._activity.show(message)
        if hasattr(self._parent, "set_activity"):
            self._parent.set_activity(message)  # type: ignore[attr-defined]

    def clear_activity(self) -> None:
        self._activity.hide()
        if hasattr(self._parent, "clear_activity"):
            self._parent.clear_activity()  # type: ignore[attr-defined]

    def _on_close(self, *_args: object) -> bool:
        if getattr(self._parent, "_settings_window", None) is self:
            self._parent._settings_window = None  # type: ignore[attr-defined]
        return False

    # --- content ----------------------------------------------------------
    def _build_content(self) -> Gtk.Widget:
        window = self
        config = Config.load()
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for column in (left, right):
            column.set_hexpand(True)
            column.set_homogeneous(True)
            column.add_css_class("settings-column")
        # All action buttons share the width of the widest one ("Open folder").
        buttons = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        def action(
            title: str,
            label: str,
            callback: object,
            help_text: str | None = None,
            danger: bool = False,
            icon: str | None = None,
            tone: str | None = None,
        ) -> Adw.ActionRow:
            row = Adw.ActionRow(title=title)
            if icon is not None:
                row.add_prefix(pages._icon(icon, tone))
            button = pages._button(label, danger=danger)
            buttons.add_widget(button)
            button.connect("clicked", lambda *_: callback(button))  # type: ignore[operator]
            row.add_suffix(button)
            if help_text is not None:
                row.add_suffix(pages._help_button(help_text))
            return row

        # --- Battle.net ---------------------------------------------------
        battle = pages.Section("Battle.net", "Install, repair, reset or remove the client.")

        keep_games = Gtk.CheckButton(label="Games")
        keep_installer = Gtk.CheckButton(label="Installer")
        for check in (keep_games, keep_installer):
            check.set_valign(Gtk.Align.CENTER)
            check.set_active(True)

        client_row = pages.ClientRow(lambda b: pages._repair(window, b))
        buttons.add_widget(client_row.button)
        client_row.add_suffix(
            pages._help_button(
                "The Battle.net client. Repair stops it, clears the CEF cache and starts it again."
            )
        )
        battle.add(client_row)

        reinstall_row = action(
            "Reinstall",
            "Reinstall",
            lambda b: pages._reinstall(window, b, keep_games, keep_installer),
            help_text="Removes the client and installs it again.",
            icon=pages.MATERIAL["refresh"],
            tone="fire",
        )
        remove_row = action(
            "Remove",
            "Remove",
            lambda b: pages._remove(window, b, keep_games, keep_installer),
            help_text="Removes the client.",
            danger=True,
            icon=pages.MATERIAL["delete"],
            tone="fire",
        )
        battle.add(reinstall_row)
        battle.add(remove_row)

        keep_row = Adw.ActionRow(title="Keep")
        keep_row.add_suffix(keep_games)
        keep_row.add_suffix(keep_installer)
        keep_row.add_suffix(
            pages._help_button(
                "Keep installed games and/or the cached installer when reinstalling or removing."
            )
        )
        battle.add(keep_row)
        left.append(battle)

        # --- Performance --------------------------------------------------
        performance = pages.Section("Performance", "Toggles that follow into the games you start.")
        performance.add(pages._switch(config, "MangoHud", "mangohud", "mangohud", _MANGO_HELP))
        performance.add(pages._switch(config, "GameMode", "gamemode", "gamemode", _GAMEMODE_HELP))

        force_fullscreen = Gtk.CheckButton(label="Force fullscreen")
        force_fullscreen.set_valign(Gtk.Align.CENTER)
        force_fullscreen.set_active(bool(config.performance.gamescope_force_fullscreen))
        force_fullscreen.set_sensitive(bool(config.performance.gamescope))
        force_fullscreen.set_tooltip_text(_FORCE_FULLSCREEN_HELP)

        def save_force(button: Gtk.CheckButton) -> None:
            cfg = Config.load()
            cfg.performance.gamescope_force_fullscreen = button.get_active()
            cfg.save()

        force_fullscreen.connect("toggled", save_force)
        gamescope_help = _GAMESCOPE_RISKY_HELP if pages._gamescope_is_risky() else _GAMESCOPE_HELP
        performance.add(
            pages._switch(
                config,
                "Gamescope",
                "gamescope",
                "gamescope",
                gamescope_help,
                extra=force_fullscreen,
                on_toggle=force_fullscreen.set_sensitive,
            )
        )
        performance.add(
            pages._switch(config, "Keep awake", "inhibit_idle", "systemd-inhibit", _INHIBIT_HELP)
        )
        left.append(performance)

        # --- Runner -------------------------------------------------------
        runners = pages.Section("Runner", "Which Proton build the games use.")
        current = proton.find(config.proton_name)
        builds = proton.all_builds()
        if builds:
            candidates = list(builds)
        elif shutil.which("umu-run"):
            candidates = [Path(name) for name in proton.CODENAMES]
        else:
            candidates = []
        if candidates:
            runner_row = Adw.ActionRow(title="Proton runner")
            dropdown = Gtk.DropDown(model=Gtk.StringList.new([c.name for c in candidates]))
            dropdown.set_valign(Gtk.Align.CENTER)
            dropdown.add_css_class("runner-dropdown")
            dropdown.set_tooltip_text("Choose the Proton build")
            selected = next(
                (index for index, candidate in enumerate(candidates) if candidate == current), 0
            )
            dropdown.set_selected(selected)

            def on_runner(row: Gtk.DropDown, _pspec: object) -> None:
                index = row.get_selected()
                if 0 <= index < len(candidates):
                    pages._pick_runner(window, candidates[index].name)

            dropdown.connect("notify::selected", on_runner)
            runner_row.add_suffix(dropdown)
            runner_row.add_suffix(
                pages._help_button(
                    "Codenames (UMU-Proton, GE-Proton) are downloaded by umu-launcher "
                    "on first launch. Saved in config.toml."
                )
            )
            runners.add(runner_row)
        else:
            runners.add(
                Adw.ActionRow(
                    title="No Proton builds found",
                    subtitle="Install umu-launcher (auto-download) or a build via ProtonPlus",
                )
            )

        for label, value in (
            ("CPU", sysinfo.cpu()),
            ("Memory", sysinfo.memory()),
            ("Disks", " · ".join(sysinfo.disks()) or "unknown"),
        ):
            runners.add(Adw.ActionRow(title=label, subtitle=value))
        left.append(runners)

        # --- Graphics -----------------------------------------------------
        graphics = pages.Section(
            "Graphics",
            "Which GPU the games use. Only the GPUs found on this machine are listed.",
        )
        preference = gpu.gpu_preference(config)
        gpu_options: list[tuple[str, str, str]] = [
            ("auto", "Auto", "Let the game choose, without forcing a GPU.")
        ]
        if gpu.nvidia_driver_info()[0] is not None:
            gpu_options.append(
                (
                    "nvidia",
                    "Dedicated",
                    'Forces DXVK_FILTER_DEVICE_NAME = "NVIDIA" (the dedicated GPU).',
                )
            )
        integrated = gpu.integrated_gpu_name()
        if integrated:
            gpu_options.append(
                (
                    "integrated",
                    "Integrated",
                    f"Same GPU as the screen ({integrated}, detected automatically). "
                    "Troubleshooting mode if the NVIDIA path causes GPU hangs.",
                )
            )
        if not any(value == preference for value, _, _ in gpu_options):
            preference = "auto"
        gpu_group: Gtk.CheckButton | None = None
        for value, title, help_text in gpu_options:
            row = Adw.ActionRow(title=title)
            radio = Gtk.CheckButton()
            radio.set_valign(Gtk.Align.CENTER)
            radio.set_tooltip_text(f"Use {title}")
            if gpu_group is None:
                gpu_group = radio
            else:
                radio.set_group(gpu_group)
            radio.set_active(value == preference)
            radio.connect(
                "toggled",
                lambda button, val=value: (
                    pages._pick_gpu(window, val) if button.get_active() else None
                ),
            )
            row.add_prefix(radio)
            row.add_suffix(pages._help_button(help_text))
            graphics.add(row)
        graphics.add(Adw.ActionRow(title="GPU", subtitle=" · ".join(sysinfo.gpus()) or "unknown"))
        right.append(graphics)

        # --- Paths --------------------------------------------------------
        paths = pages.Section("Paths", "Where the installer, config and logs live.")
        installer_row = Adw.ActionRow(title="Installer")
        open_button = pages._button(
            "Open folder", tooltip="Open the folder where the installer is cached"
        )
        buttons.add_widget(open_button)
        open_button.connect("clicked", lambda *_: pages._open_folder(config.bnet_dir))
        installer_row.add_suffix(open_button)
        paths.add(installer_row)

        def refresh_installer() -> None:
            installer_row.set_subtitle(
                f"{config.installer.name}, {pages._installer_state(config.installer)}"
            )

        refresh_installer()
        paths.add(pages._kv("Config", str(config.config_file)))

        log_row = Adw.ActionRow(title="Logs", subtitle=str(config.log_dir))
        log_button = pages._button("View", tooltip="Run and installation logs")
        buttons.add_widget(log_button)
        log_button.connect("clicked", lambda *_: pages._show_logs(window))
        log_row.add_suffix(log_button)
        paths.add(log_row)
        right.append(paths)

        # --- Diagnostics & about -----------------------------------------
        more = pages.Section("Diagnostics & about", "Check the system or read about the app.")
        diag_row = Adw.ActionRow(title="System check")
        diag_button = pages._button("Run", tooltip="Run the system check")
        buttons.add_widget(diag_button)
        diag_button.connect(
            "clicked",
            lambda *_: pages._show_recommendations(window, recommend.report(Config.load())),
        )
        diag_row.add_suffix(diag_button)
        more.add(diag_row)

        about_row = Adw.ActionRow(title="Frostfire Installer")
        about_row.add_prefix(pages._icon(pages.MATERIAL["info"]))
        about_button = pages._button("About")
        buttons.add_widget(about_button)
        about_button.connect("clicked", lambda *_: pages._show_about(window))
        about_row.add_suffix(about_button)
        more.add(about_row)
        right.append(more)

        # --- Hide the reset/remove/keep rows when there is no client ------
        def refresh_sections() -> None:
            installed = battlenet.installed(Config.load())
            for row in (reinstall_row, remove_row, keep_row):
                row.set_visible(installed)

        refresh_sections()

        self.register_state(client_row.refresh)
        self.register_state(refresh_sections)
        self.register_state(refresh_installer)

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
