"""Main window: a single column (header bar -> banner -> features)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from . import pages  # noqa: E402


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title("Frostfire Installer")
        self.set_default_size(760, 820)

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(pages.build_main(self))
        self.set_content(self.toasts)

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))
