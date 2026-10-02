"""Dialogs: logs, the system check / recommendations, about."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import __version__, service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import gpu, recommend  # noqa: E402
from .helpers import run_async  # noqa: E402
from .widgets import MATERIAL, button, command_row, icon  # noqa: E402


def _dialog(title: str, content: Gtk.Widget, width: int, height: int) -> Adw.Dialog:
    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(Adw.HeaderBar())
    toolbar.set_content(content)
    dialog = Adw.Dialog()
    dialog.set_title(title)
    dialog.set_content_width(width)
    dialog.set_content_height(height)
    dialog.set_child(toolbar)
    return dialog


def _padded_box(spacing: int, margin: int) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    for side in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{side}")(margin)
    return box


def show_logs(parent: Gtk.Widget) -> None:
    config = Config.load()
    logs = (
        sorted(config.log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if config.log_dir.is_dir()
        else []
    )
    dropdown = Gtk.DropDown.new_from_strings([path.name for path in logs] or ["(no logs)"])
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

    box = _padded_box(6, 12)
    box.append(dropdown)
    scroller = Gtk.ScrolledWindow(vexpand=True)
    scroller.set_child(view)
    box.append(scroller)
    _dialog("Logs", box, 820, 600).present(parent)


def _persistenced_control() -> Gtk.Widget:
    """Reversible in-app mitigation: keep the GPU initialised (nvidia-persistenced)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    active = gpu.persistenced_state() == "active"
    toggle = button(
        "Disable GPU persistence" if active else "Enable GPU persistence",
        primary=not active,
    )
    note = Gtk.Label(
        label="Reversible - run again to turn it off. Requires your password confirmation.",
        xalign=0,
    )
    note.set_wrap(True)
    note.add_css_class("section-desc")

    def on_click(*_args: object) -> None:
        enable = gpu.persistenced_state() != "active"
        toggle.set_sensitive(False)
        note.set_label("Waiting for authorisation ...")

        def done(_result: object) -> None:
            toggle.set_sensitive(True)
            toggle.set_label("Disable GPU persistence" if enable else "Enable GPU persistence")
            note.set_label("Done - restart the game and test." if enable else "Turned off.")

        def error(exc: Exception) -> None:
            toggle.set_sensitive(True)
            note.set_label(f"Failed: {exc}")

        run_async(lambda: service.set_persistenced(enable), done, error)

    toggle.connect("clicked", on_click)
    box.append(toggle)
    box.append(note)
    return box


_LEVEL_ICONS = {
    "warn": (MATERIAL["info"], "fire"),
    "info": (MATERIAL["info"], "ice"),
    "ok": (MATERIAL["check"], "green"),
}


def show_recommendations(parent: Gtk.Widget, items: list[recommend.Recommendation]) -> None:
    box = _padded_box(16, 16)
    for item in items:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        glyph, tone = _LEVEL_ICONS.get(item.level, (MATERIAL["info"], None))
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head.append(icon(glyph, tone))
        title = Gtk.Label(xalign=0)
        title.set_markup(f"<b>{GLib.markup_escape_text(item.title)}</b>")
        title.set_wrap(True)
        head.append(title)
        card.append(head)

        for text, css in ((item.detail, None), (item.action, "section-desc")):
            if text:
                label = Gtk.Label(label=text, xalign=0)
                label.set_wrap(True)
                if css:
                    label.add_css_class(css)
                card.append(label)

        for command in item.commands:
            card.append(command_row(command))
        if item.action_id == "persistenced":
            card.append(_persistenced_control())
        box.append(card)

    scroller = Gtk.ScrolledWindow(vexpand=True)
    scroller.set_child(box)
    _dialog("Recommendations", scroller, 620, 540).present(parent)


def show_about(parent: Gtk.Widget) -> None:
    Adw.AboutDialog(
        application_name="Frostfire Installer",
        application_icon="applications-games-symbolic",
        version=__version__,
        developer_name="frostfireinstaller contributors",
        comments="A Battle.net installer helper for Linux (umu-launcher + Proton).",
        license_type=Gtk.License.MIT_X11,
    ).present(parent)
