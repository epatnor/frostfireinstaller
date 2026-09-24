# Installing frostfireinstaller

frostfireinstaller drives the host's `umu-launcher` + a Proton build. It is **not**
a Flatpak-only app (yet); the recommended installs are below.

## Requirements

- Linux, Python 3.11+
- [`umu-launcher`](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run`)
- A Proton build (GE-Proton, UMU-Proton or Proton-CachyOS) in a `compatibilitytools.d`
  directory — install one with [ProtonPlus](https://github.com/Vysp3r/ProtonPlus)
- Vulkan-capable GPU drivers

Check everything with:

```bash
frostfireinstaller doctor
```

## Distro support

The tool only needs Python 3.11+ plus the host's `umu-run`/Proton, so the **pipx
and curl channels work everywhere**. Native channels exist where a distro has a
package manager convention.

| Distro | Recommended channel |
|---|---|
| Bazzite / Silverblue / ublue (Fedora atomic) | `ujust` recipe, or Flatpak (experimental) |
| Fedora Workstation, Nobara | pipx / curl |
| Arch, CachyOS, EndeavourOS, Manjaro | AUR |
| Debian, Ubuntu, Mint, Pop!_OS | pipx / curl |
| openSUSE (Tumbleweed/Leap) | pipx / curl |
| Alpine, Void, Gentoo | pipx / curl |
| SteamOS | pipx / curl (or Flatpak) |
| macOS (for reference/testing) | Homebrew |

Immutable/atomic distros that cannot install host `umu-launcher` should use the
Flatpak (once it ships) or install umu via `rpm-ostree`/Homebrew and use pipx.

## Channel 1 — pipx (recommended, universal)

```bash
pipx install frostfireinstaller
# or straight from git:
pipx install git+https://github.com/epatnor/frostfireinstaller
```

## Channel 2 — curl | bash

```bash
curl -fsSL https://raw.githubusercontent.com/epatnor/frostfireinstaller/main/packaging/install.sh | bash
```

## Channel 3 — AUR (Arch family)

```bash
yay -S frostfireinstaller          # or: paru -S frostfireinstaller
```

(Package source: `packaging/aur/PKGBUILD`.)

## Channel 4 — Bazzite (`ujust`)

Once the recipe ships in your image:

```bash
ujust install-frostfireinstaller
```

(Recipe source: `packaging/frostfireinstaller.ujust`.)

## Channel 5 — Homebrew

```bash
brew tap epatnor/frostfireinstaller
brew install frostfireinstaller
```

(Formula source: `packaging/brew/frostfireinstaller.rb`.)

## Channel 6 — Flatpak (experimental)

See `packaging/flatpak/`. A sandboxed app cannot run the host's `umu-run`
directly, so the manifest currently relies on `flatpak-spawn --host`. A future
version will bundle umu + Proton inside the sandbox and ship on Flathub (and thus
appear in Bazaar).

## After install

```bash
frostfireinstaller          # ensure everything and launch Battle.net
frostfireinstaller gui      # graphical interface
frostfireinstaller doctor   # environment + status
```

First run downloads the Battle.net installer (cached at
`~/Games/battlenet/Battle.net-Setup.exe`) and installs it into
`~/Games/battlenet/prefix`. The cached installer is reused on reinstall; use
`--purge-installer` or the *Även installeraren* checkbox to force a fresh download. When the launcher appears, close it once (the tool
does this automatically) and then start it again before logging in.

## Custom prefix location

The prefix lives in `~/Games/battlenet` by default. Override it with an environment
variable or a config entry (the config wins):

```bash
export FROSTFIREINSTALLER_BNET_DIR=/mnt/games/battlenet
```

```toml
# ~/.config/frostfireinstaller/config.toml
[paths]
bnet_dir = "/mnt/games/battlenet"
```

## Updating

```bash
pipx upgrade frostfireinstaller     # or: pipx install --force .
```

`frostfireinstaller` keeps the prefix, games and settings; only the code changes.

## Removing

```bash
frostfireinstaller remove       # remove the client, keep installed games
frostfireinstaller remove --purge
frostfireinstaller remove --purge-installer   # also drop the cached installer
frostfireinstaller uninstall    # remove prefix, desktop entry and icon
```

> The project is not published yet, so the PyPI/curl/AUR/brew commands only work
> once `epatnor/frostfireinstaller` is pushed and released. Until then, install
> from a clone:
>
> ```bash
> git clone https://github.com/epatnor/frostfireinstaller
> cd frostfireinstaller && pipx install .
> ```
>
> The Homebrew tap expects a companion repo named `homebrew-frostfireinstaller`;
> the AUR package must be pushed to the AUR (`packaging/aur/PKGBUILD`).

## Troubleshooting

See [`docs/troubleshooting.md`](troubleshooting.md) for common failures (e.g. the
WoW `ERROR #109` D3D12 freeze, launcher issues, where the logs live).
