# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- **App id is now `io.github.epatnor.frostfireinstaller`** (the Flathub
  reverse-DNS form). The desktop entry and icon follow; a legacy
  `io.github.frostfireinstaller` entry/icon is cleaned up on setup.

### Added
- README header image (`assets/frostfire_installer_github.png`) and screenshots
  (`assets/screenshots/`), also referenced from the Flatpak metainfo.
- **AI disclosure**: `docs/ai-disclosure.md`, a README badge/notice and a
  CONTRIBUTING note — the project is built with generative AI under human
  supervision (the maintainer reviews, tests and is responsible).
- `docs/support.md` (scope, safety, no warranty), `CODE_OF_CONDUCT.md` and
  `docs/flatpak.md` (Flatpak/Flathub status, blockers and plan).
- **Vulkan capability check**: `core/recommend.py` warns when Vulkan is missing,
  older than 1.3, software-only (llvmpipe), or when the **32-bit Vulkan loader**
  is absent — the prerequisites Battle.net (32-bit) and the games need.
- **Proton auto-download**: when no local Proton build is found, `umu-launcher`
  downloads **UMU-Proton** on first launch; the Runner list offers the umu
  codenames and the messages explain the fallback. Clearer guidance when even
  `umu-run` is missing.
- Flatpak: renamed to the new app id, metainfo gains `<developer>`/`<releases>`
  and screenshots; the manifest now runs **umu inside the sandbox** (bundled
  umu-launcher + `org.winehq.Wine` base + `--allow=per-app-dev-shm`) instead of
  the `flatpak-spawn --host` escape — the pattern Flathub accepts.

## [0.1.0] - 2026-09-24

### Added
- `core`: distro/proton detection, umu runner, Battle.net install/launch/repair, health checks.
- Logging: per-run and per-installation logs with full diagnostics.
- **GUI** (GTK4 + libadwaita, `frostfireinstaller gui`): a compact, fixed-width
  single column with the Frostfire banner, system/config strips and the Battle.net
  band; everything else sits behind the *Show advanced* footer. Background
  operations show an activity strip and toasts.
- **Activity strip** under the run bar: a spinner + label showing the current operation
  (searching for Proton, downloading the installer, installing, starting, removing).
- Reinstall / remove Battle.net with a **"Keep games"** (keep games) option.
- **`[env]` config section**: extra environment for the Wine session (umu-run →
  Battle.net → games), merged last so it overrides the defaults — handy for
  driver workarounds such as `DXVK_FILTER_DEVICE_NAME` (see
  `docs/troubleshooting.md`).
- **System check & recommendations**: `core/recommend.py` inspects what it can see
  locally — `umu-run`, Proton builds, free disk space, the prefix filesystem
  (NTFS/exFAT warning), hybrid-GPU setups, the NVIDIA driver/module type and any
  recent `NVRM: Xid` / `NV_ERR_NO_MEMORY` faults, enabled-but-missing performance
  tools, and the runner. A strip under the Battle.net band appears **only for
  warnings** and opens a dialog with copy-ready commands; the full report
  (including OK checks) is under **Advanced → Diagnostics → System check** and
  in `frostfireinstaller doctor`. The one **reversible** mitigation
  (`nvidia-persistenced`) is an in-app toggle (Polkit-prompted); the app never
  makes large system changes itself.
- Performance toggles: MangoHud, GameMode, Gamescope (persisted in `config.toml`).
- Packaging: `install.sh` (curl | bash), Bazzite `ujust` recipe, AUR `PKGBUILD`,
  Homebrew formula, experimental Flatpak manifest + AppStream metadata.
- **Release workflow** (`.github/workflows/release.yml`): on a `v*` tag, builds the
  sdist/wheel, verifies the wheel installs, and creates a GitHub release; optional
  PyPI publish via Trusted Publishing (repo variable `PUBLISH_PYPI=true`).
- Project hygiene: `SECURITY.md`, issue templates and a pull-request template.
- Docs: `docs/architecture.md`, `docs/install.md`, `docs/design.md`,
  `docs/troubleshooting.md`, `docs/technical-reference.md`,
  `docs/wow-forever-error-history.md`; `docs/install.md` now has a distro support
  matrix.
- Tests (pytest) and CI (ruff / mypy / pytest).

- **Also the installer** checkbox in the *Remove* row and `--purge-installer` (CLI):
  drop the cached `Battle.net-Setup.exe` so the download path can be re-tested.
- Advanced → Paths shows where the installer is cached and whether it is present;
  the row updates live after actions and has an **Open folder** button so removal can
  be verified.
- GUI: client status and *Repair* share one row; logs moved under Advanced
  (a *View* button on the Logs row).
- New narrow **config band** (`#051320`) with Proton and prefix, so the run bar
  carries state only and configuration is always visible; a missing Proton is
  highlighted.
- Run bar status now has three states: *Running* / *Stopped* / *Not installed*.
- **Battle.net band**: state, Proton and prefix moved from the info strip into the
  run bar (dimmed second line); the info strip is now a single line of system info.

### Fixed
- **Installer download** now retries transient failures (5xx/timeouts, up to 3
  attempts) instead of failing on a single "bad gateway".
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
  ("Install"); the maintenance row is status-only (plus Repair).
- GUI actions split into "Installation & maintenance" (ice) and "Reset & remove" (fire).
- Icon install now includes the hicolor `index.theme` so the app icon resolves.
- New app icon: the frostfire gateway (half ice, half lava), installed as a full
  hicolor PNG set (16-512 px) via `tools/make_icon.py`; help popovers on the
  performance toggles.
- Info strip: one line of system info (distro + kernel, session, GPU name and
  driver). Commas and parentheses instead of `·`; session name normalised
  (`Wayland`, `X11`).
- **Battle.net-inspired UI**: flat bordered panels with 1px row separators, 4px
  corner radii, uppercase section labels, status pills and gradient buttons
  (blue primary, orange destructive) — using our own frost/fire palette. The
  bundled **Open Sans** is now the app font; `Adw.PreferencesPage`/`Group` were
  replaced by custom `Section` panels.
- **Compact layout**: everything except the run controls is hidden behind an
  **Advanced footer expander** right under the Battle.net band ("Show advanced"
  with a chevron-down/up). The window is a fixed **608 px wide** (not
  user-resizable) with a banner scaled down 20 % (608 × 198, fixed size); only
  its height changes (350 ↔ 770) when toggled, so the banner never resizes.
- *Installation & maintenance* and *Reset & remove* are hidden while no client
  is installed (the run bar already offers *Install*); the "Is/Eld" section
  descriptions were removed.
- **English-only**: all UI strings, CLI/`doctor` output, log messages, comments
  and documentation are now in English (the app was Swedish-only).
- UI icons are now **outlined and light** (Material Symbols FILL 0, weight 200)
  instead of solid; the subset is rebuilt with `tools/make_symbols.py`.
- Internal: renamed the `FrostyApplication` class to `FrostfireApplication`.

### Removed
- `PLAN.md` (superseded by the `docs/` set) and the stale
  `assets/icons/frostylauncher-symbolic.svg`.
- Unused bundled fonts **Doto** and **Silkscreen** (dropped banner-font experiment)
  and the unused `gui.helpers.make_icon()` helper (it referenced the removed SVG).

### Notes
- First public release. Project URLs and packaging point at
  `epatnor/frostfireinstaller`; the GitHub repo and `v0.1.0` release are public
  (PyPI/AUR/Homebrew not yet).
- Ported from the verified `bnetstarter` bash prototype (umu-launcher + GE-Proton on Bazzite).
- **Field result (Bazzite, RTX 3050 Ti Laptop):** the WoW: Forever build-69913
  `Xid 109` GPU hang was a **client shader bug** (unbounded GI-probe compute
  shader), not the driver — the proprietary NVIDIA driver did not stop it. It is
  **fixed in build 69977** (verified 2026-09-24, zero `Xid` on NVIDIA). Recorded
  in `docs/wow-forever-error-history.md` and `docs/troubleshooting.md`.
