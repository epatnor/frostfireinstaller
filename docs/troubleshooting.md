# Troubleshooting

`frostfireinstaller` keeps the Battle.net client healthy. The app checks for you:
a warning strip appears when a check fails, and the full report is under
*Settings → Diagnostics → System check* and in `frostfireinstaller doctor`
(umu, Proton, Vulkan, disk, prefix filesystem, GPU driver and recent `NVRM: Xid`
faults, WoW render scale, performance tools, runner).

> **Lesson learned.** Weeks of WoW: Forever beta stutter, lag and GPU hangs on the
> reference machine looked like Linux/Proton/driver problems. They were not: the
> game's own patches fixed them, and the rest was a 138 % render scale left behind
> by a monitor that slept mid-session (below). **Update the game and check its
> settings before tuning the system.**

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
`GxWindowedResolution`/`GxFullscreenResolution`, and **`RenderScale`** — it should
be `1`. A bogus resolution can leave an odd value such as `1.383333`: the game then
renders ~1.9x the pixels and scales them down, a large hidden performance cost. The
system check flags any render scale above 100 %. **Edit just these keys** —
regenerating the file loses the narration keys below.

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

**Performance and GPU hangs — fixed by Blizzard.** The beta's `ERROR #109` /
NVIDIA `Xid 109` hang (build 1.60.1.69913, an unbounded Global Illumination
shader that also hit AMD/Windows and macOS), its session-long memory leak and the
general stutter were client bugs, fixed in later builds (69977, the 2026-09-24
build and on up to **70170**). Not Linux, Proton or the driver: switching NVIDIA
driver flavours and power-management tweaks did not help, and running on the
integrated GPU only sidestepped the hang; the game updates fixed it. Update the
game first.

## Game freezes — `ERROR #109 (0x8510006d)` on D3D12

Symptom: window freezes, crash file shows `dxgi.dll`/`d3d12core.dll` with `GxApi D3D12`.
If an update does not help, try **D3D11** (DXVK, the more mature path): in game
*System → Graphics → Graphics API*, or `SET GxApi "D3D11"` in
`<edition>/WTF/Config.wtf`, or launch with `-d3d11`.

## NVIDIA `Xid` / `NV_ERR_NO_MEMORY` in the kernel log

The system check warns when the driver logged a GPU fault this boot
(`journalctl -k -b | grep -i nvrm`). In our experience it is a symptom of a game bug
far more often than of the driver: note which game and build triggered it, update
the game, and keep the driver current (`rpm-ostree upgrade` on Bazzite). Report it
upstream if it persists on the latest build. On a laptop, *Settings → Graphics →
Integrated* is a quick way to tell whether the dedicated GPU path is involved.

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
