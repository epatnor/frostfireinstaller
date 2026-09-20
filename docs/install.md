# Installing frostylauncher

frostylauncher drives the host's `umu-launcher` + a Proton build. It is **not**
a Flatpak-only app (yet); the recommended installs are below.

## Requirements

- Linux, Python 3.11+
- [`umu-launcher`](https://github.com/Open-Wine-Components/umu-launcher) (`umu-run`)
- A Proton build (GE-Proton, UMU-Proton or Proton-CachyOS) in a `compatibilitytools.d`
  directory — install one with [ProtonPlus](https://github.com/Vysp3r/ProtonPlus)
- Vulkan-capable GPU drivers

Check everything with:

```bash
frostylauncher doctor
```

## Channel 1 — pipx (recommended)

```bash
pipx install frostylauncher
# or straight from git:
pipx install git+https://github.com/OWNER/frostylauncher
```

## Channel 2 — curl | bash

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/frostylauncher/main/packaging/install.sh | bash
```

## Channel 3 — Bazzite (`ujust`)

Once the recipe ships in your image:

```bash
ujust install-frostylauncher
```

(Recipe source: `packaging/frostylauncher.ujust`.)

## Channel 4 — Homebrew

```bash
brew tap OWNER/frostylauncher
brew install frostylauncher
```

(Formula source: `packaging/brew/frostylauncher.rb`.)

## Channel 5 — Flatpak (experimental)

See `packaging/flatpak/`. A sandboxed app cannot run the host's `umu-run`
directly, so the manifest currently relies on `flatpak-spawn --host`. A future
version will bundle umu + Proton inside the sandbox and ship on Flathub.

## After install

```bash
frostylauncher          # ensure everything and launch Battle.net
frostylauncher gui      # graphical interface
frostylauncher doctor   # environment + status
```

First run downloads the Battle.net installer and installs it into
`~/Games/battlenet/prefix`. When the launcher appears, close it once (the tool
does this automatically) and then start it again before logging in.
