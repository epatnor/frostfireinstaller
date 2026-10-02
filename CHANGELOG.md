# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- **Graphics adapts to the hardware.** The GPU list is built from what is
  detected: *Dedicated* only appears when an NVIDIA GPU is present and
  *Integrated* only when an integrated GPU is found, instead of hardcoding the
  vendors.
- **Host summary in Settings -> Runner.** Below the Proton dropdown the card now
  lists CPU (with its advertised, static clock), memory, GPU(s) and disks
  (memory type/speed only when `dmidecode` is readable, i.e. as root). The Runner
  dropdown is a little shorter.
- **Header banner cropped and colour-matched.** The header artwork had a lot of
  near-black dead space above the stars and below the forest. It is now cropped
  to the content plus ~8 px of dark on each side (1216x545 -> 1216x443), and the
  info strip (distro/session/GPU) and the Settings footer row use the banner's
  bottom dark tone (`#00030a`) so they blend.
- **Settings moved into their own resizable window.** The advanced options no
  longer expand the launcher window in place. A *Settings* button under the
  Battle.net band opens a standalone, resizable window with all options grouped
  into fewer **cards** (Battle.net, Performance, Runner, Graphics, Paths,
  Diagnostics & about), each with its header inside the card. On a wide window
  the cards sit in two equal-height columns as a grid; a narrow window falls back
  to a single, natural-height column. The launcher window stays a fixed, compact
  size.
- **Settings are more compact.** Each card keeps a one-line subtitle; the
  per-option explanations are tucked behind round "(i)" buttons. Action buttons
  (Repair, Reinstall, Remove, Open folder, View, Run, About) share the width of
  the widest one with normal padding, and rows are shorter. *Runner* is a
  bordered dropdown, the GPU choice says just *Integrated* (AMD or Intel,
  detected automatically). *Keep games* and *Keep installer* moved to their own
  row at the bottom of the Battle.net card, and *Force fullscreen (gamescope)* is
  a checkbox on the *Gamescope* switch, enabled only while Gamescope is on. When
  a required tool is missing, the row no longer grows a subtitle: the title is
  greyed, the warning moves into the "(i)" popover and the button gets an orange
  border. The window opens tall enough to show every card, capped to the screen.
- **The run button's icons are now the filled Material Symbols variant** (a new
  bundled `MaterialSymbolsFilled.ttf` subset), so the play/stop/install glyphs
  read more clearly on the gradient button. The Settings gear uses it too.

### Added
- **Monochrome tray icon.** The tray now uses a dedicated black-and-white
  gateway glyph (`data/icons/frostfireinstaller-tray.png`, generated from the
  colour icon with the OpenRouter Image API; prototypes under
  `assets/prototypes/`) instead of the colour app icon, so it matches the other
  symbolic panel icons. The launcher/taskbar icon is unchanged. The pixmap is
  supplied at 16/22/24/32/48 px.
- **Tray icon (StatusNotifierItem).** A native KDE/GNOME tray icon is registered
  over D-Bus (no `AppIndicator3` dependency, which cannot coexist with GTK4 in
  one process). Its menu offers *Show Frostfire Installer*, *Start/Stop
  Battle.net* and *Quit*, and it carries the running state in its tooltip.
- **Battle.net running indicator.** While Battle.net is up the header subtitle
  reads *Battle.net running* and the app's dock/taskbar icon carries a badge
  (Unity Launcher API), so it is obvious after a suspend/resume even with both
  windows minimised.

### Fixed
- **Settings window now opens on Wayland.** `_fit_height` called
  `Gdk.Display.get_primary_monitor` and `Gdk.Monitor.get_workarea`, neither of
  which exists on the Wayland display, so clicking *Settings* raised and the
  window never appeared. The monitor is now resolved from the window's surface
  (falling back to the monitor list) and its height from `get_workarea` when
  present, else `get_geometry`.
- **Gamescope switch now warns about NVIDIA on Wayland.** It described itself as
  "can help on Wayland" with no caveat. Nesting gamescope inside a Wayland
  session on the proprietary NVIDIA driver can collapse presentation against the
  outer compositor and strobe the entire display - a photosensitivity hazard,
  reported from a real session on an RTX 4070. When NVIDIA and Wayland are both
  detected the row says so in its subtitle and the help text spells out the risk
  and the way out (Alt+F4, `pkill -f gamescope`). *Force fullscreen* notes that
  it makes the flicker worse.
- **The idle-lock sidecar no longer quits seconds after starting.** It treated
  the first missing wineserver as the end of the session, but relaunching
  Battle.net leaves the old wineserver dying as the new one starts - so the lock
  was released into that gap every time. It now gives up only after three
  consecutive misses, and logs when it starts, when no inhibit tool is found and
  when it fails to spawn, instead of failing silently.
- **`inhibit_idle` no longer releases the lock mid-session.** It wrapped
  `umu-run`, so the lock died with the launcher - and Battle.net is normally
  closed once the game is up, leaving the rest of the play session unprotected.
  The lock is now a detached sidecar that tracks the **wineserver** instead, and
  gives up after two minutes if no Wine session ever appears rather than leaking
  a lock. `--what=idle` also became `--what=idle:sleep`, and `kde-inhibit
  --power --screenSaver` is applied alongside it: KDE's PowerDevil blanks the
  screen off the freedesktop ScreenSaver interfaces and fires straight through a
  logind-only lock. A monitor sleeping mid-game is a common cause of the game
  window returning at the wrong size or on the wrong monitor.

### Added
- **Gamescope wrapper gained the geometry flags**: `-W`/`-H` (fixed virtual
  output), `-O` (pin to one monitor), `--force-grab-cursor` and
  `--force-windows-fullscreen`, plus `--mangoapp` when MangoHud is on. A fixed
  nested output is what keeps DPMS and monitor re-probing from reaching the
  game at all.
- GUI switches for **Force fullscreen (gamescope)** and **Keep awake while
  playing** - both settings previously existed only in `config.toml`, out of
  reach of the users the bugs actually hit.

### Changed
- **App id is now `io.github.epatnor.frostfireinstaller`** (the Flathub
  reverse-DNS form). The desktop entry and icon follow; a legacy
  `io.github.frostfireinstaller` entry/icon is cleaned up on setup.
- Docs: recorded the **WoW: Forever build of 2026-09-24**, whose change log
  (*"Fixed a memory leak causing gradual performance degradation for some
  players"*) resolves the session-long FPS/VRAM drop tracked since 69913. The
  `Xid 109` GPU hang remains fixed in 69977. Updated
  `docs/troubleshooting.md` and `docs/wow-forever-error-history.md` accordingly.

### Added
- README header image (`assets/frostfire_installer_github.png`) and screenshots
  (`assets/screenshots/`), also referenced from the Flatpak metainfo.
- **AI disclosure**: `docs/ai-disclosure.md`, a README badge/notice and a
  CONTRIBUTING note — the project is built with generative AI under human
  supervision (the maintainer reviews, tests and is responsible).
- `docs/support.md` (scope, safety, no warranty), `CODE_OF_CONDUCT.md` and
  `docs/flatpak.md` (Flatpak/Flathub status, blockers and plan).
- **Aspect-adaptive banner**: the window derives the banner height from the header
  image's own aspect ratio (it fills the fixed 608 px width, undistorted) and the
  window height follows. Updated the header image.
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
- **GUI dependencies are now handled by the installer.** A plain `pipx install .`
  created an isolated venv without the system's PyGObject, so
  `frostfireinstaller gui` failed with `ModuleNotFoundError: No module named
  'gi'`. `packaging/install.sh` now installs with
  `pipx install --system-site-packages` (exposing the distro's
  PyGObject/GTK4/libadwaita), falls back to the `[gui]` extra only when the system
  Python has no `gi`, and verifies the toolkit import afterwards with per-distro
  guidance. The pipx docs/README command, the AUR `depends` and the Homebrew
  formula were updated to match.
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
