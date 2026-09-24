# Flatpak / Flathub (experimental)

Frostfire Installer is primarily distributed as a normal host app (pipx, AUR,
Homebrew, the Bazzite `ujust` recipe). A **Flatpak** is planned for immutable
desktops and for **Flathub** (and therefore **Bazaar**, which lists Flathub apps).

The current manifest lives in `packaging/flatpak/`. It is **experimental** and
**not yet Flathub-ready**.

## Why it is not on Flathub yet

1. **Sandbox escape.** A Flatpak cannot run the host's `umu-run` directly. The
   current manifest works around this with `flatpak-spawn --host` and
   `--talk-name=org.freedesktop.Flatpak`. Flathub does **not** accept that escape
   hatch.
2. **Bundling.** The right long-term design (what Bottles does) is to bundle
   `umu-launcher`, a Proton runtime and the Steam Linux Runtime pieces **inside**
   the sandbox, so no host binaries are needed.
3. **Offline build.** Flathub builds without network access. The manifest must
   vendor the build backend (hatchling) and use the runtime's PyGObject instead
   of fetching from PyPI.
4. **AppStream.** The metainfo needs at least one `<screenshots>` entry; the
   `<developer>` and `<releases>` elements are already present.

## Plan

- [ ] Bundle `umu-launcher` + a Proton build + the runtime inside the sandbox.
- [ ] Replace `flatpak-spawn --host` with the bundled runner; drop
      `--talk-name=org.freedesktop.Flatpak`.
- [ ] Make the build offline (vendor hatchling; PyGObject from the runtime).
- [ ] Add screenshots to `io.github.epatnor.frostfireinstaller.metainfo.xml`.
- [ ] Validate with `flatpak-builder-lint` and `appstreamcli validate`.
- [ ] Submit a PR to `flathub/io.github.epatnor.frostfireinstaller`.

## App id

The Flatpak uses `io.github.epatnor.frostfireinstaller` (the Flathub reverse-DNS
form `io.github.<user>.<app>`). This matches the app id used for the desktop
entry and icon on all channels.

## Local test build (host `umu-run`, experimental only)

```bash
flatpak-builder --user --install --force-clean build-dir \
  packaging/flatpak/io.github.epatnor.frostfireinstaller.yml
flatpak run io.github.epatnor.frostfireinstaller
```

This requires `umu-run` and a Proton build on the **host**, and the
`org.freedesktop.Flatpak` talk permission.
