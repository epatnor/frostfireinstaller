"""Local, offline system checks and recommendations.

The app cannot know NVIDIA's or Blizzard's release schedule, so it reports what
it *can* see locally: whether the tools exist, where the prefix lives, how much
disk is free, the NVIDIA driver/module type and any recent ``NVRM: Xid`` /
``NV_ERR_NO_MEMORY`` faults in the kernel log, hybrid-GPU setups, and a Proton
runner suggestion.

Each finding carries copy-ready commands (and, for the reversible GPU mitigation,
an in-app toggle) so the user has the tools to act. ``collect()`` returns the
actionable warnings for the GUI strip; ``report()`` returns every check,
including the passing ones, for the "Systemkontroll" dialog and ``doctor``.
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
        return Recommendation("vram", "info", "Grafikminne kunde inte läsas", "")
    gb = mib / 1024
    if mib < 6 * 1024:
        return Recommendation(
            "vram",
            "info",
            f"Lågt grafikminne ({gb:.0f} GB)",
            "Moderna Blizzard-spel vill gärna ha mer. Det är sällan orsaken till "
            "frysningar (drivrutinen är), men håll grafikinställningarna måttliga.",
        )
    return Recommendation("vram", "ok", f"{gb:.0f} GB grafikminne", "")


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
                "Inget NVIDIA-kort hittat",
                "Körs på AMD/Intel – inga NVIDIA-specifika kontroller.",
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
                f"NVIDIA GPU-fel upptäckt ({' + '.join(signals)})",
                "GPU:n tappade sin kontext / kunde inte allokera minne – spel kan "
                "frysa vid tunga laddningar (t.ex. när en värld öppnas). Vanligt med "
                "open-kärnmodulerna.",
                "Prova de reversibla åtgärderna först; byt annars till den "
                "proprietàra drivrutinen. Se docs/troubleshooting.md.",
                commands=_driver_commands(is_open, True),
                action_id=action_id,
            )
        ]
    if is_open:
        return [
            Recommendation(
                "nvidia-open",
                "info",
                f"NVIDIA open-drivrutin {version}",
                "Open-kärnmodulerna har kända Xid/minnesproblem i vissa spel.",
                "Om spel fryser, byt till den proprietàra drivrutinen.",
                commands=_driver_commands(True, False),
                action_id=action_id,
            )
        ]
    return [
        Recommendation(
            "nvidia-ok",
            "ok",
            f"NVIDIA-drivrutin {version}",
            "Inga GPU-fel i kernelloggen den här uppstarten.",
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
        return Recommendation("hybrid", "ok", "Enkel GPU-konfiguration", "")

    if gpu_preference(config) == "integrated":
        return Recommendation(
            "hybrid",
            "ok",
            f"Hybrid-GPU: spelar på {integrated}",
            "Spelet är bundet till samma kort som skärmen – ingen kopiering mellan korten.",
        )

    log = _kernel_log()
    trouble = any(x in _SERIOUS_XIDS for x in _XID_RE.findall(log)) or "NV_ERR_NO_MEMORY" in log
    detail = (
        f"Laptopen har både NVIDIA och ett integrerat {integrated}-kort, och skärmen "
        "sitter på det integrerade kortet. Kör spelet på NVIDIA kopieras därför varje "
        "bildruta mellan korten (PRIME). Den vägen kan ge GPU-häng (Xid 109 / 'GPU "
        "Hung') och sessioner som blir allt långsammare – det är inte minnesbrist och "
        "inte strömläget."
    )
    if trouble:
        detail += " Kernelloggen visar redan sådana fel."
    return Recommendation(
        "hybrid",
        "warn" if trouble else "info",
        "Hybrid-GPU: skärmen sitter på det integrerade kortet",
        detail,
        "Välj grafikkort under Avancerat → Grafik: NVIDIA för dGPU-prestanda, "
        f"Integrerad ({integrated}) som felsökningsläge vid GPU-häng. Reversibelt.",
        commands=(
            '[env]\nDXVK_FILTER_DEVICE_NAME = "NVIDIA"     # tvinga NVIDIA',
            f'[env]\nDXVK_FILTER_DEVICE_NAME = "{integrated}"  # felsökningsläge',
            "vulkaninfo --summary   # visa exakta kortnamn",
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
        return Recommendation("wow-tuning", "ok", "Ingen WoW-installation hittad", "")

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
            "WoW: höj bakgrunds-FPS (maxFPSBK)",
            "När spelet står stilla (t.ex. vid karaktärsvalet) sänker WoW "
            "bildfrekvensen hårt i bakgrunden. Tillsammans med hybrid-GPU:n kan det "
            f"bidra till GPU-häng. Stäng spelet och lägg raden i {target} – ta bort "
            "den för att återställa.",
            commands=('SET maxFPSBK "60"',),
        )
    return Recommendation("wow-tuning", "ok", "WoW: bakgrunds-FPS satt", "")


def _check_wow_forever(config: Config) -> Recommendation:
    """Surface the two known World of Warcraft: Forever build-69913 bugs."""
    betas = [path for path in _find_wow_configs(config) if "_classic_beta_" in str(path)]
    if not betas:
        return Recommendation("wow-forever", "ok", "Ingen Forever-beta hittad", "")
    return Recommendation(
        "wow-forever",
        "info",
        "WoW Forever: kända buggar i build 69913",
        "Två oberoende fel i betan, båda olösta och inte orsakade av grafikkortet: "
        "(1) ERROR #135 – narration/röst-assert i VoiceSpeakManager vid inloggningen, "
        "ofarlig (ASSERTSAFE), ignorera dialogen; (2) ERROR #109 / NVIDIA Xid 109 – "
        "GPU-häng vid världsinträde. Build 69893 var stabil. Drivrutinen är inte för "
        "gammal – det är en klientregression.",
        "Vid GPU-häng: sätt Secondary Lighting till Fair under Options → Graphics "
        "(och ev. GxApi D3D11). Se docs/troubleshooting.md.",
    )


# --- requirements --------------------------------------------------------
def _check_umu() -> Recommendation:
    if shutil.which("umu-run"):
        return Recommendation("umu", "ok", "umu-launcher hittad", "")
    return Recommendation(
        "umu",
        "warn",
        "umu-launcher saknas",
        "Utan umu-run kan Battle.net inte startas.",
        "Installera umu-launcher (finns i Bazzite/Fedora och hos Open-Wine-Components).",
    )


def _check_proton() -> Recommendation:
    builds = proton.all_builds()
    if builds:
        return Recommendation("proton", "ok", f"{len(builds)} Proton-byggen hittade", "")
    return Recommendation(
        "proton",
        "warn",
        "Ingen Proton hittad",
        "En Proton-runner (GE-Proton/UMU-Proton) behövs i en compatibilitytools.d-katalog.",
        "Installera en via ProtonPlus (https://github.com/Vysp3r/ProtonPlus).",
    )


def _check_disk(config: Config) -> Recommendation:
    try:
        usage = shutil.disk_usage(_existing(config.bnet_dir))
    except OSError:
        return Recommendation("disk", "info", "Diskutrymme kunde inte läsas", "")
    free_gb = usage.free / 1024**3
    if free_gb < _MIN_FREE_GB:
        return Recommendation(
            "disk",
            "warn",
            f"Lite diskutrymme ({free_gb:.0f} GB ledigt)",
            "Spelen är stora och prefixen växer.",
            "Frigör utrymme eller flytta prefixen: sätt [paths] bnet_dir till en större disk.",
        )
    return Recommendation("disk", "ok", f"{free_gb:.0f} GB ledigt", "")


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
            f"Prefixen ligger på {fstype}",
            "Wine behöver ett Linux-filsystem (skiftlägeskänsligt, stöd för symlänkar "
            "och rättigheter). NTFS/exFAT kan ge konstiga fel.",
            "Flytta prefixen till t.ex. ~/Games (sätt [paths] bnet_dir).",
        )
    return Recommendation("prefix-fs", "ok", f"Filsystem: {fstype or 'okänt'}", "")


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
            f"Prestandaverktyg saknas: {', '.join(missing)}",
            "En påslagen växel pekar på ett paket som inte är installerat.",
            "Installera paketet eller stäng av växeln under Avancerat → Prestanda.",
        )
    return Recommendation("perf-tools", "ok", "Prestandaverktyg OK", "")


def _check_runner(config: Config) -> Recommendation:
    names = {build.name for build in proton.all_builds()}
    if not names:
        return Recommendation("runner", "info", "Ingen runner att rekommendera", "")
    preferred = next((name for name in sorted(names) if "UMU-Proton" in name), None)
    if preferred and config.proton_name != preferred:
        return Recommendation(
            "runner",
            "info",
            f"Rekommenderad runner: {preferred}",
            "UMU-Proton fungerar ofta bäst för Battle.net.",
            "Välj den under Avancerat → Runner.",
        )
    return Recommendation("runner", "ok", "Runner vald", "")


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
