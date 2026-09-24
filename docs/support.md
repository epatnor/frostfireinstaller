# Support and scope

Frostfire Installer is a small open-source helper, provided **as is**, without
warranty (see [LICENSE](../LICENSE)). You are free to use it, and the maintainer
offers **best-effort** support through GitHub issues — there is no guarantee of a
fix, a response time, or that it works on every system.

This page sets expectations so that "does it work?" has a clear answer.

## What this project is

A helper that installs, verifies and repairs **Battle.net** and launches it
through the host's `umu-launcher` + a Proton build. It keeps its own Wine prefix,
applies the known compatibility fixes, and reports what it can see locally.

## What this project is not

- **Not a game launcher or library.** Games are started from Blizzard's own
  Battle.net launcher.
- **Not a Wine/Proton/driver.** Those come from your host; this app orchestrates
  them.
- **Not affiliated with Blizzard.** It does not modify game files and does not
  bundle Blizzard software.

## In scope (we try to fix)

- Installing/repairing/removing Battle.net and its prefix.
- The launcher not starting, blank CEF windows, the known `WINE_SIMULATE_WRITECOPY`
  / `locationapi` fixes.
- Our own install, packaging, CLI and GUI behaviour.

## Out of scope (report upstream)

- **Bugs inside a game** (crashes, GPU hangs, freezes, anti-cheat). These are
  Wine/Proton/driver/vendor issues. See `docs/troubleshooting.md` for known cases.
- **Anti-cheat that refuses Linux at the kernel level** (e.g. Call of Duty's
  Ricochet). This cannot work under Wine and is outside our control.
- **GPU driver bugs** (e.g. NVIDIA `Xid`), distribution packaging of Wine/Proton,
  or Blizzard account/server issues.

## Safety commitments

- The app **never makes large, irreversible system changes on its own**. The one
  system-level action (GPU persistence, `nvidia-persistenced`) is opt-in,
  reversible, and password-prompted.
- **No telemetry, no secrets, no accounts.** Nothing is sent anywhere except the
  download of Blizzard's official installer over HTTPS.
- Every subprocess call passes an argument list (no shell).
- The prefix lives in a normal directory (`~/Games/battlenet` by default) and is
  yours to inspect, move or delete.

## Reporting a problem

Open an [issue](https://github.com/epatnor/frostfireinstaller/issues/new/choose)
and include the **`frostfireinstaller doctor`** output and, if relevant, the logs
from `~/.local/state/frostfireinstaller/logs`. Security issues go through
[SECURITY.md](../SECURITY.md).

## No warranty

To the extent permitted by law, the authors and contributors are **not liable**
for any damage or data loss arising from use of the software. The MIT license
governs. If that matters to you, read it — it is short.
