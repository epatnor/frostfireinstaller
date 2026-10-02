"""Shared building blocks: glyphs, buttons, cards, the activity strip.

The visual language (flat bordered panels, thin separators, small radii,
gradient buttons, uppercase section labels) is modelled on the Battle.net
launcher, but uses our own frost/fire palette (CSS in ``application.py``).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk, Pango  # noqa: E402

# Material Symbols glyphs (subset of the variable font, see data/fonts).
MATERIAL = {
    "download": "",
    "play": "",
    "build": "",
    "stop": "",
    "refresh": "",
    "delete": "",
    "info": "",
    "check": "",
    "settings": "",
}


class Surface(Protocol):
    """What background actions report to: the main or the settings window."""

    def toast(self, message: str) -> None: ...
    def set_activity(self, message: str) -> None: ...
    def clear_activity(self) -> None: ...
    def refresh_state(self) -> None: ...


def reporter(surface: Surface) -> Callable[[str], None]:
    """A thread-safe progress callback that shows steps in the activity strip."""

    def report(message: str) -> None:
        GLib.idle_add(surface.set_activity, message)

    return report


def icon(glyph: str, tone: str | None = None, filled: bool = False) -> Gtk.Label:
    label = Gtk.Label(label=glyph)
    label.add_css_class("material-icon-filled" if filled else "material-icon")
    if tone is not None:
        label.add_css_class(f"icon-{tone}")
    return label


def button(
    label: str,
    *,
    primary: bool = False,
    danger: bool = False,
    tooltip: str | None = None,
) -> Gtk.Button:
    widget = Gtk.Button(label=label)
    widget.set_valign(Gtk.Align.CENTER)
    if danger:
        widget.add_css_class("bn-btn-danger")
    elif primary:
        widget.add_css_class("bn-btn-primary")
    else:
        widget.add_css_class("bn-btn")
    if tooltip is not None:
        widget.set_tooltip_text(tooltip)
    return widget


def help_button(text: str) -> Gtk.MenuButton:
    """A round "(i)" button whose popover carries the explanation."""
    label = Gtk.Label(label=text)
    label.set_wrap(True)
    label.set_max_width_chars(42)
    for side in ("top", "bottom", "start", "end"):
        getattr(label, f"set_margin_{side}")(10)

    popover = Gtk.Popover()
    popover.set_child(label)

    widget = Gtk.MenuButton()
    widget.set_icon_name("help-about-symbolic")
    widget.add_css_class("help-button")
    widget.set_valign(Gtk.Align.CENTER)
    widget.set_popover(popover)
    return widget


def kv(title: str, value: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, subtitle=value)


def toolbar_page(title: str, content: Gtk.Widget) -> tuple[Adw.ToolbarView, Adw.WindowTitle]:
    view = Adw.ToolbarView()
    header = Adw.HeaderBar()
    title_widget = Adw.WindowTitle(title=title)
    header.set_title_widget(title_widget)
    view.add_top_bar(header)
    view.set_content(content)
    return view, title_widget


def open_folder(path: Path) -> None:
    """Open a folder in the desktop file manager."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607
    except OSError:
        pass


def installer_state(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError:
        return "missing, will download on next start"
    return f"{size / 1024**2:.1f} MB, downloaded and cached"


def copy_to_clipboard(text: str) -> None:
    display = Gdk.Display.get_default()
    if display is not None:
        display.get_clipboard().set(text)


def command_row(command: str) -> Gtk.Widget:
    """A read-only command with a Copy button."""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    entry = Gtk.Entry()
    entry.set_text(command)
    entry.set_editable(False)
    entry.set_hexpand(True)
    entry.add_css_class("monospace")
    copy_button = button("Copy", tooltip="Copy the command to the clipboard")

    def copy(*_args: object) -> None:
        copy_to_clipboard(command)
        copy_button.set_label("Copied")

    copy_button.connect("clicked", copy)
    row.append(entry)
    row.append(copy_button)
    return row


class Section(Gtk.Box):
    """A card: a bordered panel whose first row is the header, then the rows."""

    def __init__(self, title: str, description: str | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("bn-section")

        self.rows = Gtk.ListBox()
        self.rows.set_selection_mode(Gtk.SelectionMode.NONE)
        self.rows.set_vexpand(True)
        self.rows.add_css_class("bn-panel")

        head = Gtk.ListBoxRow()
        head.set_activatable(False)
        head.set_selectable(False)
        head.set_focusable(False)
        head.add_css_class("card-head")
        head_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("card-title")
        head_box.append(heading)
        if description is not None:
            note = Gtk.Label(label=description, xalign=0)
            note.set_wrap(True)
            note.add_css_class("card-desc")
            head_box.append(note)
        head.set_child(head_box)
        self.rows.append(head)

        self.append(self.rows)

    def add(self, row: Gtk.Widget) -> None:
        self.rows.append(row)


class ActivityBar(Gtk.Box):
    """Thin strip that shows the operation currently running (spinner + text)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add_css_class("activity-bar")
        self.spinner = Gtk.Spinner()
        self.spinner.set_valign(Gtk.Align.CENTER)
        self.label = Gtk.Label(xalign=0)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.append(self.spinner)
        self.append(self.label)
        self.set_visible(False)

    def show(self, text: str) -> None:
        self.label.set_label(text)
        self.spinner.start()
        self.set_visible(True)

    def hide(self) -> None:
        self.spinner.stop()
        self.set_visible(False)
