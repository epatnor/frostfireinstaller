#!/usr/bin/env python3
"""Build the bundled Material Symbols subset used by the GUI.

The GUI only needs a handful of glyphs. We take Google's Material Symbols
variable font, pin the axes (outlined style, light weight) and keep just the
codepoints listed in ``frostfireinstaller.gui.pages.MATERIAL``.

Requires ``fonttools`` and ``brotli`` (dev-only):

    pip install fonttools brotli
    python tools/make_symbols.py
    python tools/make_symbols.py --fill 1 --family "Material Symbols Filled" \
        --out src/frostfireinstaller/data/fonts/MaterialSymbolsFilled.ttf

The first run downloads the variable font (~10 MB) into a cache; pass
``--src`` to use a local copy instead.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

SOURCE_URL = (
    "https://github.com/google/material-design-icons/raw/master/variablefont/"
    "MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D.ttf"
)
CACHE = Path("/tmp/opencode/MaterialSymbols-var.ttf")

# Keep in sync with pages.MATERIAL (download, play, build, stop, refresh,
# delete, info, expand_more, expand_less, check, settings).
CODEPOINTS = [
    0xF090,
    0xE037,
    0xF8CD,
    0xE047,
    0xE5D5,
    0xE92E,
    0xE88E,
    0xE5CF,
    0xE5CE,
    0xE5CA,
    0xE8B8,
]

DEFAULT_OUT = Path("src/frostfireinstaller/data/fonts/MaterialSymbols.ttf")


def ensure_source(path: Path, url: str) -> Path:
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, path)  # noqa: S310
    return path


def rename_font(font: TTFont, family: str) -> None:
    """Give the subset its own family name (so a filled variant can coexist)."""
    postscript = family.replace(" ", "")
    name = font["name"]
    for name_id, value in ((1, family), (3, family), (4, family), (6, postscript), (16, family)):
        name.setName(value, name_id, 3, 1, 0x409)
        name.setName(value, name_id, 1, 0, 0)


def build(
    src: Path,
    out: Path,
    fill: float,
    weight: float,
    grade: float,
    opsz: float,
    family: str | None = None,
) -> None:
    font = TTFont(src)
    instantiateVariableFont(
        font,
        {"FILL": fill, "wght": weight, "GRAD": grade, "opsz": opsz},
        inplace=True,
        updateFontNames=False,
    )
    options = subset.Options()
    options.layout_features = ["*"]
    options.notdef_outline = True
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes=CODEPOINTS)
    sub.subset(font)
    if family is not None:
        rename_font(font, family)
    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(out)
    print(f"wrote {out} ({out.stat().st_size} bytes, FILL={fill} wght={weight}, family={family})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=CACHE, help="variable font to subset")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fill", type=float, default=0.0, help="0 = outlined, 1 = filled")
    parser.add_argument("--weight", type=float, default=200.0)
    parser.add_argument("--grade", type=float, default=0.0)
    parser.add_argument("--opsz", type=float, default=24.0)
    parser.add_argument("--family", default=None, help="rename the subset to this family")
    args = parser.parse_args()

    src = ensure_source(args.src, SOURCE_URL)
    build(src, args.out, args.fill, args.weight, args.grade, args.opsz, args.family)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
