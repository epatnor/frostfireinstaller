# Design — Frostfire Installer

## Namn och motiv

- **Visningsnamn:** Frostfire Installer
- **Tekniskt namn:** `frostfireinstaller` (paket, CLI, app-id `io.github.frostfireinstaller`)
- **Motiv:** frost/eld. Isen bevarar, elden förstör.

## Is och eld (UI-koncept)

Åtgärderna är uppdelade i två områden med varsitt tema:

| Område | Tema | Innehåll |
|---|---|---|
| **Installation & underhåll** | **Is** (bevara, hålla igång) | Installera/verifiera, Starta, Reparera, Stoppa |
| **Återställ & ta bort** | **Eld** (förstörande) | Behåll spel, Återinstallera, Ta bort |

- **Behåll spel** är is-sidan av de förstörande åtgärderna: elden tar klienten, isen räddar spelen.
- **Framtid:** accentfärger per område — isblå för underhåll, glödbrand/orange för förstörande
  knappar; ev. tematiska sektionsrubriker och ikoner.

## Färger

| Roll | Färg |
|---|---|
| Bakgrund | djup marinblå (`#0A2540` → `#081B33`) |
| Is / primär | cyan-blå (`#74D8FF`, ljus `#EAF9FF`) |
| Eld / destruktiv | glödbrand (`#FF7A2F`) |
| Text | libadwaitas standard (följer tema) |

## Layout

- **En kolumn:** fönstrets menyrad (header bar) → fullbredds-banner → alla funktioner som rader.
- Bannern når kant-till-kant (AspectFrame, inga marginaler).
- GTK4 + libadwaita; mörkt/ljust följer systemet.

## Tillgångar (assets)

- **Banner:** `assets/header/frostfire_installer_header_1.png` (FROSTFIRE Installer-logotyp),
  paketerad i `src/frostfireinstaller/data/header/`.
- **App-ikon:** `assets/icon/frostfireinstaller.svg` (isig port + snöflinga).
- **Symbolisk ikon:** `assets/icons/frostfireinstaller-symbolic.svg`.
- Spelomslag (ej paketerade, för framtida bruk): `assets/covers/`.

## Ikonografi i UI

- Standard-symboliska ikoner från tema-ikonen (libadwaita), t.ex. `go-home-symbolic`,
  `folder-download-symbolic`, `preferences-system-symbolic`.
- Egen symbolisk snöflinga för varumärket.
