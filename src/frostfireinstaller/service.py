"""High-level operations shared by the CLI and the GUI.

Keeps the orchestration (ensure/launch/shortcut) out of the front-ends.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from .config import Config
from .core import battlenet, proton, recommend, umu
from .logsetup import get_logger

log = get_logger()

Progress = Callable[[str], None]


def _emit(on_progress: Progress | None, message: str) -> None:
    if on_progress is None:
        return
    try:
        on_progress(message)
    except Exception:  # noqa: BLE001
        log.debug("progress callback failed", exc_info=True)


APP_ID = "io.github.frostfireinstaller"


def _data_file(*parts: str) -> Path | None:
    try:
        base = resources.files("frostfireinstaller.data")
    except (ModuleNotFoundError, TypeError):
        return None
    target = base.joinpath(*parts)
    try:
        return Path(str(target)) if target.is_file() else None
    except (FileNotFoundError, OSError):
        return None


def applications_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    return base / "applications"


def _desktop_exec(*parts: str) -> str:
    """Quote argv parts for a .desktop Exec line (double quotes per the spec)."""
    return " ".join(f'"{part}"' if " " in part else part for part in parts)


def ensure_shortcut(config: Config) -> Path:
    """Install the app icon and a .desktop entry that opens the GUI."""
    data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    apps = applications_dir()
    icons = data_home / "icons/hicolor/512x512/apps"
    apps.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)

    icon_src = _data_file("icons", "frostfireinstaller.png")
    if icon_src is not None:
        shutil.copyfile(icon_src, icons / f"{APP_ID}.png")
    # Icons from the pre-0.1 SVG were installed here; drop any stale copy.
    (data_home / "icons/hicolor/scalable/apps" / f"{APP_ID}.svg").unlink(missing_ok=True)

    # The user hicolor theme needs an index.theme, otherwise the icon is not found.
    theme_index = data_home / "icons/hicolor/index.theme"
    if not theme_index.is_file():
        system_index = Path("/usr/share/icons/hicolor/index.theme")
        if system_index.is_file():
            shutil.copyfile(system_index, theme_index)

    exe = shutil.which("frostfireinstaller")
    if exe:
        exec_line = _desktop_exec(exe, "gui")
    else:
        exec_line = _desktop_exec(sys.executable, "-m", "frostfireinstaller", "gui")

    desktop = apps / f"{APP_ID}.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Name=Frostfire Installer\n"
        "Comment=Battle.net installer helper (umu + Proton)\n"
        f"Exec={exec_line}\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Game;\n"
        f"StartupWMClass={APP_ID}\n",
        encoding="utf-8",
    )
    (apps / "frostfireinstaller.desktop").unlink(missing_ok=True)

    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(apps)], check=False)
    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(data_home / "icons/hicolor")],
            check=False,
        )
    return desktop


def set_persistenced(enable: bool) -> None:
    """Toggle ``nvidia-persistenced`` (reversible GPU mitigation).

    Run as the user: systemd asks Polkit/the desktop for authorisation. Raises
    ``subprocess.CalledProcessError`` if the user declines or it fails.
    """
    action = "enable" if enable else "disable"
    subprocess.run(["systemctl", action, "--now", "nvidia-persistenced"], check=True)


def set_gpu_preference(preference: str) -> None:
    """Set which GPU the games use: ``auto``, ``nvidia`` or ``integrated``.

    Writes/removes ``DXVK_FILTER_DEVICE_NAME`` in config.toml. On a hybrid laptop
    whose panel hangs off the integrated GPU, the "integrated" option renders on
    the same GPU as the screen and avoids the cross-GPU (PRIME) copy that can hang
    the NVIDIA driver. Fully reversible, no privileges.
    """
    if preference not in {"auto", "nvidia", "integrated"}:
        raise ValueError(f"unknown GPU preference: {preference!r}")
    config = Config.load()
    if preference == "auto":
        config.env.pop("DXVK_FILTER_DEVICE_NAME", None)
    elif preference == "nvidia":
        config.env["DXVK_FILTER_DEVICE_NAME"] = "NVIDIA"
    else:
        config.env["DXVK_FILTER_DEVICE_NAME"] = recommend.integrated_gpu_name() or "AMD Radeon"
    config.save()


def find_proton(config: Config) -> Path:
    build = proton.find(config.proton_name)
    if not build:
        raise RuntimeError(
            "Hittade ingen Proton. Installera GE-Proton/UMU-Proton i en "
            "compatibilitytools.d-katalog (t.ex. via ProtonPlus)."
        )
    return build


def ensure(config: Config, on_progress: Progress | None = None) -> Path:
    """Idempotently set everything up and return the chosen Proton build."""
    if not shutil.which("umu-run"):
        raise RuntimeError("umu-run saknas. Installera umu-launcher och försök igen.")

    config.bnet_dir.mkdir(parents=True, exist_ok=True)

    _emit(on_progress, "Söker efter Proton ...")
    build = find_proton(config)
    log.info("Proton: %s", build)

    battlenet.ensure_installer(config, on_progress=on_progress)

    if battlenet.installed(config):
        log.info("Battle.net redan installerat")
    else:
        log_path = battlenet.install(config, build, on_progress=on_progress)
        log.info("Installationslogg: %s", log_path)

    if battlenet.ensure_config(config):
        log.info("Stängde av 'starta minimerad'")

    _emit(on_progress, "Skapar genväg ...")
    ensure_shortcut(config)
    return build


def launch(config: Config, build: Path) -> None:
    from .core import health

    if health.running():
        log.info("Battle.net kör redan")
        return
    log.info("Startar Battle.net ...")
    umu.spawn(config, build, config.battlenet_exe)
