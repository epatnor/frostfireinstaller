#!/usr/bin/env python3
"""Render the main and Settings windows to PNG (for design work and the README).

The windows are shown briefly, given time for the background checks to fill
in, then each one is rendered through GTK's own renderer - so the image is
exactly what GTK draws, without the compositor's decorations or shadows.

    python3 tools/screenshot.py                 # -> preview/main.png, preview/settings.png
    python3 tools/screenshot.py --out assets/screenshots --delay 3

Runs from a checkout (uses ``src/``) under a separate app id, so it does not
collide with an instance of the app that is already running.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Graphene", "1.0")
from gi.repository import Adw, Gio, GLib, Graphene, Gtk  # noqa: E402

from frostfireinstaller.gui.application import APP_ID, FrostfireApplication  # noqa: E402
from frostfireinstaller.gui.window import MainWindow  # noqa: E402


def save(window: Gtk.Window, path: Path) -> None:
    width, height = window.get_width(), window.get_height()
    snapshot = Gtk.Snapshot()
    Gtk.WidgetPaintable.new(window).snapshot(snapshot, width, height)
    node = snapshot.to_node()
    if node is None:
        raise RuntimeError(f"nothing rendered for {path.name}")
    renderer = window.get_native().get_renderer()
    rect = Graphene.Rect().init(0, 0, width, height)
    renderer.render_texture(node, rect).save_to_png(str(path))
    print(f"{path} ({width}x{height})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "preview")
    parser.add_argument("--delay", type=float, default=2.5, help="seconds to let checks finish")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    app = Adw.Application(
        application_id=f"{APP_ID}.Screenshot", flags=Gio.ApplicationFlags.NON_UNIQUE
    )
    status = {"code": 0}

    def capture(window: MainWindow) -> bool:
        try:
            save(window, args.out / "main.png")
            settings = window._settings
            if settings is not None:
                save(settings, args.out / "settings.png")
        except Exception as exc:  # noqa: BLE001
            print(f"error: {exc}", file=sys.stderr)
            status["code"] = 1
        app.quit()
        return False

    def activate(application: Adw.Application) -> None:
        FrostfireApplication._load_css(application)  # type: ignore[arg-type]
        window = MainWindow(application=application)
        window.present()
        window.open_settings()
        GLib.timeout_add(int(args.delay * 1000), capture, window)

    app.connect("activate", activate)
    app.run([sys.argv[0]])
    return status["code"]


if __name__ == "__main__":
    raise SystemExit(main())
