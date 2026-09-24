# Troubleshooting

Practical fixes for the most common failures. `frostfireinstaller` keeps the
Battle.net client healthy; problems that happen **inside a game** (after you press
Play) are usually Wine/Proton/graphics issues, not the installer.

> **The app checks for you.** A **recommendation strip** appears under the
> Battle.net band when a check fails, with copy-ready commands. The full report —
> every check, including the ones that pass — is under
> **Avancerat → Diagnostik → Systemkontroll** and in `frostfireinstaller doctor`.
> It covers: `umu-run`, Proton builds, free disk space, the prefix filesystem
> (NTFS/exFAT warning), hybrid GPUs, the NVIDIA driver/module and any recent
> `NVRM: Xid` / `NV_ERR_NO_MEMORY` faults, missing performance tools and the
> runner.

## Where the logs are

- App run/installation logs: `~/.local/state/frostfireinstaller/logs`
  (also in the GUI: *Advanced → Paths → **View logs***).
- Battle.net client log:
  `<prefix>/drive_c/users/*/AppData/Local/Battle.net/Logs/battle.net-*.log`.
- Per-game crash dumps: `<game dir>/Errors/*.txt` (e.g. `_retail_/Errors/`).
- `frostfireinstaller doctor` prints the environment and current status.

## Known bugs in World of Warcraft: Forever

> **Resolved in build 69977 (2026-09-22).** The `ERROR #109` / NVIDIA `Xid 109`
> GPU hang below was a **client regression in build 69913**, caused by an
> unbounded compute shader (the **Global Illumination probe update**) whose loop
> count is read from a not-yet-initialised constant buffer on its first dispatch.
> It was **not** the driver, Proton or your setup — the same setting also times
> out drivers on AMD/Windows and freezes macOS. Blizzard's 69977 build fixes it
> (verified on the reference machine: a 2026-09-24 play session on the NVIDIA
> RTX 3050 Ti with **zero** `Xid`). The notes are kept for older builds and for
> the two issues that remain (a session-long FPS degradation and the soft
> narration assert). Sources: [Blizzard #2359917], [gist: fx], [blue post 69977].

The 69913 beta had **two independent bugs**. They looked alarming but were not
caused by your GPU choice, the installer, or an outdated driver. Sources:
[Blizzard forum #2353584], [Proton #10157], [vkd3d-proton #3304].

[Blizzard forum #2353584]: https://us.forums.blizzard.com/en/wow/t/wowf-beta-69913-hard-gpu-hang-entering-world-map-2991-client-deadlock-in-device-lost-recovery-error-109/2353584
[Blizzard #2359917]: https://us.forums.blizzard.com/en/wow/t/linuxnvidia-forever-gi-secondary-lighting-gpu-hang-xid-109-cause-isolated-shader-override-workaround/2359917
[gist: fx]: https://gist.github.com/fx/88cf5be8bed8e9ce761e26e183b0ba90
[blue post 69977]: https://us.forums.blizzard.com/en/wow/t/beta-client-update-september-22/2358655
[Proton #10157]: https://github.com/ValveSoftware/Proton/issues/10157
[vkd3d-proton #3304]: https://github.com/HansKristian-Work/vkd3d-proton/issues/3304

### 1. `ERROR #135` — narration/voice assert at the login screen

```
ASSERTSAFE(m_platformInterface != nullptr)  VoiceSpeakManager.cpp:204
ERROR #135    Lua: StopSpeakingText -> NarrateCurrentScreen ("Login Screen")
GxRestarts: 0   GxDeviceLostCount: 0
```

This is the **new narration / text-to-speech subsystem** — not graphics, and
unaffected by the GPU you run on. It fires repeatedly at the login/character
screen (~every 1.7 s) **even with screen narration disabled**, on both builds.
It is a soft assert (`ASSERTSAFE`), so you can dismiss the dialog and play on;
the dialog is a separate Blizzard Error process and may linger after you quit.
There is no client-side fix yet — this is usually the dismissible error seen at
character select.

### 2. `ERROR #109` / `Xid 109` — GPU hang on world entry (regression, fixed in 69977)

Build **69913** regressed. ~11–15 s after the loading screen reaches 100 %, the
GPU queue hangs (`NVRM: Xid ... 109 CTX SWITCH TIMEOUT`), and the client's
device-lost recovery then **deadlocks in `WaitForFence`**, so the freeze watchdog
kills the process. Build **69893 was stable**. Reported on NVIDIA GPUs from a
GTX 1070 to an RTX 4090 and on **both** D3D11 and D3D12 — a **client
regression, not an outdated driver**.

The root cause was isolated to one **compute shader** (the GI probe update) whose
unbounded loops read an invalid count on their first dispatch; it also times out
drivers on AMD/Windows and freezes macOS. Build **69977 fixes it**. The
workarounds below only apply if you are still on an older build.

Workarounds, in order:

1. **Set Secondary Lighting to `Fair`** (Options → Graphics) — reported to let
   you load in with everything else on high/ultra.
2. Lower **Global Illumination** and **Volumetric Fog** as well.
3. Try **DirectX 11** (`SET GxApi "D3D11"` / `-d3d11`) and/or the lowest preset.
4. New characters often load where existing ones hang (zone/character dependent).

A conservative, verified baseline (matches the reference machine's config; the
quality sliders are stored one lower than the in-game label):

| Setting | In-game | CVar |
|---|---|---|
| Graphics API | DirectX 11 | `GxApi "D3D11"` |
| Secondary Lighting | Fair | (no explicit CVar; set in UI) |
| Global Illumination | Fair | `giQuality "1"` |
| Volumetric Fog | Low | `volumeFogLevel "1"` |
| Compute Effects | Low | `graphicsComputeEffects "1"` |
| SSAO / Depth Effects | Disabled | `graphicsSSAO "0"` / `graphicsDepthEffects "0"` |
| Shadow Quality | Low | `graphicsShadowQuality "0"` |
| Base Game Quality | 3 | `graphicsQuality "2"` |
| Max Background FPS | 60 (raise from 30) | `maxFPSBK "60"` |

> On the reference machine **Secondary Lighting is already Fair and the API
> already DirectX 11**, so that workaround alone does not prevent the hang there —
> the reliable escape remains the iGPU fallback (or waiting for a Blizzard fix).

> The client misparses the NVIDIA driver version (`Device Lost on NVIDIA driver
> version 999.99`), which disables Aftermath GPU crash dumps — so no dump is
> captured for these hangs.

## Game freezes — `ERROR #109 (0x8510006d) A thread has become unresponsive`

**Symptom:** the game window is up (often still rendering), then freezes; the
WoW error dialog reports `ERROR #109`, `Soft Lock`, and the crash file's stack
shows `dxgi.dll` / `d3d12core.dll` with `<GxApi> D3D12`.

**Cause:** the **D3D12 path (VKD3D-Proton) hangs**. Switch the game to **D3D11**
(DXVK), the more mature path:

- In game: **System → Graphics → Graphics API → DirectX 11**.
- Or edit the game's `Config.wtf` (`<game dir>/WTF/Config.wtf`) and set
  `SET GxApi "D3D11"` (back the file up first).
- Or launch with `-d3d11` (Battle.net → game → Options → Additional command line
  arguments).

This is the single most common fix for Blizzard titles on Linux.

## GPU hang — `NVRM: Xid ... 109` / `CTX SWITCH TIMEOUT`

> **Note (2026-09-24):** for WoW: Forever this was the build-69913 shader bug and
> is **fixed in build 69977** — update the game first. The steps below remain
> useful for any *other* title or older build that shows the same kernel fault.

**Symptom:** the game freezes regardless of D3D11/D3D12, and

```bash
journalctl -k | grep -i nvrm
# NVRM: Xid (PCI:0000:01:00): 109, name=WowB.exe, errorString CTX SWITCH TIMEOUT
```

The crash stack sits in `dxgi.dll` (the present path): this is a **GPU driver
hang**, not the game. It is common on hybrid/Optimus laptops with the NVIDIA
**open** kernel modules.

> Changing the Proton runner or lowering the in-game graphics settings usually
> does **not** help here — the fault is below them (it happens with both D3D11 and
> D3D12, on any runner, and can be intermittent). Focus on the driver.

> The app surfaces this automatically: the **recommendation strip** → **Visa**
> shows the steps below and can toggle the reversible one for you. The app never
> makes large system changes itself — the rest are copy-ready commands.

1. **Keep the GPU initialised (reversible, in-app):** in the recommendation
   dialog, press **Aktivera GPU-persistens** (it runs
   `systemctl enable --now nvidia-persistenced`, with your desktop's
   authorisation prompt). Press again to turn it off.
2. **Keep the discrete GPU awake** (disable runtime power management). Test it
   live:

   ```bash
   sudo sh -c 'echo on > /sys/bus/pci/devices/0000:01:00.0/power/control'
   ```

   Make it persistent with `options nvidia NVreg_DynamicPowerManagement=0x00` in
   `/etc/modprobe.d/`.
3. **PCIe ASPM:** force performance mode and test:

   ```bash
   sudo sh -c 'echo performance > /sys/module/pcie_aspm/parameters/policy'
   ```

   Make it persistent with the kernel argument `pcie_aspm.policy=performance`.
4. **Update or switch the driver:** on Bazzite run `rpm-ostree upgrade` and
   reboot; if it persists, rebase from the open modules
   (`bazzite-nvidia-open`) to the proprietary `bazzite-nvidia` image.

   > **Tested on the reference machine (2026-09-22):** rebasing to the
   > **proprietary** driver (`kmod-nvidia-580.178.04`, replacing
   > `kmod-nvidia-open`) did **not** fix `Xid 109` — two fresh
   > `CTX SWITCH TIMEOUT` faults on `WowB.exe` appeared within minutes of the
   > first launch. This confirmed the driver type was **not** the cause; the
   > real cause was the 69913 shader regression (fixed in **69977**). The iGPU
   > (step 5) was the working fallback in the meantime.
5. **Last resort — run on the integrated GPU** (enough for WoW). Add to
   `~/.config/frostfireinstaller/config.toml`:

   ```toml
   [env]
   DXVK_FILTER_DEVICE_NAME = "AMD Radeon"
   ```

   Match a substring of a device name from `vulkaninfo --summary`. Everything in
   `[env]` is passed to the Wine session (umu-run → Battle.net → games).

## "It gets worse the longer I play" — two separate problems

Field data (Bazzite, RTX 3050 Ti Laptop, GE-Proton11-7, **already on D3D11**)
shows two *independent* failure modes that are easy to confuse. Inspect
`<edition>/Logs/gx.log` for both.

### A. `ERROR #109` is a *symptom* of NVIDIA `Xid 109` (`CTX SWITCH TIMEOUT`)

> **Superseded for WoW: Forever (2026-09-24).** The PRIME-path explanation below
> was the best theory on build 69913. The actual cause turned out to be a
> **client shader bug** (the GI probe compute shader), and it was **fixed in
> build 69977** — it also affected AMD/Windows and macOS. Treat this section as
> historical for Forever; it may still apply to other titles.

The game's render thread blocks in `dxgi.dll` waiting for a wedged GPU context;
after 20 s WoW's watchdog raises `ERROR #109` / `Soft Lock`. Confirm with:

```bash
journalctl -k | grep -i nvrm
# NVRM: Xid (PCI:0000:01:00): 109, name=WowB.exe, errorString CTX SWITCH TIMEOUT
```

On hybrid laptops the likely root cause is the **cross-GPU (PRIME) path**: the
panel is wired to the *integrated* GPU (`/sys/class/drm/card*-eDP-1` is
`connected`), while the game picks the *discrete* one (`gx.log`:
`Choosing gpu with monitor attached: "NVIDIA ..."`). Every frame is then copied
between GPUs, and on Wayland that path hangs the NVIDIA driver; the device is
removed and the 20 s watchdog fires. The crashes are **early (1–6 min) and at low
memory (13–22 %)** — this is not memory pressure and not the power profile.

**Fix (reversible, no privileges):** run the game on the integrated GPU — the
same one that drives the panel. Choose **Integrated** under
**Advanced → Graphics** (Auto / NVIDIA / Integrated), or set it yourself:

```toml
# ~/.config/frostfireinstaller/config.toml
[env]
DXVK_FILTER_DEVICE_NAME = "AMD Radeon"
```

The game **often recovers by itself** by re-creating its D3D11 device — `gx.log`
shows `Device Destroy Successful` → `Dx11 Device Create Successful`. That is why
the error can be dismissed and play resumed, and why the error dialog can linger
after the game exits (it is a separate Blizzard Error process).

> Optional, only if you want to keep using the discrete GPU: keeping it
> initialised (`nvidia-persistenced` / `power/control=on`) can reduce
> idle-triggered timeouts. It is **not required**, goes against a low-power/quiet
> setup, and is your choice — the app never changes it for you.

### B. Slowdown to a slideshow is **VRAM pressure, not heat**

`gx.log` "Periodic Gpu Status Report" shows the budget filling while clocks and
temperature stay healthy:

```
Mem Budget: 0.6GB / 3.3GB (17.6%)  Freq:1.49GHz Temp:53C
Mem Budget: 2.0GB / 3.3GB (62.1%)  Freq:1.93GHz Temp:70C
Mem Budget: 2.7GB / 3.3GB (84.4%)  Freq:1.94GHz Temp:67C
```

The kernel logs the allocation failure:

```bash
journalctl -k | grep -i 'NV_ERR_NO_MEMORY\|_memdescAllocInternal'
# NVRM: nvCheckOkFailedNoLog: ... Out of memory [NV_ERR_NO_MEMORY] ... _memdescAllocInternal
```

A 4 GB laptop GPU minus the desktop and Battle.net (≈0.4 GB) leaves only
~3.3 GB for the game. As the budget fills, DXVK evicts/streams and performance
degrades progressively. **`/reload` will not help** — it reloads the Lua UI, not
GPU resources.

Reduce pressure (easiest first):

- **Run WoW on the iGPU** (ample system RAM, no 4 GB wall, no `Xid`): in
  `~/.config/frostfireinstaller/config.toml` set
  `[env] DXVK_FILTER_DEVICE_NAME = "AMD Radeon"`.
- Close the **Battle.net launcher** window after the game has started (frees
  ~0.4 GB VRAM).
- Cap the frame rate and lower render scale / textures.
- **Raise the background FPS cap** so idling at character select does not drop
  the client into a low-power state: add `SET maxFPSBK "60"` to
  `<edition>/WTF/Config.wtf` (remove the line to restore).

## No Proton build found

If no Proton build is in a `compatibilitytools.d` directory, `frostfireinstaller`
asks `umu-launcher` to download **UMU-Proton** on first launch. If `umu-run` is
missing too, install `umu-launcher` first (it fetches Proton for you), or install
GE-Proton/UMU-Proton with ProtonPlus. `frostfireinstaller doctor` shows which case
you are in.

## Vulkan / old or weak GPU

Battle.net's launcher and DXVK are **32-bit** and need a 32-bit Vulkan loader; the
games need **Vulkan 1.3+** (vkd3d-proton) or DXVK. On very old integrated
graphics (Intel HD 6000, GCN 1, Maxwell) the launcher may start but the game will
fail — that is Blizzard's hardware floor, not the tool. `doctor` warns when Vulkan
is missing, too old, software-only (llvmpipe), or the 32-bit loader is absent, and
lists the packages to install.

## Other freezes or low performance

Try these one at a time:

- **Overlays:** turn off **MangoHud** in the app to rule out the overlay.
- **Shader cache:** delete the game's `vkd3d-proton.cache*` / DXVK cache and let
  it rebuild.
- **Runner:** try a different Proton build in the app's **Runner** section
  (e.g. Proton-CachyOS or UMU-Proton instead of GE-Proton).
- **GameMode / Gamescope:** toggle them off to isolate the wrapper.
- **`vm.max_map_count`:** some titles need a higher limit
  (`sudo sysctl vm.max_map_count=1048576`).
- **Driver:** make sure your GPU driver (Mesa/NVIDIA) is current.

## Battle.net launcher: blank window, spinning gear or stuck login

The launcher needs two Wine fixes, which `frostfireinstaller` already applies:

- `WINE_SIMULATE_WRITECOPY=1`
- `WINEDLLOVERRIDES=locationapi=d`

If the client still misbehaves, use **Reparera** (stops the client, clears
CEF/cache and relaunches). A full **Reinstall** (with *Keep games*) keeps
your games.

## "bad gateway" while downloading the installer

A transient 5xx from Blizzard's CDN; the app retries automatically. If it keeps
failing, check your network/DNS and try again.

## Resetting

- Config: `~/.config/frostfireinstaller/config.toml`.
- Cached installer: `~/Games/battlenet/Battle.net-Setup.exe` (drop it with the
  *Also the installer* checkbox or `--purge-installer`).
- Full reset: `frostfireinstaller remove --purge --purge-installer`, then start
  again.
