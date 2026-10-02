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

## Tools

`tools/` holds developer-only scripts (never bundled): `make_icon.py`, `make_header.py`,
`make_symbols.py`. See their docstrings.

## Guidelines

- Keep the **core** GUI-free and dependency-light (stdlib first).
- Every behavior change needs a test where feasible.
- Update `CHANGELOG.md`.
- **AI-assisted contributions are welcome but must be reviewed and tested by
  you.** Disclose it in the PR and say how you verified it — see
  [`docs/ai-disclosure.md`](docs/ai-disclosure.md).
- Be kind in issues and reviews.

## Commit style

Conventional Commits, e.g. `feat(core): detect UMU-Proton builds`.
