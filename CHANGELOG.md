# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

## [0.3.0] - 2026-10-07

### Added
- **Update check and one-click update.** The app checks the GitHub release at
  start and shows a banner when a newer version exists; *Settings → Updates*
  reports the installed and latest versions and installs the release wheel into
  a pipx/venv install in place. `frostfireinstaller update [--check]` does the
  same from the CLI. A package-manager install is only pointed at its own
  updater. Opt out with `FROSTFIREINSTALLER_NO_UPDATE_CHECK=1`.
- **Settings window:** the advanced options moved from an in-place expander into a
  standalone, resizable window of equal-height cards (Battle.net, Performance,
  Runner, Graphics, Paths, Diagnostics & about) — two columns when wide, one when
  narrow. Per-option help sits behind "(i)" buttons; action buttons share one width;
  a missing tool greys the title and moves the warning into the popover.
- **Host summary** in *Settings → Runner*: CPU (advertised clock), memory, GPUs and
  disks (memory type/speed only when `dmidecode` is readable).
- **Tray icon** (StatusNotifierItem over D-Bus, no AppIndicator dependency) with
  *Show*, *Start/Stop Battle.net* and *Quit*, using a monochrome glyph
  (`data/icons/frostfireinstaller-tray.png`).
- **Running indicator:** header subtitle *Battle.net running* and a taskbar badge
  (Unity Launcher API), visible after suspend/resume even with windows minimised.
- **Gamescope geometry flags** (`-W`/`-H`, `-O`, `--force-grab-cursor`,
  `--force-windows-fullscreen`, `--mangoapp` with MangoHud) and GUI switches for
  *Force fullscreen* and *Keep awake while playing* (previously `config.toml` only).
- README header image and screenshots; `docs/support.md`, `docs/ai-disclosure.md`,
  `CODE_OF_CONDUCT.md`.
- **Render-scale check:** warns when a WoW `Config.wtf` stores `RenderScale` above
  100 % (a 138 % value left by a monitor sleep made the game render ~1.9x the
  pixels).

### Changed
- **Graphics** lists *Dedicated* only when an NVIDIA GPU is present and *Integrated*
  only when one is found.
- **Banner** cropped to its content (1216x545 → 1216x443); the info strip and
  Settings row use its bottom tone (`#00030a`).
- The run button and Settings gear use the filled Material Symbols variant.
- **App id** is now `io.github.epatnor.frostfireinstaller` (Flathub form); the old
  desktop entry/icon is cleaned up on setup.
- Docs consolidated: `design.md` merged into `architecture.md`, `flatpak.md` into
  `install.md`, and the WoW error history condensed into `troubleshooting.md`.

- **GUI internals:** `pages.py` split into `widgets`, `actions`, `dialogs` and
  `state`; GPU/Vulkan detection moved from `recommend.py` to `core/gpu.py`.
- **System check reflects what WoW: Forever taught us.** The beta's lag and GPU
  hangs turned out to be client bugs (fixed by build 1.60.1.70170), not Linux or
  Proton. The hybrid-GPU check no longer blames the cross-GPU path, the NVIDIA check
  no longer pushes a driver switch or sysfs/ASPM tweaks, and the `maxFPSBK` tip is
  gone.

### Fixed
- **Startup no longer blocks on the system check.** Host detection and the
  check (`vulkaninfo`, `journalctl`, ...) run in the background, and the check
  runs once instead of twice.
- **Settings follow `config.toml`.** Switches drew the value from when the window
  was built, so after an on-disk change a click re-saved the stale value; every
  control now re-syncs on refresh and when a window regains focus. The config
  band no longer shows the runner from startup after it is changed.
- **Settings window did not open on Wayland** (`get_primary_monitor` and
  `get_workarea` do not exist there); the monitor now comes from the window's surface.
- **Gamescope + NVIDIA + Wayland** can strobe the whole display (photosensitivity
  hazard). The switch now warns and the help explains the way out.
- **Idle lock released mid-session.** It wrapped `umu-run`, so it died with the
  launcher although Battle.net exits once the game is up. It is now a detached
  sidecar tracking the **wineserver**, giving up after two minutes if none appears
  and exiting only after three consecutive misses. `--what=idle:sleep` plus
  `kde-inhibit --power --screenSaver` cover logind and KDE PowerDevil.


### Removed
- The in-app **GPU persistence** toggle (`nvidia-persistenced` via `systemctl`), the
  app's only system change, built for a hang that was a game bug.
- Unused game covers, the legacy ice-portal SVG, `core/profiles.py` with its JSON
  profiles (only printed by `doctor`), and `tools/genassets.py` with `.env.example`.

## [0.1.0] - 2026-09-24

First public release, ported from the verified `bnetstarter` bash prototype
(umu-launcher + GE-Proton on Bazzite).

### Added
- `core`: distro/Proton detection, umu runner, Battle.net install/launch/repair,
  health checks; per-run and per-installation logs.
- **GUI** (GTK4 + libadwaita): fixed 608 px column with banner, info strip, config
  band (Proton, prefix) and Battle.net band (*Running*/*Stopped*/*Not installed*),
  activity strip and toasts. The start button installs a missing client.
- Reinstall/remove with *Keep games* and `--purge-installer` / *Also the installer*;
  *Settings → Paths* shows the cached installer with an *Open folder* button.
- **`[env]` config section** for the Wine session, merged last (e.g.
  `DXVK_FILTER_DEVICE_NAME`).
- **System check:** `core/recommend.py` inspects umu, Proton, free disk, prefix
  filesystem, hybrid GPUs, NVIDIA driver/module and recent `NVRM: Xid`/
  `NV_ERR_NO_MEMORY`, performance tools and the runner. A warning strip appears only
  on problems; the full report is in *Diagnostics* and `doctor`. The one reversible
  mitigation (`nvidia-persistenced`) is an in-app toggle; the app makes no large
  system changes itself.
- MangoHud, GameMode and Gamescope toggles persisted in `config.toml`.
- Packaging: `install.sh`, Bazzite `ujust`, AUR, Homebrew, experimental Flatpak;
  release workflow on `v*` tags (optional PyPI via Trusted Publishing).
- `SECURITY.md`, issue/PR templates, docs set, pytest and CI (ruff/mypy/pytest).

### Changed
- **Renamed to Frostfire Installer** (`frostfireinstaller`): package, CLI, app id,
  paths, desktop entry, icon (the frostfire gateway, hicolor set via `tools/make_icon.py`).
- Scope: a Battle.net installer helper, not a launcher or library.
- **Battle.net-inspired UI:** flat bordered panels, uppercase labels, status pills,
  gradient buttons (blue primary, orange destructive), bundled Open Sans, outlined
  Material Symbols (`tools/make_symbols.py`), in our own frost/fire palette.
- English-only UI, CLI output, logs and docs (previously Swedish).

### Fixed
- **GUI dependencies:** a plain `pipx install .` lacked PyGObject. `install.sh` now
  uses `--system-site-packages`, falls back to the `[gui]` extra, and verifies the
  toolkit import; AUR/Homebrew updated.
- Installer download retries transient failures (5xx/timeouts, 3 attempts).
- Icon install referenced a removed SVG; the packaged PNG is installed instead.
- `Config.save()` dropped hand-written keys and did not escape strings; it now
  merges and escapes.
- The health check treated "no X display" as failure on Wayland and could kill the
  client and wipe its CEF cache; unknown now means "fine".
- `kill_all()` sends SIGTERM before SIGKILL; the Wine user directory is discovered
  instead of assuming `steamuser`.

### Security
- All subprocess calls pass argument lists; `proton.find()` rejects path traversal;
  `.desktop` `Exec` paths are quoted; `FROSTYLAUNCHER_*` env vars renamed to
  `FROSTFIREINSTALLER_*`.

### Notes
- Field result (Bazzite, RTX 3050 Ti Laptop): the WoW: Forever build-69913
  `Xid 109` hang was a client shader bug, not the driver; fixed in build 69977 (see
  `docs/troubleshooting.md`).
