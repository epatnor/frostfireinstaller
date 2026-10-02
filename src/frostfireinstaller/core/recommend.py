"""Local, offline system checks and recommendations.

The app cannot know NVIDIA's or Blizzard's release schedule, so it reports what
it *can* see locally: whether the tools exist, where the prefix lives, how much
disk is free, the GPU driver and any recent ``NVRM: Xid`` / ``NV_ERR_NO_MEMORY``
faults in the kernel log, Vulkan support, WoW's render scale, and a Proton runner
suggestion.

Each finding carries copy-ready commands so the user has the tools to act; the
app itself changes nothing on the system. ``collect()`` returns the actionable
findings for the GUI strip; ``report()`` returns every check, including the
passing ones, for the "System check" dialog and ``doctor``.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from . import gpu, proton

# Xid values that usually mean a GPU/driver hang rather than an app bug.
_SERIOUS_XIDS = {"13", "31", "43", "62", "79", "109", "119", "120"}
_MIN_FREE_GB = 15
_LINUX_FSTYPES = {"ext2", "ext3", "ext4", "btrfs", "xfs", "f2fs", "zfs", "tmpfs", "overlay"}

# vkd3d-proton (D3D12) needs Vulkan 1.3; Battle.net is 32-bit and needs a 32-bit loader.
_VULKAN_MIN = (1, 3)
_SOFTWARE_VULKAN = ("llvmpipe", "lavapipe", "swiftshader")

_RENDER_SCALE_RE = re.compile(r'^SET RenderScale "([0-9.]+)"', re.MULTILINE)


@dataclass(slots=True)
class Recommendation:
    id: str
    level: str  # "ok" | "info" | "warn"
    title: str
    detail: str = ""
    action: str = ""
    commands: tuple[str, ...] = field(default_factory=tuple)


def _level_rank(item: Recommendation) -> int:
    return {"warn": 0, "info": 1, "ok": 2}.get(item.level, 3)


def _existing(path: Path) -> Path:
    node = path
    while not node.exists() and node != node.parent:
        node = node.parent
    return node


def _check_vram() -> Recommendation:
    mib = gpu.vram_mib()
    if mib is None:
        return Recommendation("vram", "info", "Video memory could not be read", "")
    gb = mib / 1024
    if mib < 6 * 1024:
        return Recommendation(
            "vram",
            "info",
            f"Low video memory ({gb:.0f} GB)",
            "Modern Blizzard games prefer more; keep texture quality and render scale moderate.",
        )
    return Recommendation("vram", "ok", f"{gb:.0f} GB video memory", "")


def _check_vulkan() -> Recommendation:
    if not shutil.which("vulkaninfo"):
        return Recommendation(
            "vulkan",
            "info",
            "Vulkan could not be checked",
            "Install vulkan-tools to enable this check.",
        )
    versions, names = gpu.vulkan_versions_and_names()
    if not versions:
        return Recommendation(
            "vulkan",
            "warn",
            "No Vulkan device found",
            "Battle.net (32-bit) and the games need a Vulkan-capable driver.",
            "Install a Vulkan driver: Mesa RADV/ANV (AMD/Intel) or the NVIDIA "
            "driver, plus the 32-bit libraries.",
        )
    best = max(versions)
    best_text = ".".join(str(part) for part in best)
    if best < _VULKAN_MIN:
        return Recommendation(
            "vulkan",
            "warn",
            f"Vulkan too old ({best_text})",
            "vkd3d-proton (D3D12) needs Vulkan 1.3; older drivers can fail to run the games.",
            "Update your GPU driver (Mesa or NVIDIA).",
        )
    real = [name for name in names if not any(s in name.lower() for s in _SOFTWARE_VULKAN)]
    if names and not real:
        return Recommendation(
            "vulkan",
            "warn",
            "Only software Vulkan found",
            "Only the software renderer (llvmpipe) is available; games will be "
            "unusably slow or fail to start.",
            "Install a GPU driver with Vulkan support.",
        )
    if not gpu.has_32bit_vulkan():
        return Recommendation(
            "vulkan",
            "warn",
            "32-bit Vulkan loader not found",
            "Battle.net's launcher and DXVK are 32-bit and need a 32-bit Vulkan loader.",
            "Install the 32-bit Vulkan libraries for your GPU (e.g. "
            "lib32-vulkan-radeon, libvulkan1:i386, mesa-vulkan-drivers.i686).",
        )
    return Recommendation("vulkan", "ok", f"Vulkan {best_text} ({len(real)} GPU)", "")


def _check_nvidia() -> list[Recommendation]:
    version, is_open = gpu.nvidia_driver_info()
    if version is None:
        return [
            Recommendation(
                "nvidia",
                "info",
                "No NVIDIA GPU found",
                "Running on AMD/Intel - no NVIDIA-specific checks.",
            )
        ]

    log = gpu.kernel_log()
    serious = sorted({x for x in gpu.XID_RE.findall(log) if x in _SERIOUS_XIDS}, key=int)
    oom = "NV_ERR_NO_MEMORY" in log
    if serious or oom:
        signals = []
        if serious:
            signals.append(f"Xid {', '.join(serious)}")
        if oom:
            signals.append("NV_ERR_NO_MEMORY")
        return [
            Recommendation(
                "nvidia-fault",
                "warn",
                f"NVIDIA GPU fault this boot ({' + '.join(signals)})",
                "The driver reported a GPU hang or a failed allocation. In our "
                "experience this is usually a game client bug that the game's own "
                "patches fix, not Linux or Proton.",
                "Update the game first. If it keeps happening, see docs/troubleshooting.md.",
                commands=("journalctl -k -b | grep -i nvrm   # show the faults",),
            )
        ]
    module = "open kernel module" if is_open else "proprietary module"
    return [
        Recommendation(
            "nvidia-ok",
            "ok",
            f"NVIDIA driver {version} ({module})",
            "No GPU faults in the kernel log this boot.",
        )
    ]


def _check_hybrid_gpu(config: Config) -> Recommendation:
    version, _ = gpu.nvidia_driver_info()
    integrated = gpu.integrated_gpu_name()
    if not (version and integrated):
        return Recommendation("hybrid", "ok", "Single-GPU configuration", "")
    target = {"auto": "auto", "nvidia": "NVIDIA", "integrated": integrated}[
        gpu.gpu_preference(config)
    ]
    return Recommendation(
        "hybrid",
        "ok",
        f"Hybrid GPU: NVIDIA + {integrated}, games on {target}",
        "Choose the GPU under Settings -> Graphics.",
    )


def _find_wow_configs(config: Config) -> list[Path]:
    base = config.prefix / "drive_c" / "Program Files (x86)" / "World of Warcraft"
    if not base.is_dir():
        return []
    return sorted(base.glob("*/WTF/Config.wtf"))


def _render_scale(path: Path) -> float | None:
    try:
        match = _RENDER_SCALE_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    try:
        return float(match.group(1)) if match else None
    except ValueError:
        return None


def _check_render_scale(config: Config) -> Recommendation:
    """Flag a WoW render scale above 100 %.

    WoW can store an odd scale (e.g. 1.38) computed from a bogus resolution after
    the monitor slept mid-session. It then renders ~1.9x the pixels and
    downsamples them - a large, invisible performance cost on a laptop.
    """
    configs = _find_wow_configs(config)
    if not configs:
        return Recommendation("render-scale", "ok", "No WoW installation found", "")
    high = [(path, scale) for path in configs if (scale := _render_scale(path) or 1.0) > 1.01]
    if not high:
        return Recommendation("render-scale", "ok", "WoW render scale at or below 100 %", "")
    path, scale = high[0]
    edition = path.parent.parent.name
    return Recommendation(
        "render-scale",
        "warn",
        f"WoW renders at {scale * 100:.0f} % ({edition})",
        f"The game draws about {scale * scale:.1f}x the pixels of your screen and then "
        "scales them down - a big performance cost for no visible gain. Odd values "
        "such as 138 % usually come from a monitor that slept mid-session.",
        "In game: Options -> Graphics -> Render Scale 100 %. Or, with the game "
        f"closed, set the line below in {path}.",
        commands=('SET RenderScale "1"',),
    )


# --- requirements --------------------------------------------------------
def _check_umu() -> Recommendation:
    if shutil.which("umu-run"):
        return Recommendation("umu", "ok", "umu-launcher found", "")
    return Recommendation(
        "umu",
        "warn",
        "umu-launcher is missing",
        "Without umu-run, Battle.net cannot be started.",
        "Install umu-launcher (available on Bazzite/Fedora and from "
        "Open-Wine-Components). It can also download Proton for you.",
    )


def _check_proton() -> Recommendation:
    builds = proton.all_builds()
    if builds:
        return Recommendation("proton", "ok", f"{len(builds)} Proton builds found", "")
    if shutil.which("umu-run"):
        return Recommendation(
            "proton",
            "info",
            "No local Proton build",
            "umu-launcher will download UMU-Proton automatically on first launch.",
            "Or install GE-Proton/UMU-Proton with ProtonPlus "
            "(https://github.com/Vysp3r/ProtonPlus).",
        )
    return Recommendation(
        "proton",
        "warn",
        "No Proton build and no umu-launcher",
        "Install umu-launcher (it can then fetch UMU-Proton automatically), or a "
        "Proton runner in a compatibilitytools.d directory.",
        "Install umu-launcher, or GE-Proton/UMU-Proton via ProtonPlus "
        "(https://github.com/Vysp3r/ProtonPlus).",
    )


def _check_disk(config: Config) -> Recommendation:
    try:
        usage = shutil.disk_usage(_existing(config.bnet_dir))
    except OSError:
        return Recommendation("disk", "info", "Disk space could not be read", "")
    free_gb = usage.free / 1024**3
    if free_gb < _MIN_FREE_GB:
        return Recommendation(
            "disk",
            "warn",
            f"Low disk space ({free_gb:.0f} GB free)",
            "Games are large and prefixes grow.",
            "Free up space or move the prefix: set [paths] bnet_dir to a larger disk.",
        )
    return Recommendation("disk", "ok", f"{free_gb:.0f} GB free", "")


def _mount_fstype(path: Path) -> str | None:
    try:
        lines = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    best: tuple[int, str] | None = None
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        mount, fstype = parts[1].replace("\\040", " "), parts[2]
        if str(path).startswith(mount) and (best is None or len(mount) > best[0]):
            best = (len(mount), fstype)
    return best[1] if best else None


def _check_prefix_fs(config: Config) -> Recommendation:
    fstype = _mount_fstype(_existing(config.bnet_dir))
    if fstype and fstype not in _LINUX_FSTYPES:
        return Recommendation(
            "prefix-fs",
            "warn",
            f"The prefix is on {fstype}",
            "Wine needs a Linux filesystem (case-sensitive, with symlink and "
            "permission support). NTFS/exFAT can cause odd errors.",
            "Move the prefix to e.g. ~/Games (set [paths] bnet_dir).",
        )
    return Recommendation("prefix-fs", "ok", f"Filesystem: {fstype or 'unknown'}", "")


def _check_perf_tools(config: Config) -> Recommendation:
    missing = [
        name
        for name, enabled in (
            ("mangohud", config.performance.mangohud),
            ("gamemode", config.performance.gamemode),
            ("gamescope", config.performance.gamescope),
        )
        if enabled and not shutil.which(name)
    ]
    if missing:
        return Recommendation(
            "perf-tools",
            "warn",
            f"Performance tools missing: {', '.join(missing)}",
            "A toggle is on but points at a package that is not installed.",
            "Install the package or turn the toggle off under Settings -> Performance.",
        )
    return Recommendation("perf-tools", "ok", "Performance tools OK", "")


def _check_runner(config: Config) -> Recommendation:
    names = {build.name for build in proton.all_builds()}
    if not names:
        if shutil.which("umu-run"):
            return Recommendation(
                "runner",
                "info",
                f"Runner: {proton.DEFAULT_CODENAME} (auto-download)",
                "No local Proton build; umu-launcher will fetch it on first launch.",
                "Change the runner under Settings -> Runner.",
            )
        return Recommendation("runner", "info", "No runner to recommend", "")
    preferred = next((name for name in sorted(names) if "UMU-Proton" in name), None)
    if preferred and config.proton_name != preferred:
        return Recommendation(
            "runner",
            "info",
            f"Recommended runner: {preferred}",
            "UMU-Proton often works best for Battle.net.",
            "Pick it under Settings -> Runner.",
        )
    return Recommendation("runner", "ok", "Runner selected", "")


def report(config: Config) -> list[Recommendation]:
    """Every check (ok/info/warn), most severe first."""
    checks = [
        *_check_nvidia(),
        _check_vram(),
        _check_vulkan(),
        _check_hybrid_gpu(config),
        _check_render_scale(config),
        _check_umu(),
        _check_proton(),
        _check_disk(config),
        _check_prefix_fs(config),
        _check_perf_tools(config),
        _check_runner(config),
    ]
    checks.sort(key=_level_rank)
    return checks


def collect(config: Config) -> list[Recommendation]:
    """Actionable findings (info/warn) for the GUI strip and ``doctor``."""
    return [item for item in report(config) if item.level != "ok"]
