# Flatpak / Flathub

Frostfire Installer is primarily distributed as a normal host app (pipx, AUR,
Homebrew, the Bazzite `ujust` recipe). A **Flatpak** is planned for immutable
desktops and for **Flathub** (and therefore **Bazaar**, which lists Flathub apps).

The manifest lives in `packaging/flatpak/`. It is **experimental** — it follows a
proven Flathub pattern but has not been built end-to-end yet.

## Design

The earlier draft used `flatpak-spawn --host` to reach the host's `umu-run`.
Flathub does **not** accept that sandbox escape. Instead the manifest now mirrors
[`io.github.Faugus.faugus-launcher`](https://github.com/flathub/io.github.Faugus.faugus-launcher),
which runs UMU-Launcher **inside** the sandbox:

- **Base `org.winehq.Wine`** (`stable-25.08`) — provides a Wine/Proton-compatible
  environment and the 32-bit libraries Battle.net needs, layered on
  `org.gnome.Platform`.
- **umu-launcher is bundled** — the official `umu-launcher-<ver>-zipapp.tar` is
  installed as `/app/bin/umu-run`, so `shutil.which("umu-run")` finds it.
- **`--allow=per-app-dev-shm`** — lets pressure-vessel (umu's container) run
  nested inside the Flatpak sandbox.
- **`--filesystem=home`** — exposes the Wine prefix (`~/Games/battlenet`) and
  Steam's `compatibilitytools.d` so Proton builds can be found. umu downloads
  Proton and the Steam Linux Runtime on first use.
- **No `--talk-name=org.freedesktop.Flatpak`**, no `flatpak-spawn`.

The app itself needs no special Flatpak branch: the prefix, config and state paths
already use `$HOME`/`$XDG_*`, and `umu-run` is found on `PATH`.

## Build

```bash
flatpak-builder --user --install --force-clean build-dir \
  packaging/flatpak/io.github.epatnor.frostfireinstaller.yml
flatpak run io.github.epatnor.frostfireinstaller
```

Requires `flatpak-builder` (or the `org.flatpak.Builder` app) and the
`org.gnome.Platform//50` runtime plus the `org.winehq.Wine` base.

## Remaining work before Flathub

- [ ] Build the manifest end-to-end and fix whatever breaks.
- [ ] Confirm umu + pressure-vessel work nested (install Battle.net from the
      Flatpak, launch a game).
- [ ] Tighten `--filesystem=home` to the narrow paths actually needed, if
      possible.
- [ ] Validate with `flatpak-builder-lint`.
- [ ] Submit a PR to `flathub/io.github.epatnor.frostfireinstaller`.

## App id

The Flatpak uses `io.github.epatnor.frostfireinstaller` (the Flathub reverse-DNS
form `io.github.<user>.<app>`), matching the desktop entry and icon on all
channels.

## References

- Faugus Launcher (UMU inside Flatpak, on Flathub):
  https://github.com/flathub/io.github.Faugus.faugus-launcher
- Flathub requirements: https://docs.flathub.org/docs/for-app-authors/requirements
- AppStream metadata: https://www.freedesktop.org/software/appstream/docs/
