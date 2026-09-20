"""Main window: sidebar navigation + content stack."""

from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from . import pages  # noqa: E402

_NAV = [
    ("home", "Hem", "go-home-symbolic"),
    ("install", "Installera", "folder-download-symbolic"),
    ("runners", "Runners", "applications-games-symbolic"),
    ("performance", "Prestanda", "power-profile-performance-symbolic"),
    ("logs", "Loggar", "text-x-generic-symbolic"),
    ("settings", "Inställningar", "preferences-system-symbolic"),
]


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title("frostylauncher")
        self.set_default_size(1000, 700)

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        split = Adw.NavigationSplitView()
        self.toasts.set_child(split)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(pages.build_home(self), "home")
        self.stack.add_named(pages.build_install(self), "install")
        self.stack.add_named(pages.build_runners(self), "runners")
        self.stack.add_named(pages.build_performance(self), "performance")
        self.stack.add_named(pages.build_logs(self), "logs")
        self.stack.add_named(pages.build_settings(self), "settings")

        split.set_sidebar(Adw.NavigationPage(title="frostylauncher", child=self._sidebar()))
        split.set_content(Adw.NavigationPage(title="frostylauncher", child=self.stack))

    def _sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="frostylauncher"))
        box.append(header)

        listbox = Gtk.ListBox()
        listbox.add_css_class("navigation-sidebar")
        for name, label, icon in _NAV:
            row = Adw.ActionRow(title=label)
            row.set_activatable(True)
            row.set_name(name)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            listbox.append(row)
        listbox.connect("row-selected", self._on_row_selected)
        initial = os.environ.get("FROSTYLAUNCHER_GUI_PAGE", "home")
        names = [name for name, _, _ in _NAV]
        index = names.index(initial) if initial in names else 0
        listbox.select_row(listbox.get_row_at_index(index))

        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(listbox)
        box.append(scroller)
        return box

    def _on_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is not None:
            self.stack.set_visible_child_name(row.get_name())

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))
