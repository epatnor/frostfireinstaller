# Contributing

Thanks for wanting to help! `frostfireinstaller` aims to be a stable, well-tested project.

## Development setup

```bash
git clone https://github.com/OWNER/frostfireinstaller
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
```

## Guidelines

- Keep the **core** GUI-free and dependency-light (stdlib first).
- Every behavior change needs a test where feasible.
- Update `CHANGELOG.md`.
- Be kind in issues and reviews (see `CODE_OF_CONDUCT.md`).

## Commit style

Conventional Commits, e.g. `feat(core): detect UMU-Proton builds`.
