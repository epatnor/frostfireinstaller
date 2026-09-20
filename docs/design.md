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

- **En kolumn:** fönstrets menyrad (header bar) → fullbredds-banner → infofält → alla
  funktioner som rader.
- Bannern når kant-till-kant (AspectFrame, inga marginaler).
- **Infofältet** (mörkt, `#00070f`) visar App- och Systemdata i två lika breda kolumner,
  tre rader var:
  - App: Battle.net-status, Proton, Prefix
  - System: Distro + kernel, session + skrivbord, GPU (namn, VRAM, drivrutin)
- GTK4 + libadwaita; mörkt/ljust följer systemet.

## Tillgångar (assets)

- **Banner:** `assets/header/frostfire_installer_header_1.png` (FROSTFIRE Installer-logotyp),
  paketerad i `src/frostfireinstaller/data/header/`.
- **App-ikon:** `assets/icon/frostfireinstaller.png` — porten med is till vänster och
  lava/eld till höger. Härleds till hela hicolor-setet (16–512 px, rundade hörn) med
  `tools/make_icon.py`; paketet skeppar 512 px-versionen
  (`src/frostfireinstaller/data/icons/frostfireinstaller.png`).
- **Äldre koncept:** `assets/icon/legacy-ice-portal.svg` (isporten, ersatt).
- Spelomslag (ej paketerade, för framtida bruk): `assets/covers/`.

## Ikonografi i UI

- **Material Symbols (filled)** — ett litet urval (8 glyfer) inbäddat i
  `data/fonts/MaterialSymbols.ttf` och färgkodat:
  - is `#74d8ff` (bevara/underhåll), eld `#ff7a2f` (förstörande),
    röd `#f66151` (stoppa), grön `#57e389` (starta).
- Övriga ikoner från tema-ikonen (libadwaita), t.ex. `help-about-symbolic`.
- **Hjälp-popovertrar:** varje prestandaväxel har en "?"-knapp som förklarar vad
  verktyget gör och att det gäller spelen (samma Wine-session), inte bara launchern.
