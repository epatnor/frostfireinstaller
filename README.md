# frostylauncher

> Install and launch Blizzard games (focus: **World of Warcraft**) on Linux —
> reliably, reproducibly, and with a nice GUI. Backend: **umu-launcher + Proton**.

**Status:** early development (v0.1, Python port of a verified prototype).

---

## Why

Battle.net on Linux is fiddly. `frostylauncher` aims to be the boring, reliable way to
get Blizzard games running:

- **One command:** ensure everything is set up, then launch.
- **Idempotent:** safe to re-run; only missing pieces are done.
- **Self-healing:** detects a hung/faulty client and recovers.
- **Broad distro support** (Bazzite/Fedora atomic, Arch, Debian/Ubuntu, ...).
- **Per-game profiles** so different titles can use different Proton versions/flags.

It was born from a working recipe on Bazzite: `umu-launcher` + GE-Proton (see `docs/`).

---

## Requirements

- Linux, Python **3.11+**
- [`umu-launcher`](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run`)
- A Proton build (GE-Proton, UMU-Proton or Proton-CachyOS) in a `compatibilitytools.d` dir
- GPU drivers (Vulkan)

## Install

```bash
pipx install frostylauncher          # CLI (once published)
# or from source:
git clone https://github.com/OWNER/frostylauncher
cd frostylauncher
pipx install .
```

## Usage

```bash
frostylauncher              # ensure + launch Battle.net
frostylauncher ensure       # set up/verify only
frostylauncher doctor       # show environment and status
frostylauncher logs         # latest run log
frostylauncher install-logs # latest installation log
frostylauncher kill         # stop all Battle.net processes
frostylauncher uninstall    # remove prefix, shortcut, icon
```

## How it works

`frostylauncher` orchestrates the host's `umu-run` + a Proton build against a dedicated
Wine prefix. It does **not** bundle Wine. See `docs/architecture.md`.

## Supported games

`frostylauncher` supports **everything Battle.net can run under Wine/Proton**. The only titles
that can't work are those whose anti-cheat refuses Linux at the OS level — that is a
**vendor/anti-cheat limitation, not a limitation of this tool**.

| Game | Status |
|---|---|
| World of Warcraft (retail/Forever), Classic | ✅ |
| Diablo II/III/IV, Hearthstone, StarCraft I/II, Heroes of the Storm, Warcraft III Reforged | ✅ |
| Overwatch 2 | ✅ |
| Call of Duty (Battle.net) | ⛔ blocked by kernel-level anti-cheat (Ricochet) — outside our control |

## License

MIT — see [LICENSE](LICENSE).
