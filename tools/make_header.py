#!/usr/bin/env python3
"""Bake the product line into the banner.

The FROSTFIRE wordmark ships without a subtitle; this tool draws
"Battle.net installer" just below the wordmark, using the bundled Saira font, and
writes the banner that goes into the Python package.

Examples:
    python tools/make_header.py
    python tools/make_header.py --src assets/header/frostfire_installer_header_no_installer.png \
        --out src/frostfireinstaller/data/header/frostfire_installer_header.png --size-ratio 18
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = Path("src/frostfireinstaller/data/fonts/Saira.ttf")
DEFAULT_TEXT = "Battle.net installer"
COLOR = (234, 249, 255)


def load_font(path: Path, size: int, weight: str) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size)
    try:
        font.set_variation_by_name(weight)
    except (OSError, ValueError):
        pass
    return font


def tracked_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    tracking: float,
) -> float:
    return sum(draw.textlength(char, font=font) for char in text) + tracking * max(len(text) - 1, 0)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: object,
    tracking: float,
) -> None:
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + tracking


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src",
        type=Path,
        default=Path("assets/header/frostfire_installer_header_no_installer.png"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("src/frostfireinstaller/data/header/frostfire_installer_header.png"),
    )
    parser.add_argument("--font", type=Path, default=FONT)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--weight", default="SemiBold")
    parser.add_argument("--size-ratio", type=float, default=18.0, help="image width / font size")
    parser.add_argument("--top", type=float, default=0.63, help="text top as a fraction of height")
    parser.add_argument("--tracking", type=float, default=0.10, help="letter spacing in em")
    parser.add_argument(
        "--max-width", type=int, default=1600, help="downscale the result to this width"
    )
    args = parser.parse_args()

    image = Image.open(args.src).convert("RGBA")
    width, height = image.size
    size = round(width / args.size_ratio)
    font = load_font(args.font, size, args.weight)
    tracking = size * args.tracking

    measure = ImageDraw.Draw(image)
    text_width = tracked_width(measure, args.text, font, tracking)
    position = ((width - text_width) / 2, height * args.top)

    # Soft dark halo so the line stays readable over trees and mountains.
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw_tracked(ImageDraw.Draw(shadow), position, args.text, font, (2, 10, 20, 210), tracking)
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.10))
    image = Image.alpha_composite(image, shadow)

    draw_tracked(ImageDraw.Draw(image), position, args.text, font, (*COLOR, 255), tracking)

    if args.max_width and image.width > args.max_width:
        height = round(image.height * args.max_width / image.width)
        image = image.resize((args.max_width, height), Image.LANCZOS)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out, optimize=True)
    print(f"wrote {args.out} ({image.width}x{image.height}, font {size}px at {args.top:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
