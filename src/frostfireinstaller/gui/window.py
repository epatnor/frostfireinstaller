"""Main window: a single column (header bar -> banner -> features)."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from . import pages  # noqa: E402


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title("Frostfire Installer")
        # Fixed 608 px wide (the banner's size) so the banner fills the window
        # and keeps its exact size; pages.py only changes the height
        # (350 <-> 770) when the advanced sections are toggled.
        self.set_resizable(False)
        self.set_default_size(608, 350)

        self._state_refreshers: list[Callable[[], None]] = []
        self._activity: pages.ActivityBar | None = None
        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(pages.build_main(self))
        self.set_content(self.toasts)

    def register_state(self, refresher: Callable[[], None]) -> None:
        """Widgets that show client state refresh themselves through here."""
        self._state_refreshers.append(refresher)

    def refresh_state(self) -> None:
        for refresher in self._state_refreshers:
            refresher()

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
