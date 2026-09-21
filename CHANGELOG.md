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

- **Även installeraren** checkbox in the *Ta bort* row and `--purge-installer` (CLI):
  drop the cached `Battle.net-Setup.exe` so the download path can be re-tested.
- Avancerat → Sökvägar shows where the installer is cached and whether it is present.
- GUI: client status and *Reparera* share one row; logs moved under Avancerat
  (a *Visa* button on the Loggar row).
- **Battle.net band**: state, Proton and prefix moved from the info strip into the
  run bar (dimmed second line); the info strip is now a single line of system info.

### Fixed
- **Icon install** referenced the removed SVG, so a fresh setup got no app icon;
  the packaged PNG is now installed (and a stale SVG is cleaned up).
- **Config save** dropped hand-written keys (e.g. `[paths] bnet_dir`) and did not
  escape strings; it now merges with the existing file and escapes values.
- **Health check** treated "no X display" as a failure on Wayland, which could kill
  the client and wipe its CEF cache for no reason; unknown now means "fine".
- `kill_all()` sends SIGTERM before SIGKILL; the Wine user directory is discovered
  instead of assuming `steamuser`.

### Security
- Subprocess calls all pass argument lists (no shell); `proton.find()` rejects path
  traversal; `.desktop` Exec paths are quoted when they contain spaces.
- Renamed the leftover `FROSTYLAUNCHER_*` env vars to `FROSTFIREINSTALLER_*`.

### Changed
- **Renamed to Frostfire Installer** (`frostfireinstaller`): package, CLI
  (`frostfireinstaller`, `frostfireinstaller-gui`), app id `io.github.frostfireinstaller`,
  config/state paths, desktop entry and icon.
- Scope: a **Battle.net installer helper** (not a game launcher or library).
- **Consolidated actions**: the start button installs the client when missing
  ("Installera & starta"); the maintenance row is status-only (plus Reparera).
- GUI actions split into "Installation & underhåll" (ice) and "Återställ & ta bort" (fire).
- Icon install now includes the hicolor `index.theme` so the app icon resolves.
- New app icon: the frostfire gateway (half ice, half lava), installed as a full
  hicolor PNG set (16-512 px) via `tools/make_icon.py`; help popovers on the
  performance toggles.
- Info strip: symmetric 3+3 layout; GPU row shows name, VRAM and driver
  (`nvidia-smi`, with an `lspci`/sysfs fallback for AMD/Intel). Commas and
  parentheses instead of `·`; session name normalised (`Wayland`, `X11`).

### Notes
- Project URLs and packaging point at `epatnor/frostfireinstaller`; the repo is not
  pushed yet, so install from a clone until it is.
- Ported from the verified `bnetstarter` bash prototype (umu-launcher + GE-Proton on Bazzite).

## [0.1.0] - 2026-09-20
- First public scaffold.
