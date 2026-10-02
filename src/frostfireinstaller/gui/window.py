"""Main window: a single column (header bar -> banner -> features)."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from ..config import Config  # noqa: E402
from ..core import battlenet, health  # noqa: E402
from . import pages  # noqa: E402


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title("Frostfire Installer")
        # Fixed 608 px wide so the banner fills the window. The height is set by
        # pages.py from the banner's aspect ratio; the advanced options live in
        # their own resizable window (gui/settings.py). This is only the
        # pre-build fallback.
        self.set_resizable(False)
        self.set_default_size(608, 350)

        self._state_refreshers: list[Callable[[], None]] = []
        self._activity: pages.ActivityBar | None = None
        self._title_widget: Adw.WindowTitle | None = None
        self._run_bar: pages.RunBar | None = None
        self._tray: object | None = None
        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(pages.build_main(self))
        self.set_content(self.toasts)
        self.refresh_state()

    def set_title_widget(self, widget: Adw.WindowTitle) -> None:
        """Keep the header title so the running state can be shown in it."""
        self._title_widget = widget

    def set_run_bar(self, run_bar: pages.RunBar) -> None:
        """Keep the run bar so the tray icon can start/stop Battle.net too."""
        self._run_bar = run_bar

    def set_tray(self, tray: object) -> None:
        self._tray = tray
        self._update_running_indicator()

    def toggle_battlenet(self) -> None:
        if self._run_bar is not None:
            self._run_bar.trigger()

    def register_state(self, refresher: Callable[[], None]) -> None:
        """Widgets that show client state refresh themselves through here."""
        self._state_refreshers.append(refresher)

    def refresh_state(self) -> None:
        for refresher in self._state_refreshers:
            refresher()
        self._update_running_indicator()

    def _update_running_indicator(self) -> None:
        """Show, in the title, taskbar badge and tray icon, that Battle.net is up.

        The header subtitle follows the client state, the dock/taskbar icon gets
        a badge while Battle.net runs and the tray icon mirrors it - so it is
        still obvious after the machine wakes from suspend, even with both
        windows minimised.
        """
        running = health.running()
        installed = battlenet.installed(Config.load())
        if running:
            text = "Battle.net running"
        elif installed:
            text = "Battle.net stopped"
        else:
            text = "Battle.net not installed"
        if self._title_widget is not None:
            self._title_widget.set_subtitle(text)
        pages.set_running_badge(running)
        if self._tray is not None:
            self._tray.set_state(running, installed)  # type: ignore[attr-defined]

    def register_activity(self, bar: pages.ActivityBar) -> None:
        """The strip that shows what operation is running right now."""
        self._activity = bar

    def set_activity(self, message: str) -> None:
        if self._activity is not None:
            self._activity.show(message)

    def clear_activity(self) -> None:
        if self._activity is not None:
            self._activity.hide()

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))
