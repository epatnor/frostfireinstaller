# Frostfire Installer

> A **Battle.net installer helper** for Linux — stable and compatible, with a
> cool GUI. Backend: **umu-launcher + Proton**.

**Status:** early development (v0.1, Python port of a verified prototype).

---

## Focus

We are **not** building a game launcher or a game library. Games are started from
Blizzard's own Battle.net launcher — `frostfireinstaller` is the helper underneath:

- **Install, verify and repair Battle.net** reliably (dedicated prefix, idempotent).
- **Compatibility**: correct Proton runner and the required environment fixes.
- **Performance**: optional MangoHud, GameMode and Gamescope wrappers that follow the
  games (same Wine session), plus Proton's DXVK/VKD3D/NTSync.
- **Broad distro support** (Bazzite/Fedora atomic, Arch, Debian/Ubuntu, ...).
- **Looks cool**: GTK4/libadwaita UI with a frosty identity — banner, info strip
  (App/System at a glance), a single start/stop bar, and ice/fire themed sections.

Born from a working recipe on Bazzite: `umu-launcher` + GE-Proton (see `docs/`).

---

## GUI

```bash
frostfireinstaller gui
```

- **Infofält**: Battle.net-status, Proton och prefix sida vid sida med distro, kernel,
  session och GPU (namn, VRAM, drivrutin).
- **Startknappen gör allt** (is): startar Battle.net — och installerar klienten om den saknas. Statusrad + Reparera i underhållet.
- **Återställ & ta bort** (eld): Behåll spel, Återinstallera, Ta bort.
- **Loggar**: visa kör- och installationsloggar direkt i appen.
- **Avancerat**: Prestanda (med "?"-förklaring per växel), Runner, Sökvägar, Om.

---

## Requirements

- Linux, Python **3.11+**
- [`umu-launcher`](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run`)
- A Proton build (GE-Proton, UMU-Proton or Proton-CachyOS) in a `compatibilitytools.d` dir
- GPU drivers (Vulkan)
- Optional GUI extras: `python3-gobject` (GTK4 + libadwaita); MangoHud / GameMode /
  Gamescope if you want the performance toggles

## Install

```bash
git clone https://github.com/epatnor/frostfireinstaller
cd frostfireinstaller
pipx install .                           # or: pip install --user .

# once published:
pipx install frostfireinstaller
```

## Usage

```bash
frostfireinstaller              # ensure + launch Battle.net
frostfireinstaller gui          # graphical interface
frostfireinstaller ensure       # set up/verify only
frostfireinstaller doctor       # show environment and status
frostfireinstaller reinstall    # reinstall the client (keeps games)
frostfireinstaller remove       # remove the client (keeps games)
frostfireinstaller logs         # latest run log
frostfireinstaller install-logs # latest installation log
frostfireinstaller kill         # stop all Battle.net processes
frostfireinstaller uninstall    # remove prefix, shortcut, icon
```

## Security

- No secrets are stored or required at runtime.
- No shell: every subprocess call passes an argument list.
- The only download is Blizzard's official installer over HTTPS; size and SHA-256 are
  recorded in the installation log.
- Wine/Proton come from your host — nothing is bundled or patched.
- See `docs/architecture.md` for the full model.

## Documentation

| Document | Contents |
|---|---|
| `docs/architecture.md` | backend, lifecycle, GUI, security, paths |
| `docs/install.md` | install channels, prefix override, update/remove |
| `docs/design.md` | naming, ice/fire concept, assets, iconography |

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

Developer tools (never bundled, never needed at runtime):

```bash
python tools/genassets.py --prompt "..." --out assets/generated/x.png  # concept art
python tools/make_icon.py --src assets/icon/frostfireinstaller.png --install --repo-copy \
    src/frostfireinstaller/data/icons/frostfireinstaller.png
```

## How it works

`frostfireinstaller` orchestrates the host's `umu-run` + a Proton build against a dedicated
Wine prefix. It does **not** bundle Wine. See `docs/architecture.md`.

## Supported games

`frostfireinstaller` supports **everything Battle.net can run under Wine/Proton**. The only titles
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
