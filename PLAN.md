# frostylauncher — projektplan

Arbetsnamn: **frostylauncher** (ihopskrivet). Kan ändras senare.
Ett installationsverktyg **och** en launcher för Blizzards spel på Linux — man "launchar sitt äventyr".

> Detta dokument samlar vision, beslut och vägen framåt. Prototypen i denna mapp (`bnetstarter`, bash)
> är den verifierade grunden; nästa steg är en seriös Python-app.

---

## 1. Namn

- **frostylauncher** — vänligt, tydligt, "frost" blinkar mot Blizzard, "launcher" mot att starta sitt äventyr.
- Tillgänglighet: **PyPI `frosty-launcher` ledigt**, **GitHub `frostylauncher` ledigt**.
- "Frosty" är i sig ett vanligt ord (Wendy's, Frosty the Snowman, **Frosty Mod Manager** för EA/Frostbite).
  Därför är namnet lätt att ta men svårt att varumärkesskydda — vi kan byta senare.
- Ej valda (men kollade): frostgate (belamrat), frostforge (WoW-privatserver), rimeforge (spelstudio),
  frosthollow/frostrunner/frostrealm/frostkeep (GitHub tagna), cryogate (dimmaskin), glacihold (helt fritt),
  frostlaunch (snöbollskastare).

---

## 2. Vision

- Ett **seriöst open source-verktyg** för att installera och köra Blizzards spel på Linux, med **fokus på World of Warcraft**.
- **Bred distrokompatibilitet** (Bazzite/Fedora atomic, Arch, Debian/Ubuntu, ...).
- **Snyggt GUI** + kraftfull CLI, delad kärna.
- Ska klara **alla Blizzards spel** så långt tekniken tillåter (per-spel-profiler).
- Lätt att installera (GitHub, Flatpak/Bazaar på sikt).

---

## 3. Teknikval

| Del | Val | Motivering |
|---|---|---|
| Backend | **umu-launcher + Proton** (GE-Proton/UMU-Proton/Proton-CachyOS) | Valves moderna körväg, bäst prestanda, ingen mellanhand. Verifierat fungerande. |
| Språk | **Python** (≥3.10) | Paketering, testbarhet, JSON-config, GUI, Flatpak. |
| GUI | **GTK4 + libadwaita** (rekommendation) alt. Qt6/Kirigami | Polerat, adaptivt, PyGObject finns i GNOME-runtime → smidig Flatpak. |
| CLI | `typer`/`argparse` | Entry point `frostylauncher`. |
| Kärna | Ren Python, GUI-oberoende | Testbar, återanvändbar. |

**Arkitektur (förslag):**
```
frostylauncher/
  core/     # distro, proton-detektering, prefix, game-profiler, loggning, health
  cli.py    # kommandon
  gui/      # GTK4-vyer
  data/     # game-profiler (JSON), ikoner
```

**Paketering:** `pyproject.toml` (PEP 621) + `[project.scripts]` → PyPI/pipx, Flatpak, AUR, brew.

---

## 4. Funktioner (målbild)

- Idempotent **install + start** i samma verktyg (ärvd från prototypen).
- **Per-spel-profiler**: Proton-version, env-vars, launch-args, noteringar (t.ex. `-d3d11`).
- **Loggning**: körningslogg + dedikerad installationslogg (systeminfo, sha256, installer-output, klientlogg).
- **Doctor + självläkning**: upptäck hängd/felaktig klient, rensa CEF/cache, starta om.
- **Genvägar** (`.desktop`) och ev. Steam-genväg.
- **GUI**: bibliotek, installera/uppdatera, runner-hantering, loggvisare, inställningar, doctor.

---

## 5. Blizzard-spel — vad som går

`frostylauncher` stödjer **allt som Battle.net kan köra under Wine/Proton**. Enda undantagen är spel
vars anti-cheat vägrar Linux på OS-nivå — det är en **tillverkarens/anti-cheatens begränsning, inte vår**.

**Fungerar (via Battle.net i prefix):** WoW (retail/Forever), WoW Classic, Diablo II/III/IV, Hearthstone,
StarCraft I/II, Heroes of the Storm, Warcraft III Reforged, **Overwatch 2** (user-space Warden).

**Går inte på Linux (oavsett verktyg):** **Call of Duty (Battle.net)** — kernel-level anti-cheat
(Ricochet). Verktyget ska förklara det tydligt så användaren inte tror att det är ett fel hos oss.

Enskilda titlar kan vilja ha specifik Proton-version/flaggor → hanteras via per-spel-profiler.

---

## 6. Paketering & distribution

| Kanal | Fas | Kommentar |
|---|---|---|
| GitHub + `curl \| bash` | 1 | Enklast, funkar överallt |
| **ujust-recept** (Bazzite) | 1 | Mest native på Bazzite; kräver merge i ublue |
| Homebrew (Bazzite har brew) | 1 | Användarnivå, ingen root |
| PyPI / pipx | 1–2 | `pipx install frostylauncher` |
| AUR | 2 | Arch |
| **Flatpak → Flathub → Bazaar** | 3 | Kräver bundlad umu+Proton i sandboxen |

**Flatpak-utmaningen:** kärnvärdet är att orkestrera **hostens** umu/Proton. En Flatpak kan inte köra
host-binärer rakt av. Alternativ: (1) bundla umu+Proton (som Bottles), (2) `flatpak-spawn --host`
(skört, granskas hårt), (3) egen Wine i sandboxen (tappar poängen). Därför fas 3.

---

## 7. Roadmap

**v0.1 – Python-kärna + CLI** (port av prototypen)
- [ ] `pyproject.toml`, paketstruktur, entry point
- [ ] core: distro/proton/prefix/profiler/loggning/health
- [ ] CLI-kommandon (`run`, `ensure`, `doctor`, `logs`, `kill`, `uninstall`)
- [ ] tester (`pytest` + `bats`/integration), CI (`ruff`, `mypy`, `pytest`)

**v0.2 – GUI (GTK4/libadwaita)**
- [ ] bibliotek + installera/starta
- [ ] runner-väljare, loggvisare, doctor
- [ ] tray/notiser (undersök dubbel-ikon-problemet)

**v0.3 – Per-spel & robusthet**
- [ ] game-profiler (WoW Forever, Overwatch, Diablo ...)
- [ ] självläkning, felkatalog
- [ ] bredare distrotest

**v0.4 – Distribution**
- [ ] `install.sh`, ujust-recept, Homebrew-formel, PyPI-release
- [ ] (fas 3) Flatpak med bundlad backend → Flathub/Bazaar

**v1.0**
- [ ] stabilt API, dokumentation, bidragsguide, licens

---

## 8. Verifierat recept (prototypens grund)

```
umu-run
  WINEPREFIX=~/Games/battlenet/prefix
  GAMEID=umu-battlenet
  PROTONPATH=<GE-Proton11-7-x86_64>
  WINE_SIMULATE_WRITECOPY=1
  WINEDLLOVERRIDES="locationapi=d"
  'C:\Program Files (x86)\Battle.net\Battle.net.exe'
```

- Soda (Bottles) **fungerade inte** (svart/kugghjul, `tassadar Login URL is empty`).
- Klarsignal för installation: klientloggen visar `*** LOAD COMPLETE ***` eller sätter login-URL.
- Stäng första körningen före inloggning (automatiseras av verktyget).

---

## 9. Beslut kvar att ta

1. **Projektmapp:** `~/Projects/frostylauncher`? (nuvarande prototyp ligger i `~/Skrivbord/bnetstarter`)
2. **GUI-verktyg:** GTK4/libadwaita (rekommendation) eller Qt6/Kirigami?
3. **Licens:** MIT eller GPL-3?
4. **Flatpak-timing:** fas 3 (rekommendation) eller tidigare?
5. **Bakåtkompatibilitet:** behåll `bnetstarter`-CLI:t som alias?

---

## 10. Status

- [x] Verifierat fungerande Battle.net på Bazzite (umu + GE-Proton)
- [x] Fungerande bash-prototyp (`bnetstarter`) med idempotent install/start, loggning, genväg, självläkning
- [x] Python-omskrivning (kärna + CLI + tester + CI)
- [x] GUI (GTK4/libadwaita): Bibliotek, Installera, Runners, Loggar, Inställningar
- [x] App-ikon + spelomslag (SVG + genererade covers)
- [x] Paketering: `install.sh`, `ujust`, Homebrew, Flatpak-manifest (experimentellt)
- [ ] Skarp testrunda + Flathub-screenshots
- [ ] Flatpak med bundlad umu+Proton → Flathub/Bazaar
