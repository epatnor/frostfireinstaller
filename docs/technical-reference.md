# Technical Reference — Running Windows Games on Linux

**Focus:** the Wine/Proton/Steam compatibility stack, Blizzard Battle.net under
Wine, and **World of Warcraft: Forever** specifically.

| Field | Value |
|---|---|
| Document | Technical reference / deep-dive |
| Compiled | 2026-09-22 |
| Scope | Windows→Linux game translation; Battle.net + WoW Forever; the `frostfireinstaller` backend |
| Status | Literature + local-environment reference. Not a step-by-step runbook. |

> **How to read this.** Prose and tables describe *how the stack works.* Items
> marked **[verified]** were confirmed on the local machine; items marked
> **[community]** are community-sourced and may change between builds; items
> marked **[uncertain]** are explicitly unconfirmed. A confidence legend and a
> source list are at the end.

---

## 1. Executive summary

1. **Wine is not an emulator.** It reimplements the Win32/NT API as native Unix
   libraries. There is no CPU emulation; performance is near-native when the
   graphics path is translated to Vulkan.
2. **Proton = Wine + patches + DXVK + vkd3d-proton + FAudio + dxvk-nvapi + a
   container runtime.** It is Valve's distribution of that stack for Steam.
3. **umu-launcher** reproduces Steam's runtime + `pressure-vessel` container
   *outside* Steam, so non-Steam launchers (our `frostfireinstaller`, Lutris,
   Heroic, Bottles) can run Proton games the same way Steam does.
4. **Graphics translation** is the decisive factor: D3D9/10/11 → **DXVK** →
   Vulkan; D3D12 → **vkd3d-proton** → Vulkan. Both require a Vulkan-capable
   driver (RADV/ANV/NVIDIA).
5. **Battle.net's launcher is a Chromium (CEF) app**, and its failures on Linux
   are almost always CEF/render-path issues, fixed by
   `WINE_SIMULATE_WRITECOPY=1` and `WINEDLLOVERRIDES=locationapi=d`.
6. **World of Warcraft: Forever** is (per community sources) an official Blizzard
   "Classic+" product on the modern Mainline client, version line **1.60.x**,
   beta builds **1.60.1.69913** (2026-09-17) and **1.60.1.69977** (2026-09-22,
   which fixes the `Xid 109` hang), launching **2026-11-04**. It is a D3D12 client,
   so on Linux it needs the same DXVK/vkd3d-proton stack as retail WoW. Blizzard
   does **not** support Linux.
7. **Anti-cheat decides support.** Blizzard's **Warden is user-space** → works
   under Wine. **Call of Duty's Ricochet is kernel-level** → cannot work under
   Wine.
8. **This machine** (Bazzite Kinoite 44, Wayland/KDE, RTX 3050 Ti + AMD Cezanne
   iGPU, umu 1.4.4, GE-Proton11-7 / UMU-Proton-10.0-4) is a verified-working
   Battle.net configuration; it now plays WoW: Forever on the NVIDIA GPU with no
   `Xid` after build **69977**. The iGPU (`DXVK_FILTER_DEVICE_NAME`) remains a
   useful fallback for `Xid 109` GPU hangs in general.

---

## 2. The stack, end to end

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │ Game .exe  (e.g. Battle.net.exe → Wow.exe / WowB.exe)                 │
 │   Win32 API + Direct3D calls                                          │
 └───────────────┬──────────────────────────────────────────────────────┘
                 │
 ┌───────────────▼──────────────────────────────────────────────────────┐
 │ Wine  (ntdll, kernel32, user32, dxgi, ... + wineserver)               │
 │   • WINEPREFIX: the fake C:\ and registry                             │
 │   • wine-mono (NET), wine-gecko (MSHTML), DLL overrides               │
 │   • D3D8/9/10/11 ──► DXVK         D3D12 ──► vkd3d-proton (native DLLs)│
 │   • XAudio2 ──► FAudio       NVAPI/DLSS ──► dxvk-nvapi               │
 └───────────────┬──────────────────────────────────────────────────────┘
                 │ Vulkan API
 ┌───────────────▼──────────────────────────────────────────────────────┐
 │ Vulkan loader  →  ICD: RADV (AMD) / ANV (Intel) / NVIDIA / lavapipe  │
 │   optional layers: MangoHud, vkBasalt, Gamescope                      │
 └───────────────┬──────────────────────────────────────────────────────┘
                 │ DRM/KMS
 ┌───────────────▼──────────────────────────────────────────────────────┐
 │ amdgpu / i915 / xe / nvidia  →  GPU                                   │
 └──────────────────────────────────────────────────────────────────────┘

 Wrapped by pressure-vessel + bwrap (Steam Linux Runtime: Soldier/Sniper/RT4)
 Driven by Steam (_v2-entry-point, compatibilitytools.d/)  or
           umu-launcher (umu-run, GAMEID, PROTONPATH) for non-Steam clients.
```

The **wineserver session boundary is the prefix**: a launcher and every game it
spawns share one `WINEPREFIX`, one wineserver, and therefore one environment.
This is why launcher-level fixes (write-copy, DLL overrides) reach the games.

---

## 3. Wine

### 3.1 What it is

Wine ("Wine Is Not an Emulator") reimplements the Win32 API and the NT kernel
syscall surface as native Unix shared objects (`ntdll.so`, `kernel32.dll`,
`user32.dll`, `d3d11.dll`, …) plus a supervisor process, **`wineserver`**, that
owns the per-prefix object namespace. Windows calls map onto POSIX calls
(`open`, `mmap`, `futex`, …). It is **not** CPU emulation and **not** a sandbox:
drive `Z:` maps to `/`, so Wine processes have the user's full filesystem rights.

### 3.2 The prefix (`WINEPREFIX`)

A prefix is a self-contained fake Windows install (default `~/.wine`). Layout:

```
$WINEPREFIX/
├── drive_c/
│   ├── windows/system32/        # 64-bit system DLLs
│   ├── windows/syswow64/        # 32-bit system DLLs (WoW64 prefix)
│   ├── Program Files/
│   └── users/<user>/            # user profile, AppData, game logs
├── dosdevices/                  # c: -> ../drive_c, z: -> /
├── system.reg                   # HKLM
├── user.reg                     # HKCU
└── .update-timestamp            # prefix version marker
```

Prefixes are not forward-compatible: newer Wine upgrades an old prefix and older
Wine may then refuse it. Create/maintain with
`WINEPREFIX=~/.prefix wineboot -u`.

### 3.3 Tooling

| Tool | Role |
|---|---|
| `winecfg` | Windows version, drives, DLL overrides, graphics/audio drivers |
| `regedit` / `wine reg` | Registry editing |
| `winetricks` | "Primitive package manager" — verbs install components (`corefonts`, `vcrun2015`, `dxvk`, …) |
| `protontricks` | winetricks for Steam/Proton prefixes |

### 3.4 DLL overrides (`WINEDLLOVERRIDES`)

Overrides select native vs builtin DLLs and live in
`HKCU\Software\Wine\DllOverrides`. Per-invocation form:

```sh
WINEDLLOVERRIDES="d3d11,d3d10core,dxgi,d3d9=n,b"   # native(DXVK) then builtin
WINEDLLOVERRIDES="locationapi=d"                   # disable locationapi entirely
```

`n` = native, `b` = builtin, `d` = disabled; order matters. DXVK's manual
install requires native overrides for `d3d8/d3d9/d3d10core/d3d11/dxgi`.

### 3.5 wine-mono and wine-gecko

- **wine-mono** substitutes .NET Framework (≤ 4.8.1) via Wine's builtin
  `mscoree.dll`. Remove it before installing a real .NET Framework.
- **wine-gecko** supplies MSHTML/Trident for embedded browser controls. Wine
  auto-downloads both if missing; distros ship them under `/usr/share/wine/`.

`WINEDLLPATH` prepends directories to Wine's DLL search path.

---

## 4. Proton

**Proton** runs Windows-exclusive Steam games on Linux. It is Wine plus a large
component set, vendored as submodules:

- Valve's **Wine** fork (game patches) + **wine-staging** patches in GE builds
- **DXVK** (D3D9/10/11 → Vulkan) and **vkd3d-proton** (D3D12 → Vulkan)
- **dxvk-nvapi** (NVAPI/NVML/DLSS/Reflex)
- **FAudio** (XAudio2), **ffmpeg**, **gstreamer**, media foundation
- **fonts**, **GameMode**, **OpenXR-SDK**, **lsteamclient** (Steam API shim), **FEX** (ARM)

### 4.1 Steam integration — `compatibilitytools.d`

A locally installed tool lives at:

```
~/.steam/root/compatibilitytools.d/<toolname>/
├── compatibilitytool.vdf
├── toolmanifest.vdf
├── proton
├── version
└── user_settings.sample.py
```

Register by placing it there and restarting Steam. Force a build per game via
**Properties → Compatibility → Force the use of a specific Steam Play
compatibility tool**. `user_settings.py` applies overrides inside the tool dir.

### 4.2 Build variants

| Variant | What it is | Who maintains |
|---|---|---|
| **Valve Proton** | Official, shipped by Steam | Valve |
| **Proton Experimental** | Bleeding-edge Valve branch | Valve |
| **GE-Proton** | Community fork: recent Wine, media-foundation/FSR/CUDA/PhysX/RawInput/NTSync patches, `protonfixes` | Thomas Crider ("GloriousEggroll") |
| **proton-cachyos** | CachyOS fork: dxvk-sarek, D7VK, FSR4/DLSS, nvidia-libs, PipeWire | CachyOS team |
| **UMU-Proton** | Valve Proton with UMU compatibility added; **default for `umu-run`** | Open Wine Components |

GE-Proton states that non-Steam use is supported **only via umu**, because
Proton is built to run inside the container runtime and running it outside
"severely breaks library compatibility."

---

## 5. Steam Linux Runtime and pressure-vessel

Proton is **built for a container**. The sandbox is **`pressure-vessel`** (from
steam-runtime-tools), built on **`bwrap`** (bubblewrap) + a Flatpak-derived
runtime. Rationale: Proton links a specific library set; against arbitrary
distro libraries the ABI breaks.

Steam launches a Proton game roughly as:

```
.../ubuntu12_32/reaper SteamLaunch AppId=348550 -- \
  .../ubuntu12_32/steam-launch-wrapper -- \
  .../SteamLinuxRuntime_sniper/_v2-entry-point --verb=waitforexitandrun -- \
  .../compatibilitytools.d/GE-Proton11-7/proton waitforexitandrun <game.exe>
```

Runtime generations:

| Runtime | Base | Used by |
|---|---|---|
| **Soldier** | SLR 2.0 (Debian 10) | Proton 5.13–7.x |
| **Sniper** | SLR 3.0 | Proton 8.0+ and native Linux games (`_v2-entry-point`) |
| **SteamRT 4** | `registry.gitlab.steamos.cloud/.../steamrt4` | vkd3d-proton cross-builds etc. |

Debugging: `STEAM_LINUX_RUNTIME_LOG=1`, `STEAM_LINUX_RUNTIME_VERBOSE=1`,
`PRESSURE_VESSEL_SHELL=instead` (shell inside the container),
`PRESSURE_VESSEL_FILESYSTEMS_RO` / `_RW`, `STEAM_COMPAT_LIBRARY_PATHS`.

The **Steam Flatpak** adds a second sandbox; its tools live under
`~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/`.

---

## 6. umu-launcher — Proton without Steam

**umu-launcher** (Open Wine Components) reimplements
`SteamLinuxRuntime_sniper` + steam-runtime-tools, renamed and modified to run
outside Steam. It renames `_v2-entry-point` → **`umu`** and
`steam-launch-wrapper` → **`umu-run`**, reproduces Steam's expected env, and
invokes **pressure-vessel** with a downloaded Steam Linux Runtime cached in
`$HOME/.local/share/umu`.

Core conventions:

| Variable | Meaning |
|---|---|
| `GAMEID` | umu-database id (e.g. `umu-battlenet`) selecting `protonfixes`; default `umu-default` |
| `PROTONPATH` | Proton dir path, version name (`GE-Proton11-7`), or codename (`GE-Proton` = latest); default **UMU-Proton** |
| `WINEPREFIX` | Prefix; default `$HOME/Games/umu/$GAMEID` |
| `PROTON_VERB` | Default `waitforexitandrun`; `run`/`runinprefix` attach to an existing wineserver |
| `UMU_LOG`, `UMU_RUNTIME_UPDATE`, `UMU_NO_PROTON`, `UMU_HTTP_TIMEOUT`, `UMU_HTTP_RETRIES`, `PROTONFIXES_DISABLE` | umu behaviour |

Because `pressure-vessel` exposes `$HOME` plus a subset of host paths, extra
paths are added with `STEAM_COMPAT_LIBRARY_PATHS` or
`PRESSURE_VESSEL_FILESYSTEMS_*`.

### 6.1 The `frostfireinstaller` invocation

```sh
umu-run \
  WINEPREFIX=~/Games/battlenet/prefix \
  GAMEID=umu-battlenet \
  PROTONPATH=<detected Proton build> \
  WINE_SIMULATE_WRITECOPY=1 \
  WINEDLLOVERRIDES="locationapi=d" \
  'C:\Program Files (x86)\Battle.net\Battle.net.exe'
```

The environment applied to the launcher is inherited by every game Battle.net
spawns (same prefix → same wineserver session).

---

## 7. Graphics translation

### 7.1 DXVK — D3D8/9/10/11 → Vulkan

Drop-in DLLs (`d3d8/9/10core/11`, `dxgi`) installed with native overrides.
Maintained by Philip Rebohle (doitsujin) and Joshua Ashton.

| Variable | Effect |
|---|---|
| `DXVK_HUD` | `fps,devinfo,frametimes,pipelines,memory,...`; `1` or `full` |
| `DXVK_FILTER_DEVICE_NAME` | Substring match to force a GPU (hybrid systems) |
| `DXVK_FILTER_DEVICE_UUID` | Exact device selection |
| `DXVK_SHADER_CACHE=0` / `DXVK_SHADER_CACHE_PATH` | Disable / relocate state cache (`*.dxvk-cache`) |
| `DXVK_LOG_LEVEL`, `DXVK_LOG_PATH`, `DXVK_DEBUG`, `DXVK_CONFIG_FILE` | Logging/`dxvk.conf` |
| `DXVK_STATE_CACHE_PATH` | Steam/umu state-cache dir |

Since DXVK 2.x, Graphics Pipeline Library lets shaders compile at shader-load
time rather than draw time (less stutter).

### 7.2 vkd3d-proton — D3D12 → Vulkan

The D3D12 backend, by Hans-Kristian Arntzen (themaister). Hard requirements:
Vulkan 1.3, descriptor indexing with ≥ 1,000,000 UpdateAfterBind descriptors,
`samplerMirrorClampToEdge`, `shaderDrawParameters`, `VK_EXT_robustness2`,
`VK_KHR_push_descriptor`. Recommended: `VK_EXT_mutable_descriptor_type`,
`VK_EXT_descriptor_buffer`, `VK_EXT_image_view_min_lod`. Minimum drivers: RADV
(Mesa 22.0+), NVIDIA 535+.

| Variable | Effect |
|---|---|
| `VKD3D_CONFIG` | `dxr, dxr12, force_static_cbv, single_queue, breadcrumbs, descriptor_qa_checks, pipeline_library_app_cache, ...` |
| `VKD3D_DEBUG`, `VKD3D_SHADER_DEBUG`, `VKD3D_LOG_FILE` | Logging |
| `VKD3D_SHADER_CACHE_PATH` (`=0`) | Relocate/disable `vkd3d-proton.cache` |
| `VKD3D_VULKAN_DEVICE`, `VKD3D_FILTER_DEVICE_NAME` | Device selection |
| `VKD3D_SWAPCHAIN_PRESENT_MODE`, `VKD3D_FRAME_RATE` | Presentation/frame pacing |

### 7.3 WineD3D (legacy OpenGL path)

`PROTON_USE_WINED3D=1` forces Wine's built-in D3D→OpenGL translator instead of
DXVK. `PROTON_NO_D3D11` / `PROTON_NO_D3D10` make games fall back to older D3D.

### 7.4 Overlays / post-processing

- **MangoHud** — `MANGOHUD=1`, `MANGOHUD_CONFIG`, `~/.config/MangoHud/MangoHud.conf`,
  per-app `wine-<exe>.conf`. With gamescope use `--mangoapp`.
- **vkBasalt** — `ENABLE_VKBASALT=1`; CAS/FXAA/SMAA, 3D LUT, ReShade FX.

---

## 8. Synchronization primitives

Wine's default IPC goes through `wineserver` (slow for games). Three faster
implementations exist; **use only one**.

| Primitive | Mechanism | Env | Kernel / notes |
|---|---|---|---|
| **esync** | `eventfd`, userspace | `WINEESYNC=1` | Proton default historically; **obsoleted in Proton 11.0** |
| **fsync** | `futex2`/`FUTEX_WAIT_MULTIPLE` | `WINEFSYNC=1` | Linux ≥ 5.16; Proton default; auto-disabled if unsupported |
| **ntsync** | in-kernel `/dev/ntsync` driver implementing NT semaphores/mutexes/events | `PROTON_USE_NTSYNC=1` | Linux ≥ 6.14, `CONFIG_NTSYNC`; Valve Proton 11.0+, GE-Proton 10-10+, CachyOS |

Disable toggles: `PROTON_NO_ESYNC`, `PROTON_NO_FSYNC`, `PROTON_NO_NTSYNC`
(GE) / `PROTON_USE_NTSYNC=0` (CachyOS). Check: `lsof /dev/ntsync`.
Local kernel is **7.2.4** → ntsync-capable if the module is enabled.

---

## 9. Performance layers

| Layer | How | Notes |
|---|---|---|
| **MangoHud** | overlay | FPS/frametimes/CPU/GPU; `winesync`/`wine` fields |
| **GameMode** | `gamemoderun %command%` | CPU governor, scheduling, I/O priority |
| **Gamescope** | `gamescope -f --` | micro-compositor, FSR/NIS/SGSR, FPS cap, HDR; needs `nvidia-drm.modeset=1` on NVIDIA |
| **FSR** | GE: `WINE_FULLSCREEN_FSR=1`, `WINE_FULLSCREEN_FSR_STRENGTH`, `WINE_FULLSCREEN_FSR_CUSTOM_MODE` | gamescope: `-F fsr\|nis\|sgsr` |
| **NTSync** | see §8 | input/load responsiveness |
| **`vm.max_map_count`** | `sudo sysctl vm.max_map_count=2147483642` | some games need it; persist in `/etc/sysctl.d/` |

---

## 10. Vulkan drivers

A "Vulkan-capable driver" = a userspace ICD (`.json` under
`/usr/share/vulkan/icd.d/`) + a kernel DRM driver. `vulkaninfo --summary` lists
devices.

| Driver | Provider | Notes |
|---|---|---|
| **RADV** | Mesa (AMD GCN+) | Recommended AMD driver; GFX6-7 Vulkan 1.3, GFX8+ 1.4; used on Steam Deck |
| **ANV** | Mesa (Intel Gen8+) | |
| **NVIDIA** | Proprietary `nvidia_icd.json` | vkd3d-proton wants ≥ 535 |
| **lavapipe** | Mesa software (LLVMpipe) | CI/headless only |

Device forcing: `DXVK_FILTER_DEVICE_NAME` / `VKD3D_FILTER_DEVICE_NAME`, or limit
ICDs with `VK_DRIVER_FILES` (formerly `VK_ICD_FILENAMES`).

### 10.1 Local GPU inventory **[verified]**

| Device | Driver | API |
|---|---|---|
| AMD Radeon Graphics (RADV RENOIR, iGPU) | `radv` / Mesa 26.2.2 | 1.4.354 |
| NVIDIA GeForce RTX 3050 Ti Laptop GPU | `NVIDIA` 615.71.09 | 1.4.351 |
| llvmpipe | `llvmpipe` / Mesa 26.2.2 | 1.4.354 |

Hybrid AMD+NVIDIA on NVIDIA's **open** modules — the setup behind the documented
`NVRM: Xid 109` / `CTX SWITCH TIMEOUT` GPU hangs (see §14.3).

---

## 11. Battle.net under Wine

### 11.1 Why the CEF UI breaks

The launcher is a 32-bit Windows app wrapping **Chromium Embedded Framework**
(`libcef.dll` + `Battle.net Helper.exe` subprocesses); login/store pages are
HTML. The best-documented root cause is a **memory-protection mismatch**: Wine's
`NtProtectVirtualMemory` returned `PAGE_WRITECOPY` (8) as the old protection where
Chromium expected `PAGE_READWRITE` (4), tripping Chromium's
`CHECK(old == PAGE_READWRITE)` and crashing with `0x80000003` inside `libcef.dll`.

### 11.2 The two canonical fixes

| Variable | Value | Why |
|---|---|---|
| `WINE_SIMULATE_WRITECOPY` | `1` | Wine marks the COW page as copied and returns the expected protection; fixes the blank/grey CEF window and Agent init stall |
| `WINEDLLOVERRIDES` | `locationapi=d` | Disables Wine's Location API stub; clears blank CEF login / "Agent asleep" |

Both must be set on the process that **starts Battle.net**; children inherit them.

### 11.3 Symptom map

| Symptom | Likely cause / fix |
|---|---|
| Black/grey window, no assets | CEF write-copy regression → `WINE_SIMULATE_WRITECOPY=1` / newer Proton |
| Spinning gear, no login buttons | Disable HW accel / clear launcher cache; `locationapi=d` |
| `tassadar Login URL is empty` | CEF page never loaded — a *symptom*, same fix set |
| `BLZBNTBNA00000005` "Agent has gone to sleep" | Newer Proton/GE + `locationapi=d` + clear `ProgramData/Battle.net/Agent` |
| `dxvk::DxvkError` / missing DLL | 32-bit Vulkan/DXVK missing |
| Unexpected/Blizzard error | Fonts (`winetricks corefonts`) or missing 32-bit Vulkan loader |

Battle.net needs the **32-bit** DXVK (`d3d11.dll`, `dxgi.dll`) and a 32-bit
Vulkan ICD; WoW itself uses 64-bit DXVK (D3D11) or vkd3d-proton (D3D12), sharing
one DXGI implementation (DXVK 2.1+).

### 11.4 Process model

`Battle.net.exe` (UI, 32-bit, hosts CEF) drives **`Agent.exe`**, the standalone
updater that installs/updates/repairs via **TACT/NGDP** into **CASC** archives.
Agent exposes a local REST API on `127.0.0.1:1120` and publishes its port via
`Global\Battle.netHelperSvcPortObject`. Battle.net launches the game binary **as
a child in the same Wine session/prefix**, so all env and overrides propagate.
One corrupted prefix affects every Blizzard game in it.

### 11.5 Log and path locations

| What | Path (inside prefix) |
|---|---|
| Launcher/CEF | `drive_c/users/<user>/AppData/Local/Battle.net/Logs/` (`libcef-*.log`) |
| Agent | `drive_c/ProgramData/Battle.net/Agent/Agent.<build>/Logs/` and `/Errors/` |
| WoW logs | `.../_retail_/Logs/`, `_classic_/Logs/`, `_classic_beta_/Logs/` (`gx.log`) |
| WoW config | `<edition>/WTF/Config.wtf` (and `Config-cache.wtf`, `Account/`, `SavedVariables`) |
| Installer prefix | `~/Games/battlenet/prefix` (this project) |
| Steam prefix | `~/.steam/steam/steamapps/compatdata/<appid>/pfx/` |

---

## 12. World of Warcraft: Forever

> **Sourcing note.** The product details below are from community/industry
> sources (Wikipedia, Warcraft Wiki, Wowhead, Blizzard news mirrors), not from
> Blizzard's official Linux documentation. The version `1.60.1.69913`, the
> `wow_classic_beta` product and `WowB.exe` are corroborated by this project's
> own observed environment. Treat *[uncertain]* items as hypotheses to verify at
> launch.

### 12.1 What it is **[community]**

An official Blizzard **"Classic+"** flavor of World of Warcraft that runs
alongside Retail (*Midnight*, 12.x) and WoW Classic (Era 1.15.x). Described as a
separate-continuity **"time bubble"** during WoW's first year (25 ADP). Internal
codename **"Camelot"** (explicitly to be renamed before launch). Announced at
BlizzCon 2026. Platforms: Windows and macOS — **no official Linux support.**

### 12.2 Version and dates **[community]**

| Item | Value |
|---|---|
| Version line | **1.60.x** (distinct from Era 1.15.x and Retail 12.x) |
| Beta build | **1.60.1 (69913)**, 2026-09-17 → **1.60.1 (69977)**, 2026-09-22 (fixes the `Xid 109` hang) |
| Beta window | 2026-09-17 → 2026-10-21 |
| Global launch | **2026-11-04, 15:00 PST** |
| Battle.net product (beta) | **`wow_classic_beta`** (observed in this project) |
| Launcher label | "World of Warcraft: Forever [Beta]" under Classic / In Development |
| Executable | `WowB.exe` (observed in this project **[verified locally]**; not publicly documented **[uncertain]**) |

Because Forever is built from the **Modern/Mainline client** (it exposes most
12.1.5 APIs) yet carries a Classic-era version number, the Linux path is the
**same as retail/Classic today**: Battle.net under Wine/Proton with
DXVK/vkd3d-proton, D3D12.

### 12.3 Official system requirements **[community, from Battle.net store via Wowhead]**

**Windows**

| | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 64-bit (May 2019 Update+) | Windows 11 |
| CPU | 4 cores / 3.0 GHz (Haswell / Ryzen Zen) | 8 cores / 5.2 GHz (Core Ultra 2 / Zen 5) |
| GPU | **DirectX 12-capable, 4 GB** (GTX 10-series / RDNA 1 / Iris Xe2-LPG) | **DX12, 8 GB** (RTX 40-series / RDNA 3 / Arc B-series) |
| RAM | 8 GB | 16 GB |
| Storage | SSD, 128 GB free | SSD, 128 GB free |
| Internet | Broadband | Broadband |
| Display | 1280×720 | 1280×720 |

**macOS:** macOS 12+ (min, Apple M2 / Coffee Lake) → macOS 15+ (rec, Apple M4);
Metal-capable 4 GB → 16 GB; SSD 128 GB.

**GPU floor:** GCN 1 (2012) / NVIDIA Maxwell (2014) / Intel Skylake (2015). Older
cards (GTX 760/770/780, HD 6950, Intel HD 6000) are unsupported. New art relies
on RGBA16F UAV compute-shader support.

**Linux equivalent:** a Vulkan 1.3 driver with vkd3d-proton's required extensions
(RADV Mesa 22+ / NVIDIA 535+). The local RTX 3050 Ti and RADV Renoir both clear
this bar.

### 12.4 Linux status **[community / uncertain]**

- No ProtonDB/Wine AppDB entry for Forever was found.
- A Wowhead user reported installing/running the beta under **Lutris** by setting
  game arguments `--game=wow_classic_beta --install`, implying the product works
  in a Wine prefix like other WoW flavors.
- General WoW-under-Wine knowledge (D3D11 fallback, shader caches) applies.
- **Build 69913 was a regression, fixed in 69977.** On 69913 the beta had an
  `Xid 109` GPU hang on world entry (all NVIDIA generations, D3D11 and D3D12)
  plus a soft narration assert (`ERROR #135`). The hang was a **client shader
  bug** (see §14.5/§14.6) and **build 69977 (2026-09-22) fixes it** — verified on
  the reference machine (2026-09-24, RTX 3050 Ti, zero `Xid`). See
  `docs/wow-forever-error-history.md` and `docs/troubleshooting.md`.

### 12.5 DirectX API selection

Modern WoW selects D3D11 or D3D12 via `Config.wtf`:

```ini
# <edition>/WTF/Config.wtf
SET GxApi "D3D11"   ; or "D3D12"
```

or the launch args `-d3d11` / `-d3d12` (Battle.net → game → Options →
Additional command line arguments). On Linux, D3D11 → **DXVK**, D3D12 →
**vkd3d-proton**.

---

## 13. Anti-cheat: Warden vs Ricochet

| | Blizzard **Warden** (WoW, Diablo, SC, WC3) | **Ricochet** (Call of Duty) |
|---|---|---|
| Privilege | **User-mode (ring 3)**, module in the game process | **Kernel-level (ring 0) driver** |
| Behaviour | Scans memory/modules against signatures; server can push encrypted modules | "Operates with high privileges… access all resources on your system" |
| Under Wine | **Works** (ordinary Win32 API) | **Cannot work** — Wine does not load Windows kernel drivers |

This distinction is the whole answer to "why does WoW work but Call of Duty
doesn't?" It is a vendor/anti-cheat limitation, not a limitation of the tool.
Overwatch uses Warden (user-space), hence it runs too.

---

## 14. Known WoW-on-Linux failure modes and fixes

### 14.1 `ERROR #109 (0x8510006d)` — thread unresponsive (D3D12/VKD3D)

Symptom: the game window is up, then freezes; the crash dialog reports
`ERROR #109` / `Soft Lock`, and the stack shows
`dxgi.dll` / `d3d12core.dll` with `<GxApi> D3D12`.

Cause: the **D3D12 path (vkd3d-proton) hangs**. Primary fix: switch to **D3D11**
(DXVK):

- In game: **System → Graphics → Graphics API → DirectX 11**
- `SET GxApi "D3D11"` in `<edition>/WTF/Config.wtf`
- or launch arg `-d3d11`

### 14.2 `gx.log` / device-lost evidence

```
Failure in WaitForFence
Device Removed Reason: GPU Hung. Timeout when waiting for queue: Graphics (0x80070102)
```

vkd3d warns `VK_ERROR_DEVICE_LOST` (`0x887a0005`). If the stack is in `dxgi.dll`
on the present path and **both** D3D11 and D3D12 hang, it is a **driver** issue,
not the API choice.

### 14.3 NVIDIA GPU hang — `NVRM: Xid 109` / `CTX SWITCH TIMEOUT`

> **For WoW: Forever this is resolved.** It was a build-69913 client shader bug
> (see §14.5), **fixed in build 69977**; it was not the driver or the open
> modules (switching to proprietary did not help — see §14.6). The mitigations
> below apply to other titles or older builds.

```bash
journalctl -k | grep -i nvrm
# NVRM: Xid (PCI:0000:01:00): 109, name=WowB.exe, errorString CTX SWITCH TIMEOUT
```

Common on hybrid/Optimus laptops with NVIDIA's **open** kernel modules (this
machine's exact configuration). Changing Proton or lowering settings usually
does **not** help. Mitigations, easiest first:

1. **GPU persistence** (reversible, in-app): `systemctl enable --now nvidia-persistenced`.
2. **Disable runtime power management:**
   `sudo sh -c 'echo on > /sys/bus/pci/devices/0000:01:00.0/power/control'`;
   persist with `options nvidia NVreg_DynamicPowerManagement=0x00`.
3. **PCIe ASPM performance:** `echo performance > /sys/module/pcie_aspm/parameters/policy`;
   persist with `pcie_aspm.policy=performance`.
4. **Update/switch driver:** `rpm-ostree upgrade`; if persistent, rebase
   `bazzite-nvidia-open` → proprietary `bazzite-nvidia`.
5. **Last resort — run on the iGPU** (enough for WoW): in
   `~/.config/frostfireinstaller/config.toml`:

   ```toml
   [env]
   DXVK_FILTER_DEVICE_NAME = "AMD Radeon"
   ```

### 14.4 Other freezes / low performance

- Turn off MangoHud to rule out the overlay.
- Delete `vkd3d-proton.cache*` / DXVK cache and let it rebuild (**after** full exit).
- Try another runner (Proton-CachyOS / UMU-Proton / GE-Proton).
- Toggle GameMode/Gamescope off to isolate.
- Raise `vm.max_map_count`.
- Ensure GPU driver (Mesa/NVIDIA) is current.

### 14.5 The shader root cause and the `VKD3D_SHADER_OVERRIDE` workaround **[community]**

**Root cause (isolated 2026-09-24).** The build-69913 `Xid 109` was a single
**compute shader** — the **Global Illumination probe update**. Its two outer loops
take their iteration count from a constant buffer (`cb0[2] / cb0[3]`); on the
**first dispatch** after GI resources are created the count is not yet valid and
nothing bounds the loops, so the shader never terminates and the driver times out
the context. Triggered by `giQuality >= 1` or `graphicsLightMode >= 2`. It is a
**client defect**, not the driver: the same setting times out drivers on
AMD/Windows and freezes macOS. Fixed by Blizzard in **69977**.

**Workaround (69913 only).** Dump the shaders the client compiles
(`VKD3D_SHADER_DUMP_PATH`), bound every `OpLoopMerge` (e.g. 4096 iterations),
run with `VKD3D_SHADER_OVERRIDE`, and delete `_classic_beta_/vkd3d-proton.cache`
before dumping and before playing. The override must be set on **Battle.net**
(children inherit it). D3D12 only. Sources: [Blizzard #2359917], [gist: fx].

[Blizzard #2359917]: https://us.forums.blizzard.com/en/wow/t/linuxnvidia-forever-gi-secondary-lighting-gpu-hang-xid-109-cause-isolated-shader-override-workaround/2359917
[gist: fx]: https://gist.github.com/fx/88cf5be8bed8e9ce761e26e183b0ba90

### 14.6 Errors seen on the reference machine

On the reference machine (Bazzite, RTX 3050 Ti Laptop, GE-Proton11-7), several
*graphically different* errors occur. Keep them apart — only the second is a GPU
fault.

1. **`ERROR #109` is a symptom of NVIDIA `Xid 109` (`CTX SWITCH TIMEOUT`)** — a
   **build-69913 regression, fixed in build 69977** (see §14.5). The render thread
   blocks in `dxgi.dll`; the 20 s
   watchdog fires. The crashes are **early (1–6 min) and at low memory
   (13–22 %)**, so this is not memory pressure and not the power profile.
   Community reports reproduce it on **desktop and laptop** NVIDIA GPUs (GTX 1070
   → RTX 4090) on **both D3D11 and D3D12**, and build **69893 was stable** — it is
   a client regression in the new render path (Secondary Lighting / Global
   Illumination), not an outdated driver ([Proton #10157], [vkd3d-proton #3304],
   [Blizzard #2353584]). The client's device-lost recovery also deadlocks in
   `WaitForFence`, which turns any device loss into a hang. **Workarounds:** set
   **Secondary Lighting to Fair** (Options → Graphics), lower GI/Volumetric Fog,
   or run on the **integrated GPU** (bypasses the NVIDIA path entirely — the app
   exposes Auto / NVIDIA / Integrerad under **Avancerat → Grafik**). The game
   often **recovers by re-creating its D3D11 device**
   (`Device Destroy Successful` → `Dx11 Device Create Successful`). On **69977**
   the reference machine plays on the NVIDIA GPU with **no** `Xid` (2026-09-24).

2. **`ERROR #135` is a separate narration/voice assert**, at the login screen:
   `ASSERTSAFE(m_platformInterface != nullptr)` in `VoiceSpeakManager.cpp`, called
   from `StopSpeakingText` / `NarrateCurrentScreen ("Login Screen")`. It is the new
   text-to-speech subsystem, fires repeatedly (~every 1.7 s) **even with screen
   narration disabled**, and is a soft assert — dismiss it. It is not graphics and
   does not depend on the GPU.

3. **Progressive slowdown is VRAM pressure, not heat.** `gx.log` "Periodic Gpu
   Status Report" climbs from 0.6 GB to 2.7 GB of a **3.3 GB budget** (84 %) while
   clocks stay ~1.9 GHz and temp stays ~70–81 °C; the kernel logs
   `NV_ERR_NO_MEMORY … _memdescAllocInternal`. Effective budget on a 4 GB GPU is
   ~3.3 GB after desktop + Battle.net. Mitigate by running on the iGPU
   (`DXVK_FILTER_DEVICE_NAME="AMD Radeon"`), closing Battle.net after launch,
   capping FPS/render scale, and raising `maxFPSBK` in `<edition>/WTF/Config.wtf`.
   `/reload` does not touch GPU resources.

   > **Still open on 69977.** A **session-long FPS degradation / apparent memory
   > leak** persists after the `Xid` fix (frame rate falls toward ~30 in
   > Ironforge/Stormwind with GPU at full clocks). Community reports describe it
   > as a client leak; it is separate from the shader bug. A relog to the
   > character screen temporarily helps.

4. **Client error report confirms the product identity:** `Exception.WowProject:
   Camelot`, `Branch: 1.60.1`, `BuildNumber: 69913`, `Platform: Linux (x86 64-bit)`,
   executable `WowB.exe` — matching §12.

[Proton #10157]: https://github.com/ValveSoftware/Proton/issues/10157
[vkd3d-proton #3304]: https://github.com/HansKristian-Work/vkd3d-proton/issues/3304
[Blizzard #2353584]: https://us.forums.blizzard.com/en/wow/t/wowf-beta-69913-hard-gpu-hang-entering-world-map-2991-client-deadlock-in-device-lost-recovery-error-109/2353584

---

## 15. Environment-variable quick reference

| Variable | Typical value | Purpose |
|---|---|---|
| `WINE_SIMULATE_WRITECOPY` | `1` | Battle.net CEF fix |
| `WINEDLLOVERRIDES` | `locationapi=d` | Battle.net blank-login fix |
| `WINEPREFIX` | `~/Games/battlenet/prefix` | Dedicated prefix / session boundary |
| `GAMEID` | `umu-battlenet` | umu identity / protonfixes lookup |
| `PROTONPATH` | detected build | Runner |
| `WINEESYNC` / `WINEFSYNC` | `1` | esync / fsync |
| `PROTON_USE_NTSYNC` | `1` | Enable ntsync |
| `PROTON_NO_ESYNC` / `_NO_FSYNC` / `_NO_NTSYNC` | `1` | Disable a primitive |
| `PROTON_USE_WINED3D` | `1` | Legacy D3D→OpenGL |
| `PROTON_ENABLE_NVAPI` | `1` | NVAPI/DLSS shim |
| `DXVK_HUD` | `fps,devinfo` | DXVK overlay |
| `DXVK_FILTER_DEVICE_NAME` | `"AMD Radeon"` | Force GPU (hybrid) |
| `DXVK_SHADER_CACHE` | `0` / path | Disable/relocate DXVK cache |
| `VKD3D_CONFIG` / `VKD3D_DEBUG` / `VKD3D_SHADER_CACHE_PATH` | — | vkd3d behaviour/log/cache |
| `VKD3D_FILTER_DEVICE_NAME` | `"AMD Radeon"` | Force GPU for D3D12 |
| `MANGOHUD` | `1` | MangoHud overlay |
| `ENABLE_VKBASALT` | `1` | vkBasalt post-processing |
| `PROTON_VERB` | `waitforexitandrun` | umu/proton launch verb |
| `PROTON_LOG` | `1` | Proton debug log |

---

## 16. Recommended stack for this machine **[verified]**

| Component | Value |
|---|---|
| OS | Bazzite 44.20260919.0 (Kinoite, Fedora-atomic base) |
| Kernel | 7.2.4-ogc3.1.fc44.x86_64 |
| Session | Wayland, KDE |
| GPU (dGPU) | NVIDIA RTX 3050 Ti Laptop (driver 615.71.09, Vulkan 1.4.351) |
| GPU (iGPU) | AMD Cezanne — RADV RENOIR, Mesa 26.2.2 (Vulkan 1.4.354) |
| Backend | `umu-run` 1.4.4 (`/usr/bin/umu-run`) |
| Proton builds | GE-Proton11-7, UMU-Proton-10.0-4, Proton Experimental |
| Prefix / games | `~/Games/battlenet` |
| Fixes | `WINE_SIMULATE_WRITECOPY=1`, `WINEDLLOVERRIDES=locationapi=d` |

**Environment guidance for WoW Forever:**

- Install via Battle.net with the **Game Version** set to *World of Warcraft:
  Forever* (beta product `wow_classic_beta` during beta).
- Prefer **D3D11** (`SET GxApi "D3D11"` / `-d3d11`) — the mature DXVK path and
  the standard escape from `ERROR #109` on older builds.
- **Update to build 69977 or later** — it fixes the 69913 `Xid 109` hang. Keep the
  NVIDIA driver current; if `Xid 109` still appears, follow §14.3. The AMD iGPU
  via `DXVK_FILTER_DEVICE_NAME="AMD Radeon"` is a viable fallback.
- Enable ntsync if `/dev/ntsync` exists on kernel 7.2.4 (requires a supporting
  Proton/GE build).
- Verify with `frostfireinstaller doctor` and the in-app system check.

---

## 17. Open questions / verification checklist

1. **Post-launch Battle.net product code / label** for Forever after it leaves
   beta (the codename "Camelot" is explicitly temporary).
2. **`WowB.exe` / codename** — *confirmed locally* via the client's own error
   report (`WowProject: Camelot`, `Branch 1.60.1`, `BuildNumber 69913`,
   `Platform: Linux (x86 64-bit)`). Remaining: the **final** executable name and
   Battle.net product code after the beta renames "Camelot".
3. **Proton/Steam Deck reports** for Forever (`wow_classic_beta` /
   `wow_forever`) — gather ProtonDB data after launch.
4. **ntsync availability** on this kernel: `lsof /dev/ntsync` /
   `modprobe ntsync`; confirm the chosen Proton build enables it.
5. **Forever-specific Linux GPU behavior** — ~~whether it reproduces the
   `Xid 109` hang~~ *answered:* 69913 reproduced it, **69977 fixed it** (2026-09-24,
   verified on the reference machine). Open: the separate session FPS
   degradation / memory leak.
6. **corefonts**: decide whether the prefix needs `winetricks corefonts` or if
   GE-Proton's built-in font handling suffices.

---

## 18. Confidence legend

| Tag | Meaning |
|---|---|
| **[verified]** | Confirmed on the local machine during this session |
| **[community]** | Multiple community/industry sources; may change by build |
| **[uncertain]** | Single/weak source or explicitly unconfirmed |
| *(unmarked)* | Standard, widely-documented stack behaviour |

---

## 19. Sources

**Wine / Proton / stack**
- Wine — Arch Wiki: https://wiki.archlinux.org/title/Wine
- WineHQ User's Guide / FAQ (GitLab wiki)
- wine-mono: https://github.com/wine-mono/wine-mono
- Valve Proton: https://github.com/ValveSoftware/Proton
- GE-Proton: https://github.com/GloriousEggroll/proton-ge-custom
- Proton-CachyOS: https://github.com/CachyOS/proton-cachyos
- DXVK: https://github.com/doitsujin/dxvk
- vkd3d-proton: https://github.com/HansKristian-Work/vkd3d-proton
- umu-launcher: https://github.com/Open-Wine-Components/umu-launcher
- Steam Linux Runtime container doc: https://gitlab.steamos.cloud/steamrt/steam-runtime-tools
- ntsync kernel uAPI: https://docs.kernel.org/userspace-api/ntsync.html
- MangoHud: https://github.com/flightlessmango/MangoHud
- Gamescope: https://github.com/ValveSoftware/gamescope
- vkBasalt: https://github.com/DadSchoorse/vkBasalt
- Mesa RADV / ANV: https://docs.mesa3d.org/drivers/radv.html · https://docs.mesa3d.org/drivers/anv.html

**Battle.net / WoW on Wine**
- CEF write-copy analysis: https://github.com/wiesson/diablo4-on-mac/blob/main/docs/technical-notes.md
- Lutris Battle.net guide: https://github.com/lutris/docs/blob/master/Battle.Net.md
- GamingOnLinux Battle.net guide
- wowdev.wiki Agent: https://wowdev.wiki/Agent
- vkd3d-proton issue #3304 (WowB.exe Xid 109)
- Valve Proton issue #10157 (WoW Forever Xid 13/109)
- Shader root cause + override: https://us.forums.blizzard.com/en/wow/t/linuxnvidia-forever-gi-secondary-lighting-gpu-hang-xid-109-cause-isolated-shader-override-workaround/2359917
- Loop-cap shader tool (gist): https://gist.github.com/fx/88cf5be8bed8e9ce761e26e183b0ba90
- Blizzard blue post, build 69977: https://us.forums.blizzard.com/en/wow/t/beta-client-update-september-22/2358655
- PCGamingWiki anti-cheat: https://www.pcgamingwiki.com/wiki/Anti-cheat_middleware
- Ricochet announcement: https://news.blizzard.com/en-us/article/23733251/ricochet-anti-cheat-call-of-dutys-new-anti-cheat-initiative

**WoW: Forever**
- https://en.wikipedia.org/wiki/World_of_Warcraft:_Forever
- https://warcraft.wiki.gg/wiki/World_of_Warcraft:_Forever
- https://warcraft.wiki.gg/wiki/Patch_1.60.1/API_changes
- https://wowhead.com/forever/guide/beta-content-unlock-overview
- https://news.blizzard.com/en-us/article/24301508/ (pre-purchase)
- https://worldofwarcraft.blizzard.com/en-us/news/24301512 (GPU requirements)

---

*End of technical reference. See `docs/architecture.md`, `docs/install.md`,
`docs/design.md` and `docs/troubleshooting.md` for project-specific documentation.*