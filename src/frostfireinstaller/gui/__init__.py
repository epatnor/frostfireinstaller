"""GTK4 + libadwaita front-end for frostfireinstaller."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from .application import FrostfireApplication

    app = FrostfireApplication()
    return app.run(argv if argv is not None else [sys.argv[0]])
