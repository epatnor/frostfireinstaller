# frostylauncher

> A stable, compatible way to install **Battle.net** (and run Blizzard games,
> focus: **World of Warcraft**) on Linux — with a cool GUI. Backend:
> **umu-launcher + Proton**.

**Status:** early development (v0.1, Python port of a verified prototype).

---

## Focus

We are **not** building a game launcher. Games are launched from Blizzard's own
Battle.net launcher — `frostylauncher` is the platform underneath:

- **Install & maintain Battle.net** reliably (dedicated prefix, idempotent setup).
- **Compatibility**: correct Proton runner, required env fixes, per-title notes.
- **Performance**: optional MangoHud, GameMode and Gamescope wrappers, plus
  Proton's DXVK/VKD3D/NTSync.
- **Broad distro support** (Bazzite/Fedora atomic, Arch, Debian/Ubuntu, ...).
- **Looks cool**: GTK4/libadwaita UI with a frosty identity.

Born from a working recipe on Bazzite: `umu-launcher` + GE-Proton (see `docs/`).

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
