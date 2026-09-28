#!/usr/bin/env python3
"""Generate raster assets (banners, hero art, textures) via the OpenAI Images API.

The API key is NEVER stored in this repository. Provide it via (first match wins):
  - ``--key-file PATH`` (e.g. ``~/.config/frostfireinstaller/openai.key``, chmod 600)
  - environment variable ``OPENAI_API_KEY``
  - a ``.env`` file in the project root or ``~/.config/frostfireinstaller/.env``

Examples:
    OPENAI_API_KEY=... python tools/genassets.py --prompt "..." --out assets/generated/hero.png
    python tools/genassets.py --key-file ~/.config/frostfireinstaller/openai.key \
        --prompt "..." --out assets/generated/icon.png

Note: for functional app icons prefer hand-written SVG; use this for concept/hero/banner art.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-2.5-sunburst"


_DOTENV_CANDIDATES = (
    Path.cwd() / ".env",
    Path.home() / ".config/frostfireinstaller/.env",
)


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (no override, no deps)."""
    for path in _DOTENV_CANDIDATES:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)
        return


def load_key(key_file: str | None) -> str:
    if key_file:
        path = Path(key_file).expanduser()
        if not path.is_file():
            sys.exit(f"Key file not found: {path}")
        return path.read_text(encoding="utf-8").strip()
    _load_dotenv()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        sys.exit(
            "No API key. Set OPENAI_API_KEY, add a .env, or pass --key-file (never commit the key)."
        )
    return key


def _post(key: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:  # pragma: no cover - network
        body = exc.read().decode(errors="ignore")
        sys.exit(f"API error {exc.code}: {body}")


def generate(
    key: str,
    model: str,
    prompt: str,
    size: str,
    quality: str | None,
    out: Path,
    n: int = 1,
) -> None:
    payload: dict[str, object] = {"model": model, "prompt": prompt, "size": size, "n": n}
    if quality:
        payload["quality"] = quality

    data = _post(key, payload)
    items = data.get("data", [])
    if not items:
        sys.exit("Unexpected response: no image data")

    out.parent.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items):  # type: ignore[assignment]
        target = out if n == 1 else out.with_name(f"{out.stem}-{index}{out.suffix}")
        if item.get("b64_json"):
            target.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            with urllib.request.urlopen(item["url"], timeout=300) as resp:  # noqa: S310
                target.write_bytes(resp.read())
        else:
            sys.exit("Unexpected response: item has neither b64_json nor url")
        print(f"wrote {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default=None)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--key-file", default=None)
    args = parser.parse_args()

    key = load_key(args.key_file)
    generate(key, args.model, args.prompt, args.size, args.quality, args.out, args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
