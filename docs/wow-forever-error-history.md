# WoW: Forever — observed error history (build 69913)

A record of every crash/error the game has produced on the reference machine, for
our own tracking. **Not** a report to Blizzard/NVIDIA — just evidence we can point
at and reason from. Regenerate it any time with the snippet at the bottom.

| Field | Value |
|---|---|
| Game | World of Warcraft: Forever (Beta), build **1.60.1.69913** (`wow_classic_beta`, `WowB.exe`) |
| Machine | Lenovo IdeaPad Gaming 3 15ACH6 — Bazzite, Ryzen 5 5600H, **RTX 3050 Ti Laptop (4 GB)** + AMD Cezanne iGPU |
| Backend | umu-launcher 1.4.4 + GE-Proton11-7 |
| Window | 2026-09-21 21:45 → 2026-09-22 22:45 |
| Driver | Switched to **proprietary** `kmod-nvidia-580.178.04` before the 22:43 faults |
| Reports | **17** `.txt` + `.dmp` in `_classic_beta_/Errors/` (plus 2 kernel-only Xid after the driver switch, see below) |

## Summary

| Category | Count | API | Kernel `Xid` |
|---|---|---|---|
| `ERROR #109` (`0x8510006d`) — GPU hang | **10** | 9× D3D11, 1× D3D12 | **yes** (Xid 109) |
| `ASSERTSAFE(m_platformInterface != nullptr)` — narration/TTS | 6 | D3D12 | no |
| `ASSERTSAFES(IsArmor20())` — soft assert | 1 | D3D11 | (Xid at same second) |

The GPU hang (`#109`) is the real problem; the asserts are separate and soft
(`ASSERTSAFE`), so they can be dismissed. See
[`docs/troubleshooting.md`](troubleshooting.md) → *Known bugs in WoW: Forever*.

## Every report

| Time (local) | Error | API | App up | Frame | GxRestarts / DeviceLost |
|---|---|---|---|---|---|
| 2026-09-21 21:45:49 | narration assert | D3D12 | 13 s | 1 | 0 / 0 |
| 2026-09-21 21:45:51 | narration assert | D3D12 | 15 s | 1 | 0 / 0 |
| 2026-09-21 21:45:53 | narration assert | D3D12 | 17 s | 1 | 0 / 0 |
| 2026-09-21 21:46:01 | narration assert | D3D12 | 25 s | 335 | 0 / 0 |
| 2026-09-21 21:46:03 | narration assert | D3D12 | 27 s | 335 | 0 / 0 |
| 2026-09-21 21:46:04 | narration assert | D3D12 | 28 s | 335 | 0 / 0 |
| 2026-09-21 21:47:27 | **`ERROR #109`** | D3D12 | 1 m 51 s | 24984 | 1 / 1 |
| 2026-09-22 07:20:46 | **`ERROR #109`** | D3D11 | 1 m 11 s | 20097 | 1 / 1 |
| 2026-09-22 09:06:36 | **`ERROR #109`** | D3D11 | 6 m 07 s | 39525 | 1 / 1 |
| 2026-09-22 10:55:18 | **`ERROR #109`** | D3D11 | 1 m 20 s | 17979 | 1 / 1 |
| 2026-09-22 13:40:33 | **`ERROR #109`** | D3D11 | 2 m 41 s | 25394 | 1 / 1 |
| 2026-09-22 16:02:39 | `ASSERTSAFES(IsArmor20())` | D3D11 | 0 m 54 s | 21139 | 0 / 1 |
| 2026-09-22 16:03:02 | **`ERROR #109`** | D3D11 | 1 m 17 s | 21139 | 1 / 1 |
| 2026-09-22 16:04:52 | **`ERROR #109`** | D3D11 | 1 m 18 s | 21175 | 1 / 1 |
| 2026-09-22 16:50:30 | **`ERROR #109`** | D3D11 | 2 m 51 s | 25559 | 1 / 1 |
| 2026-09-22 21:45:56 | **`ERROR #109`** | D3D11 | 1 m 08 s | 20403 | 1 / 1 |
| 2026-09-22 22:14:51 | **`ERROR #109`** | D3D11 | 7 m 14 s | 30153 | **2** / 1 |

## Kernel `NVRM: Xid` correlation

Every `ERROR #109` is preceded (within ~1 minute) by a matching kernel Xid — the
game watchdog fires ~20 s after the driver reports the hang:

```
NVRM: Xid (PCI:0000:01:00): 109, name=WowB.exe, errorString CTX SWITCH TIMEOUT, Info 0x...
```

| Kernel time | Channel | Info | pid |
|---|---|---|---|
| 2026-09-21 21:46:47 | 0x08 | 0x3c007 | 74557 |
| 2026-09-22 07:20:24 | 0x08 | 0x3c007 | 109390 |
| 2026-09-22 07:21:38 | 0x08 | 0x38007 | 109390 |
| 2026-09-22 09:06:13 | 0x10 | 0x3c008 | 117105 |
| 2026-09-22 10:54:55 | 0x10 | 0x38008 | 126373 |
| 2026-09-22 13:40:12 | 0x08 | 0x3c007 | 137396 |
| 2026-09-22 16:02:38 | 0x08 | 0x78007 | 146684 |
| 2026-09-22 16:04:31 | 0x08 | 0x3c007 | 147149 |
| 2026-09-22 16:50:08 | 0x08 | 0x3c007 | 151015 |
| 2026-09-22 21:45:34 | 0x08 | 0x78007 | 170206 |
| 2026-09-22 21:46:48 | 0x08 | 0x38007 | 170206 |
| 2026-09-22 22:14:29 | 0x08 | 0x3c007 | 174415 |
| 2026-09-22 22:43:28 | 0x2b | 0x8c028 | 6393 |
| 2026-09-22 22:45:13 | 0x2b | 0x8c028 | 7869 |

> The last two rows are a **new boot** after rebasing from `kmod-nvidia-open` to
> the **proprietary** `kmod-nvidia-580.178.04`. No game `.txt` was produced in
> that window — only the kernel Xid — but `name=WowB.exe` shows the same fault.
> The proprietary driver therefore does **not** prevent `Xid 109` on this machine.

## Observations

- **The hang is API-independent**: it happens on **D3D11/DXVK** (9 of 10) as well
  as D3D12/vkd3d — matching [Proton #10157] and [vkd3d-proton #3304].
- **Not memory, not heat, not power**: crashes occur from 54 s to 7 m 14 s in, at
  frames 18k–40k, with `Memory.HighLoad: No` and healthy clocks/temps.
- **The workaround did not help here**: the 22:14 crash ran on **D3D11** with
  **Secondary Lighting = Fair** — the setting the community found helped on
  Windows. So on this machine the reliable escape remains the **iGPU** (the
  `frostfireinstaller` *Avancerat → Grafik* selector) until Blizzard fixes 69913.
- **Device-lost recovery is broken** (Blizzard's own secondary issue): the 22:14
  run shows `GxRestarts: 2` — the device was lost, recovered, lost again, then
  the recovery path deadlocked in `WaitForFence` and the watchdog killed it.
- **`Xid 109` is recoverable in itself.** The driver resets the hung channel and
  the game recreates its device (`GxRestart` → `Dx11 Device Create Successful`).
  That is why the game sometimes **keeps running with an Xid in the log** and the
  `#109` dialog lingering behind it. It only becomes a hard hang when Blizzard's
  recovery path deadlocks — same fault, two outcomes. This is also why the crash
  is intermittent and (per the upstream reports) zone/terrain dependent.
- **The driver type is not the cause**: after switching from the **open** to the
  **proprietary** NVIDIA module, `Xid 109` returned on the very first launch
  (22:43/22:45). Combined with the earlier data, this points at the **69913
  client regression** on the **cross-GPU (PRIME) path**, not the module choice.
- **The iGPU path is stable**: running the game on the **AMD Radeon** iGPU (the
  one wired to the panel) via `frostfireinstaller`'s *Avancerat → Grafik* selector
  works well. That remains the recommended workaround until Blizzard (or NVIDIA)
  ships a fix.
- **The asserts are separate and soft**: 6× narration (`#135`) on D3D12 (21 Sep)
  and 1× `IsArmor20()`; none correlate with a GPU fault.

## Regenerating this table

```bash
D=~/Games/battlenet/prefix/drive_c/Program\ Files\ \(x86\)/World\ of\ Warcraft/_classic_beta_/Errors
for f in "$D"/*.txt; do
  printf '%s | %s | %s | %s\n' \
    "$(basename "$f")" \
    "$(grep -am1 -E 'Error:' "$f")" \
    "$(grep -am1 -E '<CVar.GxApi>|<GxApi>' "$f")" \
    "$(grep -am1 'App Up Time:' "$f")"
done
journalctl -k --no-pager | grep -a 'NVRM: Xid'
```

## Sources

[Proton #10157]: https://github.com/ValveSoftware/Proton/issues/10157
[vkd3d-proton #3304]: https://github.com/HansKristian-Work/vkd3d-proton/issues/3304
- Blizzard forum #2353584: https://us.forums.blizzard.com/en/wow/t/wowf-beta-69913-hard-gpu-hang-entering-world-map-2991-client-deadlock-in-device-lost-recovery-error-109/2353584
