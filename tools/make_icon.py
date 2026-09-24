#!/usr/bin/env python3
"""Derive the app icon set from a square master PNG.

Applies a rounded-square mask (transparent corners) and writes every size the
freedesktop icon theme expects, plus a 512 px copy for the Python package.

Examples:
    python tools/make_icon.py --src assets/icon/frostfireinstaller.png --install
    python tools/make_icon.py --src assets/icon/frostfireinstaller.png --out-dir /tmp/icons
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw

APP_ID = "io.github.epatnor.frostfireinstaller"
SIZES = (16, 24, 32, 48, 64, 128, 256, 512)
RADIUS_RATIO = 224 / 1024
SUPERSAMPLE = 4


def rounded(image: Image.Image, radius_ratio: float = RADIUS_RATIO) -> Image.Image:
    image = image.convert("RGBA")
    size = image.width
    radius = round(size * radius_ratio)
    mask = Image.new("L", (size * SUPERSAMPLE, size * SUPERSAMPLE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * SUPERSAMPLE - 1, size * SUPERSAMPLE - 1),
        radius=radius * SUPERSAMPLE,
        fill=255,
    )
    mask = mask.resize((size, size), Image.LANCZOS)
    image.putalpha(mask)
    return image


def write_set(master: Image.Image, out_dir: Path) -> list[Path]:
    written = []
    for size in SIZES:
        target = out_dir / f"{size}x{size}/apps" / f"{APP_ID}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        master.resize((size, size), Image.LANCZOS).save(target, optimize=True)
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, type=Path, help="square master PNG")
    parser.add_argument("--out-dir", type=Path, default=None, help="icon theme root")
    parser.add_argument(
        "--install", action="store_true", help="write into ~/.local/share/icons/hicolor"
    )
    parser.add_argument("--repo-copy", type=Path, default=None, help="512 px copy for the package")
    args = parser.parse_args()

    if not args.install and args.out_dir is None:
        parser.error("pass --install or --out-dir")

    master = rounded(Image.open(args.src))
    if master.width != master.height:
        parser.error(f"master must be square, got {master.width}x{master.height}")

    if args.install:
        data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
        out_dir = data_home / "icons/hicolor"
    else:
        out_dir = args.out_dir
    assert out_dir is not None
    for path in write_set(master, out_dir):
        print(f"wrote {path}")

    if args.repo_copy:
        args.repo_copy.parent.mkdir(parents=True, exist_ok=True)
        master.resize((512, 512), Image.LANCZOS).save(args.repo_copy, optimize=True)
        print(f"wrote {args.repo_copy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
