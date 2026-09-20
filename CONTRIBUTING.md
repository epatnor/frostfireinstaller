# Contributing

Thanks for wanting to help! `frostfireinstaller` aims to be a stable, well-tested project.

## Development setup

```bash
git clone https://github.com/epatnor/frostfireinstaller
cd frostfireinstaller
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Checks (run before a PR)

```bash
ruff check .
ruff format --check .
mypy
pytest
python -m build          # wheel + sdist must build
```

## Tools (developer-only, never bundled)

```bash
# Concept/hero art via the OpenAI Images API (key from env or a gitignored file)
python tools/genassets.py --prompt "..." --out assets/generated/hero.png

# Derive the app icon set from a square master PNG
python tools/make_icon.py --src assets/icon/frostfireinstaller.png \
    --install --repo-copy src/frostfireinstaller/data/icons/frostfireinstaller.png
```

Never commit API keys: `.env`, `*.key` and `assets/generated/` are gitignored.

## Guidelines

- Keep the **core** GUI-free and dependency-light (stdlib first).
- Every behavior change needs a test where feasible.
- Update `CHANGELOG.md`.
- Be kind in issues and reviews (see `CODE_OF_CONDUCT.md`).

## Commit style

Conventional Commits, e.g. `feat(core): detect UMU-Proton builds`.
