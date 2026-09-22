# Architecture

`frostfireinstaller` is a thin, opinionated orchestrator. It does **not** bundle Wine or Proton;
it drives what is already on the host.

## Backend: umu-launcher + Proton

```
frostfireinstaller
  └─ umu-run  (host binary, package `umu-launcher`)
       └─ Proton build (GE-Proton / UMU-Proton / Proton-CachyOS)
            └─ Wine prefix  (~/Games/battlenet/prefix)
                 └─ Battle.net.exe  →  your games
```

Environment applied to the launcher:

| Variable | Value | Why |
|---|---|---|
| `WINE_SIMULATE_WRITECOPY` | `1` | avoids CEF blank UI + Agent init stall |
| `WINEDLLOVERRIDES` | `locationapi=d` | avoids blank CEF login |
| `WINEPREFIX` | `~/Games/battlenet/prefix` | dedicated prefix |
| `GAMEID` | `umu-battlenet` | umu identity |
| `PROTONPATH` | detected Proton build | the runner |

Extra variables can be added under `[env]` in `config.toml`; they are merged last
and win over the defaults (useful for driver workarounds, e.g.
`DXVK_FILTER_DEVICE_NAME`). See `docs/troubleshooting.md`.

## Why not Bottles/Soda or Lutris

- **Bottles + Soda**: the launcher's CEF UI does not render (black window / spinning gear,
  `tassadar Login URL is empty`). The runner is the differentiator, not the settings.
- **Lutris + GE-Proton**: worked, but adds a heavy layer and the author hit friction.
- **umu + Proton**: Valve's modern non-Steam path, present on Bazzite, best performance.

## Lifecycle

1. **Detect** host (distro/atomic/session/GPU) and Proton builds.
2. **Ensure** prefix, installer, Battle.net, config, shortcut (all idempotent).
3. **Install** (first time): run the installer, wait for a reliable readiness signal, then
   auto-close the first run.
4. **Launch** and **health-check**: wait for a UI window; if none, remediate and retry.

### Reliable readiness signal

The launcher writes `drive_c/users/*/AppData/Local/Battle.net/Logs/battle.net-*.log`.
The client is considered ready when the log contains `*** LOAD COMPLETE ***` or resolves
the login URL (`login.app?app=app`). This is used to auto-close the first run instead of
asking the user to do it manually.

### Health / self-healing

- `ui_window_present()` checks the X window tree (`xwininfo`) for `Battle.net` /
  `Battle.net Login`. On a pure Wayland session there is no usable X tree, so the
  check reports "fine" rather than risking a false positive.
- `kill_all()` sends `SIGTERM` first and only then `SIGKILL` (lets Wine flush state).
- On failure: kill processes, clear `Cache`/`CEF`, fix config, relaunch.

## GUI

GTK4 + libadwaita (`frostfireinstaller gui`), one column:

1. **Banner** — full-bleed header art.
2. **Info strip** — one line of system info (distro + kernel, session, GPU).
3. **Config band** — narrow band with the runner (Proton) and prefix, i.e. how the app
   is set up; a missing Proton is highlighted.
4. **Battle.net band** — client state (coloured) plus the install/start/stop button.
   The button runs `ensure()` first, so a missing client is installed ("Installera")
   before launching.
5. **Activity strip** — a spinner + text showing the operation running right now
   (searching for Proton, downloading, installing, starting, removing).
6. **Recommendation strip** — appears **only for warnings** from
   `core/recommend.py` (NVIDIA `NVRM: Xid` / `NV_ERR_NO_MEMORY` GPU faults,
   missing `umu-run`/Proton, low disk, NTFS/exFAT prefix, missing performance
   tools). It opens a dialog with copy-ready fix commands and one **reversible
   in-app toggle** (`nvidia-persistenced` via `systemctl`, Polkit-prompted). The
   full report — every check including the passing ones — is under **Avancerat →
   Diagnostik → Systemkontroll** and in `doctor`. The app never makes large
   system changes.
7. **Advanced footer expander** — right under the Battle.net band; "Visa
   avancerat" (chevron-down/up) reveals, in a scroll area below, "Installation &
   underhåll", "Återställ & ta bort", Prestanda / Runner / Sökvägar (with *Visa
   loggar*) / Om. The window is a fixed **608 px wide** (not user-resizable) with
   a banner scaled to 608 × 198; only its height changes (350 ↔ 770) on toggle,
   so the banner never resizes.

Long-running work runs in worker threads: the activity strip shows the current step,
and toasts report the result.

### Performance wrappers

| Option | Effect |
|---|---|
| MangoHud | sets `MANGOHUD=1` (overlay/diagnostics) |
| GameMode | wraps the command in `gamemode` (system tuning while running) |
| Gamescope | wraps the command in `gamescope -f --` (nested compositor, FSR, FPS cap) |

Because Battle.net and the games it starts share one Wine session, these settings
follow into the games — not just the launcher. Toggles whose tool is missing are
disabled in the UI.

## Security and robustness

- **No secrets at rest.** The tool needs none; `tools/genassets.py` (image generation)
  is developer-only and reads `OPENAI_API_KEY` from the environment or a gitignored
  `.env`/key file.
- **No shell.** Every subprocess call passes an argument list (`shell=False`).
- **No string injection into TOML.** `Config.save()` escapes values and merges with the
  existing file, so hand-written keys and sections survive.
- **Path guards.** `proton.find()` accepts plain directory names only.
- **Quoted `.desktop` Exec** when paths contain spaces.
- **Network:** the only download is Battle.net's official installer over HTTPS
  (`www.battle.net`); its size and SHA-256 are recorded in the installation log.
  Wine/Proton components come from the host, not from us.

## Paths (XDG)

| Purpose | Path |
|---|---|
| Prefix / game data | `~/Games/battlenet` (override: `FROSTFIREINSTALLER_BNET_DIR`, or `[paths] bnet_dir`) |
| Cached installer | `~/Games/battlenet/Battle.net-Setup.exe` (reused; delete with `--purge-installer`) |
| Config | `~/.config/frostfireinstaller/config.toml` |
| State | `~/.local/state/frostfireinstaller` |
| Logs | `~/.local/state/frostfireinstaller/logs` |
| Desktop entry | `~/.local/share/applications/io.github.frostfireinstaller.desktop` |
| Icon | `~/.local/share/icons/hicolor/512x512/apps/io.github.frostfireinstaller.png` |

## Logging

- `run-<ts>.log` — one per invocation (tool activity).
- `install-<ts>.log` — one per installation (system info, installer sha256, full installer
  output, client log tail, result). Meant to be shareable for bug reports.

## Troubleshooting

Common failures and their fixes (e.g. the WoW `ERROR #109` D3D12/VKD3D freeze, the
launcher CEF fixes, where the logs live) are collected in
[`docs/troubleshooting.md`](troubleshooting.md).
