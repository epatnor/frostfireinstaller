# Design — Frostfire Installer

## Name and motif

- **Display name:** Frostfire Installer
- **Technical name:** `frostfireinstaller` (package, CLI, app id `io.github.epatnor.frostfireinstaller`)
- **Motif:** frost/fire. Ice preserves, fire destroys.

## Ice and fire (UI concept)

The actions are split into two areas, each with its own theme:

| Area | Theme | Contents |
|---|---|---|
| **Installation & maintenance** | **Ice** (preserve, keep running) | Battle.net status + Repair (same row) |
| **Reset & remove** | **Fire** (destructive) | Keep games, Reinstall, Remove |

- **The start button does everything**: it runs `ensure()` first — if the client is
  missing it says *"Install"* (installs and starts), otherwise *"Start"*/*"Stop"*.
  No separate install button is needed (it was a duplicate).
- **Compact but logical**: options that belong to an action live on the same row —
  *Also the installer* is a checkbox next to *Remove*, not a row of its own. Status
  and *Repair* share a row.
- **Keep games** is the ice side of the destructive actions: fire takes the client,
  ice saves the games.
- **Future:** per-area accent colours are in place (ice-blue primary buttons,
  fire-orange destructive); still to explore are e.g. game cards and more
  pills/tabs.

## Battle.net-inspired form

The app borrows **structure and visual language** from Blizzard's Battle.net
launcher (without their logos or artwork), but keeps our own frost/fire palette:

- **Flat panels** with a 1 px border (`rgba(120,200,255,0.12)`), 4 px radius and
  thin 1 px separators between rows — instead of libadwaita's large rounded cards.
- **Section headings** in small, consistently uppercase type with letter spacing.
- **Buttons** with a subtle vertical gradient: blue primary (`#1c86e6` → `#0a5fb8`
  with a light-blue thin border `#63c2ff`), dark secondary, fire-orange destructive
  (`#ff8f45` → `#d9591a`), 3 px radius and ~30 px height.
- **Status pills** for the run-bar state (green/orange/dimmed).
- **Typeface:** bundled **Open Sans** (Regular/SemiBold/Bold) as the UI font, the
  same family the Battle.net app uses.

## Colours

| Role | Colour |
|---|---|
| Background | deep navy (`#00070f`) |
| Panel / surface | `#07121d` (border `rgba(120,200,255,0.12)`) |
| Info strip | `#00070f` |
| Config band | `#051320` |
| Battle.net band (run bar) | `#061520` |
| Ice / primary | cyan-blue (`#74D8FF`, light `#EAF9FF`); primary button `#1c86e6` → `#0a5fb8`, border `#63c2ff` |
| Fire / destructive | ember (`#FF7A2F`, button `#ff8f45` → `#d9591a`) |
| Text | `#eaf9ff`, dimmed `rgba(234,249,255,0.5)` |

## Layout

- **One column:** the window header bar → full-width banner → info strip → config
  band → Battle.net band → "Show advanced" footer → scrollable area with the panels
  (shown only when the footer is expanded).
- **Fixed width:** the window is **608 px wide and not user-resizable** (the same as
  the banner, so it fills the width).
- **Adaptive banner:** the banner fills the fixed 608 px width; its height is
  derived from the image's aspect ratio at load, so any header renders without
  distortion. On toggle only the window height changes and the app grows
  downwards.
- **The info strip** (dark, `#00070f`) is one line of system info: distro + kernel,
  session, GPU (name, driver).
- **The config band** (`#051320`, narrow) shows Proton and prefix — how the app is
  configured — so the band below only has to carry state. A missing Proton is shown
  in fire-orange (`#ff7a2f`).
- **The Battle.net band** (`#061520`) carries the state (pill) and the action button.
- **Activity strip** below the band shows the operation in progress (spinner + text)
  while downloading/installing/running.
- **The "Show advanced" footer** (chevron down/up) expands everything else in a
  scrollable area; **Installation & maintenance** and **Reset & remove** are also
  hidden when the client is not installed (the run bar then offers *Install*).
- GTK4 + libadwaita; the app uses a fixed dark palette (does not follow the system
  theme).

## Assets

- **Banner:** `assets/header/frostfire_installer_header_no_installer.png` (the
  FROSTFIRE wordmark without a subtitle); `tools/make_header.py` bakes in the line
  "Battle.net installer" and writes
  `src/frostfireinstaller/data/header/frostfire_installer_header.png`.
- **App icon:** `assets/icon/frostfireinstaller.png` — the gateway with ice on the
  left and lava/fire on the right. Derived into the full hicolor set (16–512 px,
  rounded corners) with `tools/make_icon.py`; the package ships the 512 px version
  (`src/frostfireinstaller/data/icons/frostfireinstaller.png`).
- **Older concept:** `assets/icon/legacy-ice-portal.svg` (the ice portal, replaced).
- Game covers (not packaged, for future use): `assets/covers/`.

## UI iconography

- **Material Symbols (outlined, light)** — a small selection (9 glyphs) bundled in
  `data/fonts/MaterialSymbols.ttf`. The subset is built with `tools/make_symbols.py`
  (FILL 0, wght 200, GRAD 0, opsz 24) and colour-coded:
  - ice `#74d8ff` (preserve/maintain), fire `#ff7a2f` (destructive),
    red `#f66151` (stop), green `#57e389` (start).
- Other icons come from the theme icon set (libadwaita), e.g. `help-about-symbolic`.
- **Help popovers:** every performance toggle has a "?" button that explains what
  the tool does and that it applies to the games (same Wine session), not just the
  launcher.
