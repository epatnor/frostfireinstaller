"""High-level operations shared by the CLI and the GUI.

Keeps the orchestration (ensure/launch/shortcut) out of the front-ends.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from .config import Config
from .core import battlenet, proton, umu
from .logsetup import get_logger

log = get_logger()

APP_ID = "io.github.frostylauncher"


def _data_file(*parts: str) -> Path | None:
    try:
        base = resources.files("frostylauncher.data")
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


def ensure_shortcut(config: Config) -> Path:
    """Install the app icon and a .desktop entry that opens the GUI."""
    data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    apps = applications_dir()
    icons = data_home / "icons/hicolor/scalable/apps"
    apps.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)

    icon_src = _data_file("icons", "frostylauncher.svg")
    if icon_src is not None:
        shutil.copyfile(icon_src, icons / f"{APP_ID}.svg")

    # The user hicolor theme needs an index.theme, otherwise the icon is not found.
    theme_index = data_home / "icons/hicolor/index.theme"
    if not theme_index.is_file():
        system_index = Path("/usr/share/icons/hicolor/index.theme")
        if system_index.is_file():
            shutil.copyfile(system_index, theme_index)

    exe = shutil.which("frostylauncher")
    exec_line = f"{exe} gui" if exe else f"{sys.executable} -m frostylauncher gui"

    desktop = apps / f"{APP_ID}.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Name=frostylauncher\n"
        "Comment=Battle.net installer helper (umu + Proton)\n"
        f"Exec={exec_line}\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Game;\n"
        f"StartupWMClass={APP_ID}\n",
        encoding="utf-8",
    )
    (apps / "frostylauncher.desktop").unlink(missing_ok=True)

    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(apps)], check=False)
    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(data_home / "icons/hicolor")],
            check=False,
        )
    return desktop


def find_proton(config: Config) -> Path:
    build = proton.find(config.proton_name)
    if not build:
        raise RuntimeError(
            "Hittade ingen Proton. Installera GE-Proton/UMU-Proton i en "
            "compatibilitytools.d-katalog (t.ex. via ProtonPlus)."
        )
    return build


def ensure(config: Config) -> Path:
    """Idempotently set everything up and return the chosen Proton build."""
    if not shutil.which("umu-run"):
        raise RuntimeError("umu-run saknas. Installera umu-launcher och försök igen.")

    config.bnet_dir.mkdir(parents=True, exist_ok=True)

    build = find_proton(config)
    log.info("Proton: %s", build)

    battlenet.ensure_installer(config)

    if battlenet.installed(config):
        log.info("Battle.net redan installerat")
    else:
        log_path = battlenet.install(config, build)
        log.info("Installationslogg: %s", log_path)

    if battlenet.ensure_config(config):
        log.info("Stängde av 'starta minimerad'")

    ensure_shortcut(config)
    return build


def launch(config: Config, build: Path) -> None:
    from .core import health

    if health.running():
        log.info("Battle.net kör redan")
        return
    log.info("Startar Battle.net ...")
    umu.spawn(config, build, config.battlenet_exe)
