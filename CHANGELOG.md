# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Initial Python project scaffold: core package, CLI, game profiles, tests, CI.
- `core`: distro/proton detection, umu runner, Battle.net install/launch, health checks.
- Logging: per-run log and per-installation log with full diagnostics.
- Game profiles (JSON) for Battle.net and titles.
- **GUI** (GTK4 + libadwaita, `frostylauncher gui`): sidebar with Library, Install,
  Runners, Logs and Settings; background operations with toasts.
- `service` module shared by the CLI and the GUI.
- App icon (SVG), symbolic icon, and per-game cover art.
- Packaging: `install.sh` (curl | bash), Bazzite `ujust` recipe, Homebrew formula,
  experimental Flatpak manifest + AppStream metadata.
- Docs: `docs/architecture.md`, `docs/install.md`.

### Notes
- Ported from the verified `bnetstarter` bash prototype (umu-launcher + GE-Proton on Bazzite).

## [0.1.0] - 2026-09-20
- First public scaffold.
