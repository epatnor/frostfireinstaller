# Technical reference — Battle.net on Linux

Background for the choices `frostfireinstaller` makes. Items tagged **[verified]**
were confirmed on the maintainer's own hardware, **[community]** come from community
sources and may change between builds. Everything else is standard, documented
stack behaviour; for depth follow the links at the end.

## 1. The stack

```
 Game .exe (Battle.net.exe → Wow.exe / WowB.exe)   Win32 + Direct3D
   └─ Wine (ntdll, kernel32, ... + wineserver), one WINEPREFIX = one session
        ├─ D3D8/9/10/11 → DXVK          D3D12 → vkd3d-proton
        └─ XAudio2 → FAudio             NVAPI/DLSS → dxvk-nvapi
             └─ Vulkan loader → RADV / ANV / NVIDIA   (layers: MangoHud, Gamescope)
 Wrapped by pressure-vessel + bwrap (Steam Linux Runtime), driven by
 Steam, or by umu-launcher (umu-run) for non-Steam clients.
```

- **Wine is not an emulator** and not a sandbox (`Z:` is `/`, full user rights).
- **Proton** = Wine + patches + DXVK + vkd3d-proton + FAudio + dxvk-nvapi + a
  container runtime. GE-Proton, Proton-CachyOS and UMU-Proton are community builds;
  GE-Proton supports non-Steam use **only via umu**.
- **umu-launcher** reproduces Steam's runtime and `pressure-vessel` outside Steam.
  `GAMEID` selects protonfixes (`umu-battlenet`), `PROTONPATH` is a Proton dir or
  codename (`UMU-Proton`, `GE-Proton`), `WINEPREFIX` the prefix. The runtime is cached
  in `~/.local/share/umu`; extra host paths need `STEAM_COMPAT_LIBRARY_PATHS` or
  `PRESSURE_VESSEL_FILESYSTEMS_*`.
- **The wineserver session boundary is the prefix:** the launcher and every game it
  spawns share one environment — why launcher-level fixes reach the games.

Our invocation:

```sh
umu-run WINEPREFIX=~/Games/battlenet/prefix GAMEID=umu-battlenet PROTONPATH=<build> \
  WINE_SIMULATE_WRITECOPY=1 WINEDLLOVERRIDES="locationapi=d" \
  'C:\Program Files (x86)\Battle.net\Battle.net.exe'
```

## 2. Graphics, sync and overlays

| Topic | Notes |
|---|---|
| DXVK (D3D≤11) | `DXVK_HUD`, `DXVK_FILTER_DEVICE_NAME` (substring, picks the GPU on hybrid systems), `DXVK_SHADER_CACHE`. |
| vkd3d-proton (D3D12) | Needs Vulkan 1.3 (RADV Mesa 22+, NVIDIA 535+). `VKD3D_CONFIG`, `VKD3D_FILTER_DEVICE_NAME`, `VKD3D_SHADER_CACHE_PATH`. |
| Sync primitives | Use one: esync (obsolete in Proton 11), fsync (Linux ≥ 5.16, default), **ntsync** (`PROTON_USE_NTSYNC=1`, Linux ≥ 6.14, `/dev/ntsync`; Proton 11+, GE 10-10+, CachyOS). |
| MangoHud | `MANGOHUD=1`; with gamescope use `--mangoapp`. |
| GameMode / Gamescope | CPU/IO tuning / micro-compositor; gamescope needs `nvidia-drm.modeset=1` on NVIDIA and is hazardous on NVIDIA + Wayland (see [troubleshooting](troubleshooting.md)). |
| Legacy | `PROTON_USE_WINED3D=1` forces D3D→OpenGL. |

Battle.net needs the **32-bit** DXVK and a 32-bit Vulkan ICD; WoW uses 64-bit DXVK
(D3D11) or vkd3d-proton (D3D12). `vulkaninfo --summary` lists devices.

## 3. Battle.net under Wine

The launcher is a 32-bit app wrapping Chromium Embedded Framework; login and store
are HTML. The documented root cause of the blank/grey UI is a memory-protection
mismatch: Wine returned `PAGE_WRITECOPY` where Chromium's
`CHECK(old == PAGE_READWRITE)` expected `PAGE_READWRITE`, crashing with
`0x80000003` in `libcef.dll`.

| Variable | Value | Why |
|---|---|---|
| `WINE_SIMULATE_WRITECOPY` | `1` | returns the expected protection; fixes blank CEF window and Agent init stall |
| `WINEDLLOVERRIDES` | `locationapi=d` | disables the Location API stub; clears blank login / "Agent asleep" |

Set both on the process that **starts Battle.net**.

| Symptom | Likely cause / fix |
|---|---|
| Black/grey window | CEF write-copy → `WINE_SIMULATE_WRITECOPY=1` / newer Proton |
| Spinning gear, no login | clear launcher cache; `locationapi=d` |
| `tassadar Login URL is empty` | CEF page never loaded — a symptom of the above |
| `BLZBNTBNA00000005` Agent asleep | newer Proton/GE + `locationapi=d` + clear `ProgramData/Battle.net/Agent` |
| `dxvk::DxvkError`, missing DLL | 32-bit Vulkan/DXVK missing |

**Process model:** `Battle.net.exe` (UI) drives `Agent.exe` (updater, TACT/NGDP →
CASC archives; REST API on `127.0.0.1:1120`) and launches games as children in the
same prefix. One corrupted prefix affects every Blizzard game in it.

| What | Path (inside the prefix) |
|---|---|
| Launcher/CEF | `drive_c/users/<user>/AppData/Local/Battle.net/Logs/` |
| Agent | `drive_c/ProgramData/Battle.net/Agent/Agent.<build>/Logs/` and `Errors/` |
| WoW | `<edition>/Logs/`, `<edition>/WTF/Config.wtf`, `<edition>/Errors/` |

## 4. Anti-cheat

Blizzard's **Warden is user-mode** and works under Wine (WoW, Diablo, StarCraft,
Warcraft III, Overwatch). **Call of Duty's Ricochet is a kernel driver**; Wine does
not load Windows kernel drivers, so it cannot work. A vendor limitation, not a
limitation of this tool.

## 5. World of Warcraft: Forever **[community]**

An official "Classic+" flavour on the Mainline client, version line **1.60.x**,
codename "Camelot" (temporary), Battle.net product `wow_classic_beta`, executable
`WowB.exe` (confirmed locally via the client's error report **[verified]**).
Beta from 2026-09-17, launch 2026-11-04. D3D12 client, no official Linux support,
but the Linux path is the same as retail: Battle.net under Wine/Proton with
DXVK/vkd3d-proton. Select the API with `SET GxApi "D3D11"|"D3D12"` in
`<edition>/WTF/Config.wtf` or `-d3d11`/`-d3d12`; D3D11 is the mature path.

**Beta bugs were the client, not Linux.** Build 69913 hung the GPU on world entry
(all NVIDIA generations, D3D11 and D3D12, also AMD/Windows and macOS): the Global
Illumination probe-update compute shader read its loop count from a constant buffer
that was not yet valid on the first dispatch, so it never terminated
([analysis](https://us.forums.blizzard.com/en/wow/t/linuxnvidia-forever-gi-secondary-lighting-gpu-hang-xid-109-cause-isolated-shader-override-workaround/2359917)).
The hangs were reproduced on an RTX 3050 Ti laptop with an AMD iGPU, where 69977
was also verified to fix them **[verified]**; the 2026-09-24 build fixed a
session-long memory leak, and by **1.60.1.70170** the game runs smoother than ever.
Driver flavour (open vs proprietary) and power tweaks made no difference. The other cost was
a 138 % `RenderScale` stored after a monitor sleep (see
[troubleshooting](troubleshooting.md)).

## 6. Environment quick reference

| Variable | Typical value | Purpose |
|---|---|---|
| `WINE_SIMULATE_WRITECOPY`, `WINEDLLOVERRIDES` | `1`, `locationapi=d` | Battle.net CEF fixes |
| `WINEPREFIX`, `GAMEID`, `PROTONPATH` | see §1 | prefix, umu identity, runner |
| `PROTON_USE_NTSYNC` / `PROTON_NO_ESYNC` / `PROTON_NO_FSYNC` | `1` | select a sync primitive |
| `PROTON_ENABLE_NVAPI` | `1` | NVAPI/DLSS shim |
| `DXVK_FILTER_DEVICE_NAME` / `VKD3D_FILTER_DEVICE_NAME` | `"AMD Radeon"` | force a GPU |
| `DXVK_HUD`, `MANGOHUD`, `PROTON_LOG` | `fps,devinfo`, `1`, `1` | overlays and logging |

Put any of these under `[env]` in `config.toml` to apply them to the whole Wine session.

## Sources

[Wine (Arch Wiki)](https://wiki.archlinux.org/title/Wine) ·
[Proton](https://github.com/ValveSoftware/Proton) ·
[GE-Proton](https://github.com/GloriousEggroll/proton-ge-custom) ·
[Proton-CachyOS](https://github.com/CachyOS/proton-cachyos) ·
[umu-launcher](https://github.com/Open-Wine-Components/umu-launcher) ·
[DXVK](https://github.com/doitsujin/dxvk) ·
[vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton) ·
[ntsync](https://docs.kernel.org/userspace-api/ntsync.html) ·
[CEF write-copy analysis](https://github.com/wiesson/diablo4-on-mac/blob/main/docs/technical-notes.md) ·
[Lutris Battle.net guide](https://github.com/lutris/docs/blob/master/Battle.Net.md) ·
[wowdev.wiki Agent](https://wowdev.wiki/Agent) ·
[Proton #10157](https://github.com/ValveSoftware/Proton/issues/10157) ·
[vkd3d-proton #3304](https://github.com/HansKristian-Work/vkd3d-proton/issues/3304) ·
[69977 blue post](https://us.forums.blizzard.com/en/wow/t/beta-client-update-september-22/2358655) ·
[PCGamingWiki anti-cheat](https://www.pcgamingwiki.com/wiki/Anti-cheat_middleware)
