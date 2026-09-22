# Design — Frostfire Installer

## Namn och motiv

- **Visningsnamn:** Frostfire Installer
- **Tekniskt namn:** `frostfireinstaller` (paket, CLI, app-id `io.github.frostfireinstaller`)
- **Motiv:** frost/eld. Isen bevarar, elden förstör.

## Is och eld (UI-koncept)

Åtgärderna är uppdelade i två områden med varsitt tema:

| Område | Tema | Innehåll |
|---|---|---|
| **Installation & underhåll** | **Is** (bevara, hålla igång) | Battle.net-status + Reparera (samma rad) |
| **Återställ & ta bort** | **Eld** (förstörande) | Behåll spel, Återinstallera, Ta bort |

- **Startknappen gör allt**: den kör `ensure()` först — saknas klienten heter den
  *"Installera"* (installerar och startar), annars *"Starta"*/*"Stoppa"*. Ingen
  separat installationsknapp behövs (den var en dublett).
- **Kompakt men logiskt**: val som hör till en åtgärd ligger i samma rad — *Även
  installeraren* är en kryssruta bredvid *Ta bort*, inte en egen rad. Status och
  *Reparera* delar rad.
- **Behåll spel** är is-sidan av de förstörande åtgärderna: elden tar klienten, isen räddar spelen.
- **Framtid:** accentfärger per område är på plats (isblå primärknappar, eld-orange
  destruktiva); kvar att utforska är t.ex. spelkort och fler piller/tabbar.

## Battle.net-inspirerad form

Appen lånar **struktur och formspråk** från Blizzard's Battle.net-launcher (utan
deras logotyper eller bildmaterial), men behåller vårt eget frost/eld-färgschema:

- **Platta paneler** med 1 px ram (`rgba(120,200,255,0.12)`), 4 px radie och tunna
  1 px-avgränsare mellan raderna — i stället för libadwaitas stora rundade kort.
- **Sektionsrubriker** i små, genomgående versaler med spärrad bokstavsbredd.
- **Knappar** med svag vertikal gradient: blå primär (`#1c86e6` → `#0a5fb8` med
  ljusblå tunn ram `#63c2ff`), mörk sekundär, eld-orange destruktiv
  (`#ff8f45` → `#d9591a`), 3 px radie och ~30 px höjd.
- **Status-piller** för tillståndet i run-baren (grön/orange/dämpad).
- **Typsnitt:** inbäddad **Open Sans** (Regular/SemiBold/Bold) som UI-typsnitt,
  samma familj som Battle.net-appen använder.

## Färger

| Roll | Färg |
|---|---|
| Bakgrund | djup marinblå (`#00070f`) |
| Panel / yta | `#07121d` (ram `rgba(120,200,255,0.12)`) |
| Infofält | `#00070f` |
| Konfigurationsband | `#051320` |
| Battle.net-band (run bar) | `#061520` |
| Is / primär | cyan-blå (`#74D8FF`, ljus `#EAF9FF`); primärknapp `#1c86e6` → `#0a5fb8`, ram `#63c2ff` |
| Eld / destruktiv | glödbrand (`#FF7A2F`, knapp `#ff8f45` → `#d9591a`) |
| Text | `#eaf9ff`, dämpad `rgba(234,249,255,0.5)` |

## Layout

- **En kolumn:** fönstrets menyrad (header bar) → fullbredds-banner → infofält →
  konfigurationsband → Battle.net-band → "Visa avancerat"-footer → rullbar yta med
  panelerna (som visas först när footern fälls ut).
- **Fast bredd:** fönstret är **608 px brett och inte användar-resizbart** (samma
  som bannern, så den fyller bredden).
- **Fast bannerstorlek:** bannern skalas vid laddning till **608×198 px** (20 %
  mindre än full bredd) och ritas fast, centrerad — den ändrar sig aldrig. Vid
  toggle ändras bara fönstrets höjd (350 ↔ 770) och appen växer nedåt.
- **Infofältet** (mörkt, `#00070f`) är en rad systeminfo: distro + kernel, session,
  GPU (namn, drivrutin).
- **Konfigurationsbandet** (`#051320`, smalt) visar Proton och prefix — hur appen är
  uppsatt — så att bandet nedanför bara behöver bära tillstånd. Saknad Proton visas i
  eld-orange (`#ff7a2f`).
- **Battle.net-bandet** (`#061520`) bär tillståndet (piller) och åtgärdsknappen.
- **Aktivitetsrad** under bandet visar pågående operation (spinner + text) medan
  nedladdning/installation/körning sker.
- **"Visa avancerat"-footern** (chevron ned/upp) fäller ut allt annat i en rullbar
  yta; **Installation & underhåll** och **Återställ & ta bort** döljs dessutom när
  klienten inte är installerad (run-baren erbjuder då *Installera*).
- GTK4 + libadwaita; appen använder en fast mörk palett (följer inte systemtema).

## Tillgångar (assets)

- **Banner:** `assets/header/frostfire_installer_header_no_installer.png` (FROSTFIRE-
  ordmärket utan underrubrik); `tools/make_header.py` bakar in raden "Battle.net
  installer" och skriver `src/frostfireinstaller/data/header/frostfire_installer_header.png`.
- **App-ikon:** `assets/icon/frostfireinstaller.png` — porten med is till vänster och
  lava/eld till höger. Härleds till hela hicolor-setet (16–512 px, rundade hörn) med
  `tools/make_icon.py`; paketet skeppar 512 px-versionen
  (`src/frostfireinstaller/data/icons/frostfireinstaller.png`).
- **Äldre koncept:** `assets/icon/legacy-ice-portal.svg` (isporten, ersatt).
- Spelomslag (ej paketerade, för framtida bruk): `assets/covers/`.

## Ikonografi i UI

- **Material Symbols (outlined, light)** — ett litet urval (9 glyfer) inbäddat i
  `data/fonts/MaterialSymbols.ttf`. Subseten byggs med `tools/make_symbols.py`
  (FILL 0, wght 200, GRAD 0, opsz 24) och färgkodas:
  - is `#74d8ff` (bevara/underhåll), eld `#ff7a2f` (förstörande),
    röd `#f66151` (stoppa), grön `#57e389` (starta).
- Övriga ikoner från tema-ikonen (libadwaita), t.ex. `help-about-symbolic`.
- **Hjälp-popovertrar:** varje prestandaväxel har en "?"-knapp som förklarar vad
  verktyget gör och att det gäller spelen (samma Wine-session), inte bara launchern.
