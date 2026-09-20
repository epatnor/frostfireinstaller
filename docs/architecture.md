# Architecture

`frostylauncher` is a thin, opinionated orchestrator. It does **not** bundle Wine or Proton;
it drives what is already on the host.

## Backend: umu-launcher + Proton

```
frostylauncher
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
  `Battle.net Login`.
- On failure: kill processes, clear `Cache`/`CEF`, fix config, relaunch.

## Paths (XDG)

| Purpose | Path |
|---|---|
| Prefix / game data | `~/Games/battlenet` |
| Config | `~/.config/frostylauncher/config.toml` |
| State | `~/.local/state/frostylauncher` |
| Logs | `~/.local/state/frostylauncher/logs` |
| Shortcut | `~/.local/share/applications/frostylauncher.desktop` |

## Logging

- `run-<ts>.log` — one per invocation (tool activity).
- `install-<ts>.log` — one per installation (system info, installer sha256, full installer
  output, client log tail, result). Meant to be shareable for bug reports.
