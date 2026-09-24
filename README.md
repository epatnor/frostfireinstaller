# Frostfire Installer

> A **Battle.net installer helper** for Linux — stable and compatible, with a
> cool GUI. Backend: **umu-launcher + Proton**.

[![CI](https://github.com/epatnor/frostfireinstaller/actions/workflows/ci.yml/badge.svg)](https://github.com/epatnor/frostfireinstaller/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

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
- **Looks cool:** a Battle.net-inspired GTK4/libadwaita UI with our own frost/fire
  palette — dark flat panels, uppercase section labels and gradient buttons. The
  window is a compact, fixed 608 px wide; everything except the run controls sits
  behind a "Visa avancerat" footer expander.

Born from a working recipe on Bazzite: `umu-launcher` + GE-Proton (see `docs/`).

---

## GUI

```bash
frostfireinstaller gui
```

- **Banner** (fast höjd) → **infofält** (distro + kernel, session, GPU) →
  **konfigurationsband** (Proton och prefix) → **Battle.net-bandet**.
- **Battle.net-bandet**: status-piller och åtgärdsknappen (*Installera* / *Starta* /
  *Stoppa*). Startknappen kör `ensure()` först, så en saknad klient installeras.
- **Aktivitetsrad**: spinner + text som visar pågående operation.
- **Systemkontroll & rekommendationer**: appen kontrollerar `umu-run`, Proton,
  diskutrymme, prefixens filsystem, hybrid-GPU, NVIDIA-drivrutin/modul och senaste
  `NVRM: Xid`/`NV_ERR_NO_MEMORY`, saknade prestandaverktyg och runner. En
  **varningsrad** (under bandet) visas bara vid problem och öppnar en dialog med
  **färdiga kommandon att kopiera**; hela rapporten (inkl. OK) ligger under
  **Avancerat → Diagnostik → Systemkontroll** och i `doctor`. Den **reversibla**
  åtgärden (GPU-persistens) kan slås på/av direkt i appen — appen gör aldrig
  stora systemändringar själv.
- **"Visa avancerat"** (footer med chevron) fäller ut allt annat:
  - **Installation & underhåll** (is): status + *Reparera* i samma rad.
  - **Återställ & ta bort** (eld): *Behåll spel*, *Återinstallera*, *Ta bort* (med
    kryssrutan **Även installeraren**).
  - **Prestanda** (med "?"-förklaring per växel), **Runner**, **Sökvägar**
    (inkl. *Öppna mapp* och **Visa loggar**) och **Om**.

Fönstret är **608 px brett och inte resizbart**; vid expandering växer det bara nedåt.

---

## Requirements

- Linux, Python **3.11+**
- [`umu-launcher`](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run`)
- A Proton build (GE-Proton, UMU-Proton or Proton-CachyOS) in a `compatibilitytools.d` dir
- GPU drivers (Vulkan)
- Optional GUI extras: `python3-gobject` (GTK4 + libadwaita); MangoHud / GameMode /
  Gamescope if you want the performance toggles

## Install

Any distro with **Python 3.11+** works via `pipx`; there are also native
channels. Full matrix in [`docs/install.md`](docs/install.md).

| Channel | Command | For |
|---|---|---|
| pipx (universal) | `pipx install frostfireinstaller` | any distro |
| curl \| bash | `curl -fsSL .../packaging/install.sh \| bash` | any distro |
| AUR | `yay -S frostfireinstaller` | Arch, CachyOS, EndeavourOS, Manjaro |
| Bazzite / ublue | `ujust install-frostfireinstaller` | Fedora atomic images |
| Homebrew | `brew install epatnor/frostfireinstaller/frostfireinstaller` | Linux & macOS |
| Flatpak | *(experimental, Flathub pending)* | immutable desktops |

Not published yet — until the first release, install from a clone:

```bash
git clone https://github.com/epatnor/frostfireinstaller
cd frostfireinstaller
pipx install .                           # or: pip install --user .
```

## Usage

```bash
frostfireinstaller              # ensure + launch Battle.net
frostfireinstaller gui          # graphical interface
frostfireinstaller ensure       # set up/verify only
frostfireinstaller doctor       # show environment and status
frostfireinstaller reinstall    # reinstall the client (keeps games)
frostfireinstaller remove       # remove the client (keeps games)
frostfireinstaller remove --purge-installer   # ...and the cached installer
frostfireinstaller logs         # latest run log
frostfireinstaller install-logs # latest installation log
frostfireinstaller kill         # stop all Battle.net processes
frostfireinstaller uninstall    # remove prefix, shortcut, icon
```

## Reliability

- Idempotent setup: `ensure` verifies prefix, installer, client, config and
  shortcut every run.
- The installer **retries** transient download failures (5xx/timeouts).
- **Reparera** stops a wedged client, clears CEF/cache and relaunches.
- Reinstall/remove **keep your games** unless you ask otherwise.
- Games run in Blizzard's own launcher; if a game itself misbehaves (e.g. a
  D3D12 freeze), see `docs/troubleshooting.md`.

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
| `docs/troubleshooting.md` | common failures and fixes (D3D12 freeze, launcher, logs) |
| `docs/wow-forever-error-history.md` | observed WoW: Forever (69913) error history and Xid correlation |
| `docs/technical-reference.md` | deep-dive: Wine/Proton/Steam/umu stack, Battle.net + WoW: Forever specs, env reference |

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
python tools/make_header.py                     # bake the banner subtitle
python tools/make_symbols.py                    # rebuild the Material Symbols subset
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
