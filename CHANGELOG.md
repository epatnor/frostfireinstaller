# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Added
- `core`: distro/proton detection, umu runner, Battle.net install/launch/repair, health checks.
- Logging: per-run and per-installation logs with full diagnostics.
- **GUI** (GTK4 + libadwaita, `frostfireinstaller gui`): a single column with a full-bleed
  Frostfire banner and all features as rows; background operations with toasts.
- Reinstall / remove Battle.net with a **"Behåll spel"** (keep games) option.
- Performance toggles: MangoHud, GameMode, Gamescope (persisted in `config.toml`).
- Packaging: `install.sh` (curl | bash), Bazzite `ujust` recipe, Homebrew formula,
  experimental Flatpak manifest + AppStream metadata.
- Docs: `docs/architecture.md`, `docs/install.md`, `docs/design.md`.
- Tests (pytest) and CI (ruff / mypy / pytest).

### Changed
- **Renamed to Frostfire Installer** (`frostfireinstaller`): package, CLI
  (`frostfireinstaller`, `frostfireinstaller-gui`), app id `io.github.frostfireinstaller`,
  config/state paths, desktop entry and icon.
- Scope: a **Battle.net installer helper** (not a game launcher or library).
- GUI actions split into "Installation & underhåll" (ice) and "Återställ & ta bort" (fire).
- Icon install now includes the hicolor `index.theme` so the app icon resolves.
- New app icon: the frostfire gateway (half ice, half lava), installed as a full
  hicolor PNG set (16-512 px) via `tools/make_icon.py`; help popovers on the
  performance toggles.

### Notes
- Ported from the verified `bnetstarter` bash prototype (umu-launcher + GE-Proton on Bazzite).

## [0.1.0] - 2026-09-20
- First public scaffold.
