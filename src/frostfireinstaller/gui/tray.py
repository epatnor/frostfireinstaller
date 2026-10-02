"""A StatusNotifierItem tray icon for the GTK4 app.

GTK4 cannot load the GTK3 ``AppIndicator3``/``XApp`` bindings in the same
process, so instead of a library we speak the tray protocol directly: the
``org.kde.StatusNotifierItem`` interface plus a minimal ``com.canonical.dbusmenu``
menu, registered with the ``org.kde.StatusNotifierWatcher`` that KDE Plasma (and
GNOME, with an AppIndicator extension) runs. Everything uses Gio only.

The icon stays visible while the app runs and carries the Battle.net state in its
tooltip and menu, so the client is findable even when every window is minimised.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib  # noqa: E402

from .helpers import data_file  # noqa: E402

_SNI_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionMovieName" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewIcon"/>
    <signal name="NewStatus">
      <arg type="s"/>
    </signal>
    <signal name="NewTitle"/>
    <signal name="NewToolTip"/>
  </interface>
</node>
"""

_MENU_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg type="i" name="parentId" direction="in"/>
      <arg type="i" name="recursionDepth" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="u" name="revision" direction="out"/>
      <arg type="(ia{sv}av)" name="layout" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="as" name="propertyNames" direction="in"/>
      <arg type="a(ia{sv})" name="properties" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="name" direction="in"/>
      <arg type="v" name="value" direction="out"/>
    </method>
    <method name="Event">
      <arg type="i" name="id" direction="in"/>
      <arg type="s" name="eventId" direction="in"/>
      <arg type="v" name="data" direction="in"/>
      <arg type="u" name="timestamp" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg type="a(isvu)" name="events" direction="in"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg type="i" name="id" direction="in"/>
      <arg type="b" name="needUpdate" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg type="ai" name="ids" direction="in"/>
      <arg type="ai" name="updatesNeeded" direction="out"/>
      <arg type="ai" name="idErrors" direction="out"/>
    </method>
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <signal name="LayoutUpdated">
      <arg type="u" name="revision"/>
      <arg type="i" name="parent"/>
    </signal>
    <signal name="ItemsPropertiesUpdated">
      <arg type="a(ia{sv})" name="updatedProps"/>
      <arg type="a(ias)" name="removedProps"/>
    </signal>
  </interface>
</node>
"""

_SHOW = 1
_TOGGLE = 3
_QUIT = 5
_SEPARATORS = {2, 4}
_ROOT_CHILDREN = [1, 2, 3, 4, 5]

# The tray uses a dedicated monochrome gateway glyph so it matches the other
# (symbolic) panel icons; the launcher/taskbar icon stays the colour app icon.
_ICON_NAME = ""
_TRAY_SIZES = (16, 22, 24, 32, 48)


def _argb_pixmap(pixbuf: GdkPixbuf.Pixbuf) -> tuple[int, int, bytes]:
    """Convert one pixbuf to the ARGB32 bytes the SNI IconPixmap wants."""
    width, height = pixbuf.get_width(), pixbuf.get_height()
    channels = pixbuf.get_n_channels()
    rowstride = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()
    data = bytearray()
    for y in range(height):
        row = y * rowstride
        for x in range(width):
            offset = row + x * channels
            red, green, blue = pixels[offset], pixels[offset + 1], pixels[offset + 2]
            alpha = pixels[offset + 3] if channels == 4 else 255
            data += bytes((alpha, red, green, blue))
    return (width, height, bytes(data))


def _argb_pixmaps() -> list[tuple[int, int, bytes]]:
    """The monochrome tray glyph at several sizes, for crisp panel scaling.

    The glyph is drawn 2 px shorter than the square (1 px transparent top and
    bottom), so it lines up in height with the other panel icons.
    """
    path = data_file("icons", "frostfireinstaller-tray.png")
    if path is None:
        return []
    pixmaps: list[tuple[int, int, bytes]] = []
    for size in _TRAY_SIZES:
        inner = max(1, size - 2)
        try:
            glyph = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, inner, False)
            if not glyph.get_has_alpha():
                glyph = glyph.add_alpha(False, 0, 0, 0)
            canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
            canvas.fill(0x00000000)
            glyph.composite(
                canvas,
                0,
                1,
                size,
                inner,
                0,
                0,
                1.0,
                1.0,
                GdkPixbuf.InterpType.BILINEAR,
                255,
            )
        except GLib.Error:
            continue
        pixmaps.append(_argb_pixmap(canvas))
    return pixmaps


class TrayIcon:
    """A tray icon driven by the StatusNotifierItem protocol."""

    def __init__(
        self,
        app_id: str,
        on_activate: Callable[[], None],
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._app_id = app_id
        self._on_activate = on_activate
        self._on_toggle = on_toggle
        self._on_quit = on_quit

        self._title = "Frostfire Installer"
        self._tooltip = "Battle.net state unknown"
        self._status = "Active"
        self._labels = {
            _SHOW: "Show Frostfire Installer",
            _TOGGLE: "Start Battle.net",
            _QUIT: "Quit",
        }
        self._revision = 1
        self._pixmap = _argb_pixmaps()

        self._connection: Gio.DBusConnection | None = None
        self._sni_registration = 0
        self._menu_registration = 0
        self._name_id = 0
        self._bus_name = f"org.kde.StatusNotifierItem-{os.getpid()}-1"
        self._attempts = 0
        self._start()

    # --- setup -----------------------------------------------------------
    def _start(self) -> None:
        try:
            self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            self._connection = None
            return

        sni_info = Gio.DBusNodeInfo.new_for_xml(_SNI_XML).interfaces[0]
        menu_info = Gio.DBusNodeInfo.new_for_xml(_MENU_XML).interfaces[0]
        self._sni_registration = self._connection.register_object(
            "/StatusNotifierItem", sni_info, self._sni_call, self._sni_property, None
        )
        self._menu_registration = self._connection.register_object(
            "/MenuBar", menu_info, self._menu_call, self._menu_property, None
        )
        self._name_id = Gio.bus_own_name_on_connection(
            self._connection, self._bus_name, Gio.BusNameOwnerFlags.NONE, None, None
        )
        GLib.timeout_add_seconds(1, self._register)

    def _register(self) -> bool:
        """Tell the tray host we exist; retry until a watcher answers."""
        if self._connection is None:
            return False
        self._attempts += 1
        try:
            self._connection.call_sync(
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (self._bus_name,)),
                None,
                Gio.DBusCallFlags.NONE,
                2000,
                None,
            )
            return False
        except GLib.Error:
            return self._attempts < 30

    def close(self) -> None:
        if self._connection is None:
            return
        if self._sni_registration:
            self._connection.unregister_object(self._sni_registration)
        if self._menu_registration:
            self._connection.unregister_object(self._menu_registration)
        if self._name_id:
            Gio.bus_unown_name(self._name_id)
        self._connection = None

    # --- state -----------------------------------------------------------
    def set_state(self, running: bool, installed: bool) -> None:
        if running:
            self._title = "Frostfire Installer - Battle.net running"
            self._tooltip = "Battle.net is running"
            self._labels[_TOGGLE] = "Stop Battle.net"
        elif installed:
            self._title = "Frostfire Installer"
            self._tooltip = "Battle.net is stopped"
            self._labels[_TOGGLE] = "Start Battle.net"
        else:
            self._title = "Frostfire Installer"
            self._tooltip = "Battle.net is not installed"
            self._labels[_TOGGLE] = "Install Battle.net"
        if self._connection is None:
            return
        self._revision += 1
        self._connection.emit_signal(
            None, "/StatusNotifierItem", "org.kde.StatusNotifierItem", "NewTitle", None
        )
        self._connection.emit_signal(
            None,
            "/StatusNotifierItem",
            "org.kde.StatusNotifierItem",
            "NewStatus",
            GLib.Variant("(s)", (self._status,)),
        )
        self._connection.emit_signal(
            None, "/StatusNotifierItem", "org.kde.StatusNotifierItem", "NewToolTip", None
        )
        self._connection.emit_signal(
            None,
            "/MenuBar",
            "com.canonical.dbusmenu",
            "LayoutUpdated",
            GLib.Variant("(ui)", (self._revision, 0)),
        )

    # --- StatusNotifierItem ----------------------------------------------
    def _sni_property(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _interface: str,
        prop: str,
    ) -> GLib.Variant | None:
        values = {
            "Category": GLib.Variant("s", "ApplicationStatus"),
            "Id": GLib.Variant("s", self._app_id),
            "Title": GLib.Variant("s", self._title),
            "Status": GLib.Variant("s", self._status),
            "WindowId": GLib.Variant("i", 0),
            "IconName": GLib.Variant("s", _ICON_NAME),
            "IconPixmap": GLib.Variant("a(iiay)", self._pixmap),
            "OverlayIconName": GLib.Variant("s", ""),
            "OverlayIconPixmap": GLib.Variant("a(iiay)", []),
            "AttentionIconName": GLib.Variant("s", ""),
            "AttentionIconPixmap": GLib.Variant("a(iiay)", []),
            "AttentionMovieName": GLib.Variant("s", ""),
            "ToolTip": GLib.Variant("(sa(iiay)ss)", ("", [], self._title, self._tooltip)),
            "ItemIsMenu": GLib.Variant("b", True),
            "Menu": GLib.Variant("o", "/MenuBar"),
        }
        return values.get(prop)

    def _sni_call(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _interface: str,
        method: str,
        _params: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        if method == "Activate":
            self._on_activate()
        invocation.return_value(None)

    # --- DBusMenu --------------------------------------------------------
    def _menu_property(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _interface: str,
        prop: str,
    ) -> GLib.Variant | None:
        values = {
            "Version": GLib.Variant("u", 3),
            "TextDirection": GLib.Variant("s", "ltr"),
            "Status": GLib.Variant("s", "normal"),
            "IconThemePath": GLib.Variant("as", []),
        }
        return values.get(prop)

    def _item_props(self, item_id: int) -> dict[str, GLib.Variant]:
        if item_id == 0:
            return {}
        if item_id in _SEPARATORS:
            return {"type": GLib.Variant("s", "separator"), "visible": GLib.Variant("b", True)}
        return {
            "label": GLib.Variant("s", self._labels.get(item_id, "")),
            "enabled": GLib.Variant("b", True),
            "visible": GLib.Variant("b", True),
        }

    def _layout(self, item_id: int) -> tuple[int, dict[str, GLib.Variant], list[GLib.Variant]]:
        children: list[GLib.Variant] = []
        if item_id == 0:
            children = [
                GLib.Variant("(ia{sv}av)", self._layout(child_id))
                for child_id in _ROOT_CHILDREN
            ]
        return (item_id, self._item_props(item_id), children)

    def _handle_click(self, item_id: int) -> None:
        if item_id == _SHOW:
            self._on_activate()
        elif item_id == _TOGGLE:
            self._on_toggle()
        elif item_id == _QUIT:
            self._on_quit()

    def _menu_call(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _path: str,
        _interface: str,
        method: str,
        params: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        if method == "GetLayout":
            layout = GLib.Variant("(u(ia{sv}av))", (self._revision, self._layout(0)))
            invocation.return_value(layout)
        elif method == "GetGroupProperties":
            ids, _names = params.unpack()
            result = [(item_id, self._item_props(item_id)) for item_id in ids]
            invocation.return_value(GLib.Variant("(a(ia{sv}))", (result,)))
        elif method == "GetProperty":
            item_id, name = params.unpack()
            props = self._item_props(item_id)
            if name in props:
                invocation.return_value(GLib.Variant("(v)", (props[name],)))
            else:
                invocation.return_error_literal(
                    Gio.DBusError, Gio.DBusError.UNKNOWN_PROPERTY, name
                )
        elif method == "Event":
            item_id, event_id, _data, _timestamp = params.unpack()
            if event_id == "clicked":
                self._handle_click(item_id)
            invocation.return_value(None)
        elif method == "EventGroup":
            events = params.unpack()[0]
            for item_id, event_id, _data, _timestamp in events:
                if event_id == "clicked":
                    self._handle_click(item_id)
            invocation.return_value(GLib.Variant("(ai)", ([],)))
        elif method == "AboutToShow":
            invocation.return_value(GLib.Variant("(b)", (False,)))
        elif method == "AboutToShowGroup":
            invocation.return_value(GLib.Variant("(aiai)", ([], [])))
        else:
            invocation.return_error_literal(
                Gio.DBusError, Gio.DBusError.UNKNOWN_METHOD, method
            )
