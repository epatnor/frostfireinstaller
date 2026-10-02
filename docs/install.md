# Installing frostfireinstaller

It drives the host's `umu-launcher` + a Proton build; the recommended installs are
below.

## Requirements

- Linux, Python 3.11+
- [`umu-launcher`](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run`)
- A Proton build in a `compatibilitytools.d` directory (e.g. via
  [ProtonPlus](https://github.com/Vysp3r/ProtonPlus)); without one, umu downloads UMU-Proton
- Vulkan-capable GPU drivers
- GUI only: PyGObject + GTK4 + libadwaita for the system Python (`python3-gobject`;
  preinstalled on Fedora/Bazzite). The CLI needs none.

Check everything with `frostfireinstaller doctor`.

## Channels

| Distro | Recommended |
|---|---|
| Bazzite / Silverblue / ublue | `ujust install-frostfireinstaller` |
| Arch, CachyOS, EndeavourOS, Manjaro | AUR: `yay -S frostfireinstaller` |
| Fedora, Nobara, Debian, Ubuntu, Mint, openSUSE, Alpine, Void, Gentoo, SteamOS | pipx / curl |
| macOS (testing only) | Homebrew |

**pipx** (universal):

```bash
pipx install --system-site-packages frostfireinstaller
# or: pipx install --system-site-packages git+https://github.com/epatnor/frostfireinstaller
```

`--system-site-packages` exposes the distro's GTK4/libadwaita to the app. Without
a system `gi`, use `pipx install "frostfireinstaller[gui]"` (pip builds PyGObject).

**curl | bash:**

```bash
curl -fsSL https://raw.githubusercontent.com/epatnor/frostfireinstaller/main/packaging/install.sh | bash
```

**Others:** AUR source `packaging/aur/PKGBUILD`, ujust recipe
`packaging/frostfireinstaller.ujust`, Homebrew `brew tap epatnor/frostfireinstaller &&
brew install frostfireinstaller` (formula `packaging/brew/`; needs a companion repo
`homebrew-frostfireinstaller`).

> **Publication status:** the GitHub repo and release are public. PyPI, AUR and
> Homebrew are **not published yet**; until then install from a clone:
> `git clone https://github.com/epatnor/frostfireinstaller && cd frostfireinstaller && pipx install --system-site-packages .`

### Flatpak (experimental, not built end-to-end yet)

Manifest in `packaging/flatpak/`. Flathub rejects `flatpak-spawn --host`, so it
follows [Faugus Launcher](https://github.com/flathub/io.github.Faugus.faugus-launcher):
`org.winehq.Wine` base (`stable-25.08`) for the 32-bit libraries, the official
umu zipapp as `/app/bin/umu-run`, `--allow=per-app-dev-shm` so pressure-vessel can
nest, and `--filesystem=home` for the prefix and Proton builds. App id
`io.github.epatnor.frostfireinstaller`.

```bash
flatpak-builder --user --install --force-clean build-dir \
  packaging/flatpak/io.github.epatnor.frostfireinstaller.yml
```

Before Flathub: build the manifest, confirm umu + pressure-vessel work nested,
narrow `--filesystem=home`, pass `flatpak-builder-lint`, submit to
`flathub/io.github.epatnor.frostfireinstaller`.

## First run

```bash
frostfireinstaller          # ensure everything and launch Battle.net
frostfireinstaller gui
```

The first run downloads the installer (cached at `~/Games/battlenet/Battle.net-Setup.exe`)
and installs into `~/Games/battlenet/prefix`. The tool closes the first launcher
run itself; start it again before logging in. Use `--purge-installer` or the
*Keep installer* option to force a fresh download.

## Custom prefix location

Environment variable or config (config wins):

```bash
export FROSTFIREINSTALLER_BNET_DIR=/mnt/games/battlenet
```

```toml
# ~/.config/frostfireinstaller/config.toml
[paths]
bnet_dir = "/mnt/games/battlenet"
```

## Updating and removing

```bash
pipx upgrade frostfireinstaller            # from PyPI, once published
pipx uninstall frostfireinstaller && pipx install --system-site-packages .   # from a clone

frostfireinstaller remove                  # client only, keeps games
frostfireinstaller remove --purge-installer
frostfireinstaller uninstall               # prefix, desktop entry and icon
```

Avoid `pipx install --force .`: with `uv` as backend it refuses to overwrite the
existing venv and the reinstall silently does not happen. Updating keeps the
prefix, games and settings. Verify with `frostfireinstaller --version` and `doctor`.

Problems? See [troubleshooting](troubleshooting.md).
