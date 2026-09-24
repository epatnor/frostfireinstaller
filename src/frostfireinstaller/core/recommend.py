"""Local, offline system checks and recommendations.

The app cannot know NVIDIA's or Blizzard's release schedule, so it reports what
it *can* see locally: whether the tools exist, where the prefix lives, how much
disk is free, the NVIDIA driver/module type and any recent ``NVRM: Xid`` /
``NV_ERR_NO_MEMORY`` faults in the kernel log, hybrid-GPU setups, and a Proton
runner suggestion.

Each finding carries copy-ready commands (and, for the reversible GPU mitigation,
an in-app toggle) so the user has the tools to act. ``collect()`` returns the
actionable warnings for the GUI strip; ``report()`` returns every check,
including the passing ones, for the "System check" dialog and ``doctor``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from . import proton

# Xid values that usually mean a GPU/driver hang rather than an app bug.
_SERIOUS_XIDS = {"13", "31", "43", "62", "79", "109", "119", "120"}
_MIN_FREE_GB = 15
_LINUX_FSTYPES = {"ext2", "ext3", "ext4", "btrfs", "xfs", "f2fs", "zfs", "tmpfs", "overlay"}

_XID_RE = re.compile(r"NVRM: Xid \(PCI:[0-9a-fA-F:.]+\):\s*(\d+)")
_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


@dataclass(slots=True)
class Recommendation:
    id: str
    level: str  # "ok" | "info" | "warn"
    title: str
    detail: str = ""
    action: str = ""
    commands: tuple[str, ...] = field(default_factory=tuple)
    action_id: str = ""  # a reversible in-app action, e.g. "persistenced"


def _level_rank(item: Recommendation) -> int:
    return {"warn": 0, "info": 1, "ok": 2}.get(item.level, 3)


def _existing(path: Path) -> Path:
    node = path
    while not node.exists() and node != node.parent:
        node = node.parent
    return node


# --- NVIDIA / GPU --------------------------------------------------------
def nvidia_driver_info() -> tuple[str | None, bool]:
    """Return ``(driver_version, is_open_module)`` (``(None, False)`` if no NVIDIA)."""
    try:
        text = Path("/proc/driver/nvidia/version").read_text(encoding="utf-8")
    except OSError:
        return None, False
    match = _VERSION_RE.search(text)
    return (match.group(1) if match else None), "Open Kernel Module" in text


def _nvidia_pci() -> str | None:
    """The NVIDIA GPU's PCI address (e.g. ``0000:01:00.0``), if it can be found."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=pci.bus_id", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    line = out.stdout.strip().splitlines()[0].strip() if out.stdout.strip() else ""
    # "00000000:01:00.0" -> "0000:01:00.0"
    return line[-12:] if len(line) >= 12 else None


def _kernel_log(limit: int = 300) -> str:
    if not shutil.which("journalctl"):
        return ""
    try:
        out = subprocess.run(
            ["journalctl", "-k", "-b", "-n", str(limit), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout


def recent_xids(limit: int = 300) -> list[str]:
    """Return Nvidia Xid codes from the current boot's kernel log (best effort)."""
    return _XID_RE.findall(_kernel_log(limit))


def _integrated_gpu() -> str | None:
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*/device/vendor")):
        try:
            vendor = card.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if vendor == "0x1002":
            return "AMD"
        if vendor == "0x8086":
            return "Intel"
    return None


def _vram_mib() -> int | None:
    """Total video memory in MiB, if it can be determined."""
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            out = None
        if out is not None and out.stdout.strip().splitlines():
            value = out.stdout.strip().splitlines()[0].strip()
            if value.isdigit():
                return int(value)
    for node in Path("/sys/class/drm").glob("card[0-9]*/device/mem_info_vram_total"):
        try:
            total = int(node.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if total > 0:
            return total // 1024**2
    return None


def _check_vram() -> Recommendation:
    mib = _vram_mib()
    if mib is None:
        return Recommendation("vram", "info", "Video memory could not be read", "")
    gb = mib / 1024
    if mib < 6 * 1024:
        return Recommendation(
            "vram",
            "info",
            f"Low video memory ({gb:.0f} GB)",
            "Modern Blizzard games prefer more. It is rarely the cause of freezes "
            "(the driver is), but keep the graphics settings moderate.",
        )
    return Recommendation("vram", "ok", f"{gb:.0f} GB video memory", "")


def _driver_commands(is_open: bool, serious: bool) -> tuple[str, ...]:
    commands: list[str] = []
    if serious:
        commands.append("sudo systemctl enable --now nvidia-persistenced")
        address = _nvidia_pci()
        if address:
            commands.append(f"sudo sh -c 'echo on > /sys/bus/pci/devices/{address}/power/control'")
        commands.append("sudo sh -c 'echo performance > /sys/module/pcie_aspm/parameters/policy'")
    if is_open and shutil.which("rpm-ostree"):
        commands.append(
            "rpm-ostree rebase ostree-image-signed:docker://ghcr.io/ublue-os/bazzite-nvidia:stable"
        )
    return tuple(commands)


def persistenced_state() -> str | None:
    """Return nvidia-persistenced's state, or ``None`` if unavailable."""
    if not shutil.which("nvidia-persistenced") or not shutil.which("systemctl"):
        return None
    try:
        out = subprocess.run(
            ["systemctl", "is-active", "nvidia-persistenced"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    state = out.stdout.strip()
    return state or None


def _check_nvidia() -> list[Recommendation]:
    version, is_open = nvidia_driver_info()
    if version is None:
        return [
            Recommendation(
                "nvidia",
                "info",
                "No NVIDIA GPU found",
                "Running on AMD/Intel - no NVIDIA-specific checks.",
            )
        ]

    log = _kernel_log()
    serious = sorted({x for x in _XID_RE.findall(log) if x in _SERIOUS_XIDS}, key=int)
    oom = "NV_ERR_NO_MEMORY" in log
    action_id = "persistenced" if persistenced_state() is not None else ""

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
                f"NVIDIA GPU fault detected ({' + '.join(signals)})",
                "The GPU lost its context / could not allocate memory - games can "
                "freeze under heavy loads (e.g. when a world opens). Common with the "
                "open kernel modules.",
                "Try the reversible steps first; otherwise switch to the "
                "proprietary driver. See docs/troubleshooting.md.",
                commands=_driver_commands(is_open, True),
                action_id=action_id,
            )
        ]
    if is_open:
        return [
            Recommendation(
                "nvidia-open",
                "info",
                f"NVIDIA open driver {version}",
                "The open kernel modules have known Xid/memory issues in some games.",
                "If games freeze, switch to the proprietary driver.",
                commands=_driver_commands(True, False),
                action_id=action_id,
            )
        ]
    return [
        Recommendation(
            "nvidia-ok",
            "ok",
            f"NVIDIA driver {version}",
            "No GPU faults in the kernel log this boot.",
        )
    ]


def integrated_gpu_name() -> str | None:
    """A name substring for the integrated GPU, for ``DXVK_FILTER_DEVICE_NAME``."""
    vendor = _integrated_gpu()
    if vendor == "AMD":
        return "AMD Radeon"
    if vendor == "Intel":
        return "Intel"
    return None


def gpu_preference(config: Config | None = None) -> str:
    """The configured GPU preference: ``auto``, ``nvidia`` or ``integrated``."""
    cfg = config if config is not None else Config.load()
    value = cfg.env.get("DXVK_FILTER_DEVICE_NAME", "")
    if not value:
        return "auto"
    return "nvidia" if "nvidia" in value.lower() else "integrated"


def _check_hybrid_gpu(config: Config) -> Recommendation:
    version, _ = nvidia_driver_info()
    integrated = integrated_gpu_name()
    if not (version and integrated):
        return Recommendation("hybrid", "ok", "Single-GPU configuration", "")

    if gpu_preference(config) == "integrated":
        return Recommendation(
            "hybrid",
            "ok",
            f"Hybrid GPU: playing on {integrated}",
            "The game is bound to the same GPU as the screen - no cross-GPU copy.",
        )

    log = _kernel_log()
    trouble = any(x in _SERIOUS_XIDS for x in _XID_RE.findall(log)) or "NV_ERR_NO_MEMORY" in log
    detail = (
        f"The laptop has both NVIDIA and an integrated {integrated} GPU, and the "
        "screen is wired to the integrated one. Running the game on NVIDIA therefore "
        "copies every frame between the GPUs (PRIME). That path can cause GPU hangs "
        "(Xid 109 / 'GPU Hung') and sessions that get slower and slower - it is not "
        "memory pressure and not the power profile."
    )
    if trouble:
        detail += " The kernel log already shows such faults."
    return Recommendation(
        "hybrid",
        "warn" if trouble else "info",
        "Hybrid GPU: the screen is wired to the integrated GPU",
        detail,
        "Choose the GPU under Advanced -> Graphics: NVIDIA for dGPU performance, "
        f"Integrated ({integrated}) as a troubleshooting mode for GPU hangs. "
        "Reversible.",
        commands=(
            '[env]\nDXVK_FILTER_DEVICE_NAME = "NVIDIA"     # force NVIDIA',
            f'[env]\nDXVK_FILTER_DEVICE_NAME = "{integrated}"  # troubleshooting mode',
            "vulkaninfo --summary   # show exact device names",
        ),
    )


def _find_wow_configs(config: Config) -> list[Path]:
    base = config.prefix / "drive_c" / "Program Files (x86)" / "World of Warcraft"
    if not base.is_dir():
        return []
    return sorted(base.glob("*/WTF/Config.wtf"))


def _check_wow_tuning(config: Config) -> Recommendation:
    configs = _find_wow_configs(config)
    if not configs:
        return Recommendation("wow-tuning", "ok", "No WoW installation found", "")

    unset = []
    for path in configs:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "maxFPSBK" not in text:
            unset.append(path)

    if unset:
        target = unset[0]
        return Recommendation(
            "wow-tuning",
            "info",
            "WoW: raise background FPS (maxFPSBK)",
            "When the game is idle (e.g. at character select) WoW drops the frame "
            "rate hard in the background. Combined with a hybrid GPU this can "
            f"contribute to GPU hangs. Close the game and add the line to {target} - "
            "remove it to restore.",
            commands=('SET maxFPSBK "60"',),
        )
    return Recommendation("wow-tuning", "ok", "WoW: background FPS set", "")


def _check_wow_forever(config: Config) -> Recommendation:
    """Surface the World of Warcraft: Forever build-69913 bugs and their fix."""
    betas = [path for path in _find_wow_configs(config) if "_classic_beta_" in str(path)]
    if not betas:
        return Recommendation("wow-forever", "ok", "No Forever beta found", "")
    return Recommendation(
        "wow-forever",
        "info",
        "WoW Forever: build 69913 bugs (fixed in 69977)",
        "Build 69913 had an ERROR #109 / NVIDIA Xid 109 GPU hang on world entry, "
        "caused by an unbounded Global Illumination compute shader (not the driver - "
        "it also affects AMD/Windows and macOS). Build 69977 fixes it. A separate, "
        "still-open issue is a session-long FPS drop / apparent memory leak.",
        "Update to build 69977 or later. If you are stuck on 69913, set Secondary "
        "Lighting to Fair (Options -> Graphics) or use the integrated GPU. See "
        "docs/troubleshooting.md.",
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
        "Install umu-launcher (available on Bazzite/Fedora and from Open-Wine-Components).",
    )


def _check_proton() -> Recommendation:
    builds = proton.all_builds()
    if builds:
        return Recommendation("proton", "ok", f"{len(builds)} Proton builds found", "")
    return Recommendation(
        "proton",
        "warn",
        "No Proton found",
        "A Proton runner (GE-Proton/UMU-Proton) is needed in a compatibilitytools.d directory.",
        "Install one via ProtonPlus (https://github.com/Vysp3r/ProtonPlus).",
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
            "Install the package or turn the toggle off under Advanced -> Performance.",
        )
    return Recommendation("perf-tools", "ok", "Performance tools OK", "")


def _check_runner(config: Config) -> Recommendation:
    names = {build.name for build in proton.all_builds()}
    if not names:
        return Recommendation("runner", "info", "No runner to recommend", "")
    preferred = next((name for name in sorted(names) if "UMU-Proton" in name), None)
    if preferred and config.proton_name != preferred:
        return Recommendation(
            "runner",
            "info",
            f"Recommended runner: {preferred}",
            "UMU-Proton often works best for Battle.net.",
            "Pick it under Advanced -> Runner.",
        )
    return Recommendation("runner", "ok", "Runner selected", "")


def report(config: Config) -> list[Recommendation]:
    """Every check (ok/info/warn), most severe first."""
    checks = [
        *_check_nvidia(),
        _check_vram(),
        _check_hybrid_gpu(config),
        _check_wow_tuning(config),
        _check_wow_forever(config),
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
