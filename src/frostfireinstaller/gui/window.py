"""Main window: a single column (header bar -> banner -> features)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib  # noqa: E402

from . import pages  # noqa: E402
from .state import ClientState  # noqa: E402
from .widgets import ActivityBar  # noqa: E402

Refresher = Callable[[ClientState], None]

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


class MainWindow(Adw.ApplicationWindow):
    """The launcher window, and the hub that refreshes every state widget.

    Widgets in both windows register a refresher here; ``refresh_state`` reads
    one ``ClientState`` and hands it to all of them. It runs after every action
    and whenever a window gains focus, so values changed on disk (or a client
    that was closed outside the app) show up without a restart.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title("Frostfire Installer")
        # Fixed 608 px wide so the banner fills the window; pages.build_main
        # sets the height from the banner. This is only the pre-build fallback.
        self.set_resizable(False)
        self.set_default_size(pages.WINDOW_WIDTH, 350)

        self._refreshers: list[Refresher] = []
        self._title: Adw.WindowTitle | None = None
        self._run_bar: pages.RunBar | None = None
        self._activity: ActivityBar | None = None
        self._settings: Any = None
        self._tray: Any = None

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(pages.build_main(self))
        self.set_content(self.toasts)
        self.connect("notify::is-active", self._on_focus)
        self.refresh_state()

    def attach(
        self, *, title: Adw.WindowTitle, run_bar: pages.RunBar, activity: ActivityBar
    ) -> None:
        self._title = title
        self._run_bar = run_bar
        self._activity = activity

    def set_tray(self, tray: Any) -> None:
        self._tray = tray
        self.refresh_state()

    def toggle_battlenet(self) -> None:
        if self._run_bar is not None:
            self._run_bar.trigger()

    def open_settings(self) -> None:
        """Open (or re-focus) the standalone settings window."""
        if self._settings is None:
            from .settings import SettingsWindow

            self._settings = SettingsWindow(self)
        self._settings.present()

    def settings_closed(self) -> None:
        self._settings = None

    # --- state ------------------------------------------------------------
    def register_state(self, refresher: Refresher) -> None:
        self._refreshers.append(refresher)

    def unregister_state(self, refresher: Refresher) -> None:
        if refresher in self._refreshers:
            self._refreshers.remove(refresher)

    def refresh_state(self) -> None:
        state = ClientState.read()
        for refresher in list(self._refreshers):
            refresher(state)
        self._show_running(state)

    def _on_focus(self, *_args: object) -> None:
        if self.is_active():
            self.refresh_state()

    def _show_running(self, state: ClientState) -> None:
        """Mirror the client state in the title, taskbar badge and tray icon.

        So it is still obvious after the machine wakes from suspend, even with
        both windows minimised.
        """
        if self._title is not None:
            self._title.set_subtitle(state.summary)
        set_running_badge(state.running)
        if self._tray is not None:
            self._tray.set_state(state.running, state.installed)

    # --- Surface ----------------------------------------------------------
    def set_activity(self, message: str) -> None:
        if self._activity is not None:
            self._activity.show(message)

    def clear_activity(self) -> None:
        if self._activity is not None:
            self._activity.hide()

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))
