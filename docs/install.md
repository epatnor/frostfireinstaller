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

## Channel 1 — pipx (recommended)

```bash
pipx install frostfireinstaller
# or straight from git:
pipx install git+https://github.com/OWNER/frostfireinstaller
```

## Channel 2 — curl | bash

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/frostfireinstaller/main/packaging/install.sh | bash
```

## Channel 3 — Bazzite (`ujust`)

Once the recipe ships in your image:

```bash
ujust install-frostfireinstaller
```

(Recipe source: `packaging/frostfireinstaller.ujust`.)

## Channel 4 — Homebrew

```bash
brew tap OWNER/frostfireinstaller
brew install frostfireinstaller
```

(Formula source: `packaging/brew/frostfireinstaller.rb`.)

## Channel 5 — Flatpak (experimental)

See `packaging/flatpak/`. A sandboxed app cannot run the host's `umu-run`
directly, so the manifest currently relies on `flatpak-spawn --host`. A future
version will bundle umu + Proton inside the sandbox and ship on Flathub.

## After install

```bash
frostfireinstaller          # ensure everything and launch Battle.net
frostfireinstaller gui      # graphical interface
frostfireinstaller doctor   # environment + status
```

First run downloads the Battle.net installer and installs it into
`~/Games/battlenet/prefix`. When the launcher appears, close it once (the tool
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
frostfireinstaller uninstall    # remove prefix, desktop entry and icon
```

> The `OWNER/frostfireinstaller` URLs above are placeholders until the project is
> published; until then install from a local clone (`pipx install .`).
