"""Battle.net install / readiness / config helpers."""

from __future__ import annotations

import hashlib
import platform
import shutil
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..logsetup import get_logger, open_install_log
from . import distro, health, umu

log = get_logger()


# --- state ---------------------------------------------------------------
def installed(config: Config) -> bool:
    return config.battlenet_exe_unix.is_file()


def client_log_dir(config: Config) -> Path | None:
    users = config.prefix / "drive_c" / "users"
    if not users.is_dir():
        return None
    for path in users.glob("*/AppData/Local/Battle.net/Logs"):
        if path.is_dir():
            return path
    return None


def latest_client_log(config: Config) -> Path | None:
    directory = client_log_dir(config)
    if not directory:
        return None
    logs = sorted(directory.glob("battle.net-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def launcher_ready(config: Config) -> bool:
    """Reliable signal that the launcher finished initialising."""
    path = latest_client_log(config)
    if not path:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "*** LOAD COMPLETE ***" in text or "login.app?app=app" in text


def wait_for_launcher_ready(config: Config, timeout: int = 300, interval: int = 2) -> bool:
    log.info("Väntar på att Battle.net ska bli klart (max %ss)...", timeout)
    waited = 0
    while waited < timeout:
        if installed(config) and launcher_ready(config):
            return True
        time.sleep(interval)
        waited += interval
    return False


# --- installer -----------------------------------------------------------
def ensure_installer(config: Config) -> Path:
    if config.installer.is_file():
        return config.installer
    config.bnet_dir.mkdir(parents=True, exist_ok=True)
    log.info("Hämtar Battle.net-Setup.exe ...")
    tmp = config.installer.with_suffix(".exe.part")
    with urllib.request.urlopen(config.installer_url, timeout=120) as resp, tmp.open("wb") as fh:  # noqa: S310
        shutil.copyfileobj(resp, fh)
    tmp.replace(config.installer)
    return config.installer


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install(config: Config, proton: Path) -> Path:
    """Run the installer, wait for readiness, then auto-close the first run.

    Returns the path to the installation log.
    """
    log_path = open_install_log(config.log_dir)
    _write_header(log_path, config, proton)

    log.info("Startar Battle.net-installationen (klicka ev. 'Continue' i fönstret)...")
    with log_path.open("a", encoding="utf-8") as out:
        umu.spawn(config, proton, str(config.installer), stdout=out, stderr=out)
        ready = wait_for_launcher_ready(config)
        out.write("\n--- Klarsignal ---\n")
        out.write(f"launcher_ready       : {'ja' if ready else 'nej'}\n")
        out.write(f"battlenet_installed  : {'ja' if installed(config) else 'nej'}\n")
        _append_client_log(out, config)

    ok = installed(config)
    if ok:
        log.info("Stänger första körningen automatiskt (rekommenderas före inloggning).")
        health.kill_all()
    _append_result(log_path, ready, ok)
    return log_path


# --- config --------------------------------------------------------------
def ensure_config(config: Config) -> bool:
    """Turn off 'start minimized' so the login window shows. Returns True if changed."""
    cfg = config.prefix / "drive_c/users/steamuser/AppData/Roaming/Battle.net/Battle.net.config"
    if not cfg.is_file():
        return False
    text = cfg.read_text(encoding="utf-8", errors="ignore")
    if '"MinimizedOnStartup": "true"' not in text:
        return False
    cfg.write_text(
        text.replace('"MinimizedOnStartup": "true"', '"MinimizedOnStartup": "false"'),
        encoding="utf-8",
    )
    return True


# --- log helpers ---------------------------------------------------------
def _write_header(path: Path, config: Config, proton: Path) -> None:
    host = distro.detect()
    prefix_new = "ja" if not config.prefix.is_dir() else "nej"
    lines = [
        "=" * 60,
        " frostylauncher - INSTALLATIONSLOGG",
        "=" * 60,
        f"date            : {datetime.now().isoformat(timespec='seconds')}",
        f"host            : {platform.node()}",
        f"kernel          : {platform.release()}",
        f"distro          : {host.distro}",
        f"atomic          : {'ja' if host.atomic else 'nej'}",
        f"session         : {host.session}",
        f"desktop         : {host.desktop}",
        f"gpu             : {host.gpu or '-'}",
        "",
        "--- Konfiguration ---",
        f"prefix          : {config.prefix}",
        f"prefix_ny       : {prefix_new}",
        f"gameid          : {config.gameid}",
        f"proton          : {proton}",
        f"installer       : {config.installer}",
        f"installer_url   : {config.installer_url}",
        "env             : WINE_SIMULATE_WRITECOPY=1",
        "                  WINEDLLOVERRIDES=locationapi=d",
    ]
    if config.installer.is_file():
        lines.append(f"installer_size  : {config.installer.stat().st_size} bytes")
        lines.append(f"installer_sha256: {sha256(config.installer)}")
    lines += ["", "--- Installer output (umu / Proton / Wine) ---"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_client_log(out: object, config: Config) -> None:
    path = latest_client_log(config)
    out.write("\n--- Battle.net-klientens logg (senaste 150 rader) ---\n")  # type: ignore[attr-defined]
    if path:
        out.write(f"# {path}\n")  # type: ignore[attr-defined]
        tail = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-150:]
        out.write("\n".join(tail) + "\n")  # type: ignore[attr-defined]
    else:
        out.write("(ingen klientlogg hittad)\n")  # type: ignore[attr-defined]


def _append_result(path: Path, ready: bool, ok: bool) -> None:
    with path.open("a", encoding="utf-8") as out:
        out.write("\n--- Resultat ---\n")
        out.write(f"status          : {'OK - Battle.net installerat' if ok else 'MISSLYCKAT'}\n")
        out.write(f"finished        : {datetime.now().isoformat(timespec='seconds')}\n")
