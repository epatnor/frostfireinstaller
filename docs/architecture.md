# Architecture

`frostfireinstaller` is a thin, opinionated orchestrator. It does **not** bundle
Wine or Proton; it drives what is already on the host.

```
frostfireinstaller
  └─ umu-run  (host binary, package `umu-launcher`)
       └─ Proton build (GE-Proton / UMU-Proton / Proton-CachyOS)
            └─ Wine prefix  (~/Games/battlenet/prefix)
                 └─ Battle.net.exe  →  your games
```

Environment applied to the launcher (children inherit it):

| Variable | Value | Why |
|---|---|---|
| `WINE_SIMULATE_WRITECOPY` | `1` | avoids CEF blank UI + Agent init stall |
| `WINEDLLOVERRIDES` | `locationapi=d` | avoids blank CEF login |
| `WINEPREFIX` | `~/Games/battlenet/prefix` | dedicated prefix |
| `GAMEID` | `umu-battlenet` | umu identity |
| `PROTONPATH` | detected build | the runner |

Extra variables go under `[env]` in `config.toml`; they are merged last and win
(e.g. `DXVK_FILTER_DEVICE_NAME` to pick a GPU).

**Why not Bottles/Soda or Lutris?** Bottles + Soda: the CEF UI does not render
(black window, `tassadar Login URL is empty`) — the runner is the differentiator.
Lutris + GE-Proton works but adds a heavy layer. umu + Proton is Valve's modern
non-Steam path and performs best.

## Lifecycle

1. **Detect** host (distro, atomic, session, GPU) and Proton builds.
2. **Ensure** prefix, installer, Battle.net, config, shortcut (all idempotent).
3. **Install** (first time): run the installer, wait for readiness, auto-close the
   first run. Ready = the client log (`drive_c/users/*/AppData/Local/Battle.net/Logs/battle.net-*.log`)
   contains `*** LOAD COMPLETE ***` or resolves the login URL (`login.app?app=app`).
   The GUI's start animation follows the *new* log of each launch more strictly:
   *Starting* until it appears, *Loading* until it logs `Attempting to show main
   window` (~10 s after the process starts), then *Running*.
4. **Launch** and **health-check**: wait for a UI window (`xwininfo`; on pure
   Wayland there is no X tree, so the check reports "fine"); on failure kill
   (SIGTERM, then SIGKILL), clear `Cache`/`CEF`, relaunch.

## GUI

GTK4 + libadwaita, fixed dark palette (CSS in `gui/application.py`). The launcher
is one column, **608 px wide and not resizable**:

1. **Banner** — full width, height from the image's aspect ratio.
2. **Info strip** — distro + kernel, session, GPU.
3. **Config band** — Proton and prefix; a missing Proton is shown in fire-orange.
4. **Battle.net band** — status pill and one action button. It runs `ensure()`
   first, so a missing client reads *Install*, otherwise *Start*/*Stop*.
5. **Activity strip** — spinner + the operation in progress.
6. **Warning strip** — only when `core/recommend.py` finds a problem; opens a
   dialog with copy-ready commands (the app never changes the system itself).
   The full report is under
   *Settings → Diagnostics → System check* and in `doctor`.
7. **Settings footer** — opens a separate, resizable window of equal-height cards
   (Battle.net, Performance, Runner, Graphics, Paths, Diagnostics & about) in a
   two-column grid that collapses to one column when narrow. Per-option help sits
   behind "(i)" buttons. Reset/remove rows are hidden until the client is installed.

While Battle.net runs, the header subtitle, a taskbar badge (Unity Launcher API)
and a tray icon (StatusNotifierItem, spoken over D-Bus directly because GTK4
cannot load the GTK3 indicator bindings) show it. Long-running work — including
host detection and the system check at startup — runs in worker threads and
reports through the activity strip and toasts.

**State:** `gui/state.ClientState` (config, installed, running) is read once per
refresh — after every action and whenever a window gains focus — and handed to
every widget in both windows, so values changed in `config.toml` show up without
a restart. Code layout: `pages.py` (main column), `settings.py`, `widgets.py`,
`actions.py` (background actions), `dialogs.py`, `window.py` (the refresh hub),
`tray.py`.

**Look:** Battle.net-inspired structure (flat panels with 1 px borders, uppercase
section labels, gradient buttons, bundled Open Sans), our own frost/fire palette —
ice-blue for preserving/maintaining, ember-orange for destructive actions. *Keep
games* is the ice side of *Reinstall*/*Remove*. Icons are a small Material Symbols
subset (`data/fonts/`, rebuilt by `tools/make_symbols.py`).

**Assets:** banner source `assets/header/frostfire_installer_header_no_installer.png`
→ `tools/make_header.py` bakes the subtitle into
`data/header/frostfire_installer_header.png`. App icon `assets/icon/frostfireinstaller.png`
→ `tools/make_icon.py` (hicolor set; the package ships 512 px). The tray uses a
monochrome glyph, `data/icons/frostfireinstaller-tray.png`.

### Performance wrappers

| Option | Effect |
|---|---|
| MangoHud | `MANGOHUD=1` (via `--mangoapp` under gamescope) |
| GameMode | wraps the command in `gamemode` |
| Gamescope | `gamescope -f --` plus `-W`/`-H`, `-O`, `--force-grab-cursor`, `--force-windows-fullscreen` |
| Keep awake | idle/suspend lock for the session (`inhibit_idle`) |

Battle.net and its games share one Wine session, so these follow into the games.
Toggles whose tool is missing are disabled.

> **Gamescope is not a safe default.** On NVIDIA + Wayland, nesting it can strobe
> the whole display (photosensitivity hazard, observed with an RTX 4070 on KDE Wayland).
> `settings.gamescope_is_risky()` detects the combination and the switch warns in place.
> See [troubleshooting](troubleshooting.md).

**The idle lock is a sidecar, not a wrapper.** A wrapper's lock dies with the
launcher, but Battle.net exits once the game is up — which let the monitor sleep
mid-game. `_spawn_inhibitor()` instead starts a detached process that tracks the
prefix's **wineserver**: it waits up to two minutes for one to appear, and exits
only after **three consecutive misses** (relaunching Battle.net leaves the old
wineserver dying as the new one starts). `launch_command()` stays a plain argv
list. `systemd-inhibit --what=idle:sleep` and `kde-inhibit --power --screenSaver`
are both applied when present — KDE's PowerDevil fires through a logind-only lock.

## Security and robustness

- **No secrets, no telemetry.** Nothing is sent anywhere except the download of
  Battle.net's official installer over HTTPS (`www.battle.net`); size and SHA-256
  are recorded in the installation log. Wine/Proton come from the host.
- **No shell.** Every subprocess call passes an argument list.
- **No string injection into TOML.** `Config.save()` escapes values and merges with
  the existing file, so hand-written keys and sections survive.
- **Path guards.** `proton.find()` accepts plain directory names only; `.desktop`
  `Exec` is quoted when paths contain spaces.

## Paths (XDG)

| Purpose | Path |
|---|---|
| Prefix / game data | `~/Games/battlenet` (override: `FROSTFIREINSTALLER_BNET_DIR` or `[paths] bnet_dir`) |
| Cached installer | `~/Games/battlenet/Battle.net-Setup.exe` |
| Config | `~/.config/frostfireinstaller/config.toml` |
| Logs | `~/.local/state/frostfireinstaller/logs` — `run-<ts>.log` per invocation, `install-<ts>.log` per installation (shareable in bug reports) |
| Desktop entry | `~/.local/share/applications/io.github.epatnor.frostfireinstaller.desktop` |
| Icon | `~/.local/share/icons/hicolor/512x512/apps/io.github.epatnor.frostfireinstaller.png` |
