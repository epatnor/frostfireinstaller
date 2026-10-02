# Troubleshooting

`frostfireinstaller` keeps the Battle.net client healthy; problems **inside a game**
are usually Wine/Proton/graphics issues. The app checks for you: a warning strip
appears when a check fails, and the full report is under
*Settings → Diagnostics → System check* and in `frostfireinstaller doctor`
(umu, Proton, Vulkan, disk, prefix filesystem, hybrid GPU, NVIDIA driver and recent
`NVRM: Xid` faults, performance tools, runner).

## Logs

- App logs: `~/.local/state/frostfireinstaller/logs` (GUI: *Settings → Paths → View logs*).
- Battle.net client: `<prefix>/drive_c/users/*/AppData/Local/Battle.net/Logs/battle.net-*.log`.
- Game crash dumps: `<game dir>/Errors/*.txt`; GPU/memory data in `<edition>/Logs/gx.log`.

## Gamescope strobes the whole screen — NVIDIA + Wayland **[verified]**

> **Photosensitivity hazard.** On the reference machine (driver 615.71.09 open
> module, KDE Wayland) enabling **Gamescope** made the display strobe on launch.

Get out: `Alt+F4`, then `pkill -f gamescope`. Stop it recurring — killing the
process does not change the setting. Turn the switch off in *Settings →
Performance*, or edit the file (the GUI picks it up when its window regains focus):

```bash
sed -i 's/^gamescope = true/gamescope = false/' ~/.config/frostfireinstaller/config.toml
```

Cause: nesting gamescope in a Wayland session on NVIDIA can collapse presentation
against the outer compositor; `gamescope_force_fullscreen` makes it worse. The
switch now warns on this combination. For window-geometry problems prefer a **KWin
window rule** (start by forcing only the screen); it adds nothing to the
presentation path.

## Game window returns at the wrong size or monitor

Usually after the monitor slept mid-session: DPMS off + KDE re-probe changes the
screen geometry, a borderless window follows, and WoW persists the result to
`Config.wtf`. Fix the cause with **Performance → Keep awake while playing**
(`inhibit_idle`); verify while the game runs — two processes mean the lock is held,
none means the sidecar did not start (look for `idle inhibitor started` in the log):

```bash
pgrep -a -f "systemd-inhibit|kde-inhibit"
```

Then, with WoW **closed**, fix the stored keys in `<edition>/WTF/Config.wtf`:
`GxMonitor` (output index, unstable), `GxMaximize` (`1` follows geometry),
`RenderScale` (should be `1.0`), `GxWindowedResolution`/`GxFullscreenResolution`.
**Edit just these keys** — regenerating the file loses the narration keys below.

## WoW: Forever

**`ERROR #135` — narration assert at the login screen.**
`ASSERTSAFE(m_platformInterface != nullptr)` in `VoiceSpeakManager.cpp` (the line
number varies by build — match on text and file). It is the new text-to-speech
subsystem, fires every ~1.7 s even with narration disabled, and is a soft assert:
dismiss it. Keep these keys in `<edition>/WTF/Config.wtf`; they suppress the dialog,
the difference between a nuisance and an unusable login screen:

```
SET showScreenNarrationDialog "0"
SET accessibilityScreenNarrationEnabled "0"
```

Resetting `Config.wtf` drops them (a regenerated file once produced six asserts in
13 s and a fatal `BC_ASSERT(result == WAIT_OBJECT_0)`). Re-add them if you regenerate.

**`ERROR #109` / `Xid 109` GPU hang — fixed.** Build 1.60.1.69913 had a client bug
(an unbounded Global Illumination compute shader, hitting AMD/Windows and macOS too —
not the driver, Proton or your setup). **Build 69977 (2026-09-22) fixes it**, and the
2026-09-24 build fixed a separate memory leak that caused progressive FPS/VRAM
decline. Just update the game. On an older build: set Secondary Lighting to *Fair*,
lower Global Illumination/Volumetric Fog, try DirectX 11, or run on the integrated
GPU (*Settings → Graphics → Integrated*).

## Game freezes — `ERROR #109 (0x8510006d)` on D3D12

Symptom: window freezes, crash file shows `dxgi.dll`/`d3d12core.dll` with `GxApi D3D12`.
The vkd3d-proton path hangs; switch to **D3D11** (DXVK): in game *System → Graphics →
Graphics API*, or `SET GxApi "D3D11"` in `<edition>/WTF/Config.wtf`, or launch with
`-d3d11`. The most common fix for Blizzard titles on Linux.

## NVIDIA `Xid ... 109` / `CTX SWITCH TIMEOUT` (other titles or old builds)

```bash
journalctl -k | grep -i nvrm
```

Common on hybrid laptops with NVIDIA's open modules; changing Proton or lowering
settings usually does not help. In order:

1. **GPU persistence** (reversible, in the warning dialog): `systemctl enable --now nvidia-persistenced`.
2. **Disable runtime power management:** `sudo sh -c 'echo on > /sys/bus/pci/devices/0000:01:00.0/power/control'`;
   persist with `options nvidia NVreg_DynamicPowerManagement=0x00` in `/etc/modprobe.d/`.
3. **PCIe ASPM:** `sudo sh -c 'echo performance > /sys/module/pcie_aspm/parameters/policy'`;
   persist with kernel arg `pcie_aspm.policy=performance`.
4. **Update the driver** (`rpm-ostree upgrade` on Bazzite). Switching from open to
   proprietary did not help in our tests.
5. **Run on the integrated GPU** (enough for WoW): *Settings → Graphics*, or
   `[env] DXVK_FILTER_DEVICE_NAME = "AMD Radeon"` in `config.toml` (a substring from
   `vulkaninfo --summary`). Rendering on the GPU that drives the panel also avoids the
   cross-GPU (PRIME) copy.

## Slowdown over a session = VRAM pressure

`gx.log` "Periodic Gpu Status Report" shows `Mem Budget` filling while clocks and
temperature stay healthy, and the kernel logs `NV_ERR_NO_MEMORY`. A 4 GB GPU leaves
~3.3 GB for the game. Run on the iGPU, close the Battle.net window after the game
starts (~0.4 GB), cap FPS/render scale, and raise the background cap with
`SET maxFPSBK "60"` in `Config.wtf`. `/reload` does not touch GPU resources.

## No Proton build found

umu downloads **UMU-Proton** on first launch. If `umu-run` is missing too, install
`umu-launcher` first, or install GE-Proton/UMU-Proton with ProtonPlus. `doctor`
shows which case you are in.

## Vulkan / old GPU

Battle.net and DXVK are **32-bit** and need a 32-bit Vulkan loader; games need
Vulkan 1.3+ (vkd3d-proton). Very old GPUs (Intel HD 6000, GCN 1, Maxwell) may start
the launcher but not the game — Blizzard's hardware floor. `doctor` warns when
Vulkan is missing, too old, software-only (llvmpipe) or the 32-bit loader is absent.

## Other freezes or low performance

One at a time: turn off MangoHud; delete `vkd3d-proton.cache*`/DXVK caches (with the
game closed); try another runner; toggle GameMode/Gamescope off;
`sudo sysctl vm.max_map_count=1048576`; update Mesa/NVIDIA.

## Battle.net launcher: blank window, spinning gear, stuck login

The two required fixes (`WINE_SIMULATE_WRITECOPY=1`, `WINEDLLOVERRIDES=locationapi=d`)
are already applied. Use **Repair** (stops the client, clears CEF/cache, relaunches);
a full **Reinstall** with *Keep games* keeps your games. A "bad gateway" while
downloading the installer is a transient 5xx and is retried automatically.

## Resetting

Config: `~/.config/frostfireinstaller/config.toml`. Cached installer:
`~/Games/battlenet/Battle.net-Setup.exe`. Full reset:
`frostfireinstaller remove --purge --purge-installer`, then start again.
