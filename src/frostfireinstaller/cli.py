"""Command-line interface for frostfireinstaller."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, service
from .config import Config
from .core import battlenet, distro, health, profiles, proton
from .logsetup import get_logger, setup_console, setup_run_log

log = get_logger()


def _show_log(path: Path) -> int:
    if not path.is_file():
        log.error("Ingen logg hittad: %s", path)
        return 1
    if sys.stdout.isatty() and shutil.which("less"):
        subprocess.run(["less", "-R", str(path)], check=False)
    else:
        sys.stdout.write(path.read_text(encoding="utf-8", errors="ignore"))
    return 0


def cmd_run(_args: argparse.Namespace) -> int:
    config = Config.load()
    setup_run_log(config.log_dir)
    build = service.ensure(config)
    service.launch(config, build)
    if not health.wait_for_ui(40):
        health.remediate(config)
        service.launch(config, build)
        if not health.wait_for_ui(40):
            log.error("Kunde inte starta Battle.net.")
            return 1
    log.info("Klart.")
    return 0


def cmd_ensure(_args: argparse.Namespace) -> int:
    config = Config.load()
    setup_run_log(config.log_dir)
    service.ensure(config)
    return 0


def cmd_reinstall(args: argparse.Namespace) -> int:
    config = Config.load()
    setup_run_log(config.log_dir)
    build = service.find_proton(config)
    log_path = battlenet.reinstall(config, build, keep_games=not args.purge)
    log.info("Installationslogg: %s", log_path)
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    config = Config.load()
    setup_run_log(config.log_dir)
    battlenet.remove(config, keep_games=not args.purge)
    log.info("Battle.net borttaget%s", "" if args.purge else " (spel behållna)")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    config = Config.load()
    setup_run_log(config.log_dir)
    host = distro.detect()
    print(f"frostfireinstaller {__version__}")
    print(f"distro     : {host.distro}")
    print(f"atomic     : {'ja' if host.atomic else 'nej'}")
    print(f"session    : {host.session}")
    print(f"desktop    : {host.desktop}")
    print(f"kernel     : {host.kernel}")
    print(f"gpu        : {host.gpu or '-'}")
    print(f"umu        : {shutil.which('umu-run') or 'saknas'}")
    print(f"winetricks : {shutil.which('winetricks') or 'saknas'}")
    print(f"proton     : {proton.find(config.proton_name) or 'saknas'}")
    print(f"prefix     : {config.prefix} {'(finns)' if config.prefix.is_dir() else '(saknas)'}")
    print(f"bnet       : {'installerat' if battlenet.installed(config) else 'ej installerat'}")
    print(f"running    : {'ja' if health.running() else 'nej'}")
    print(f"loggar     : {config.log_dir}")

    builds = proton.all_builds()
    if builds:
        print("proton-byggen:")
        for build in builds:
            print(f"  - {build}")

    games = profiles.load_all()
    if games:
        print("spelprofiler:")
        for game in games.values():
            print(f"  - {game.id}: {game.name}")
    return 0


def cmd_logs(_args: argparse.Namespace) -> int:
    config = Config.load()
    return _show_log(config.log_dir / "latest.log")


def cmd_install_logs(_args: argparse.Namespace) -> int:
    config = Config.load()
    return _show_log(config.log_dir / "latest-install.log")


def cmd_kill(_args: argparse.Namespace) -> int:
    health.kill_all()
    return 0


def cmd_gui(_args: argparse.Namespace) -> int:
    from . import gui

    return gui.main([sys.argv[0]])


def cmd_uninstall(args: argparse.Namespace) -> int:
    config = Config.load()
    apps = service.applications_dir()
    data_home = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
    icon = data_home / "icons/hicolor/scalable/apps" / f"{service.APP_ID}.svg"
    log.warning("Tar bort: %s, genväg och ikon", config.bnet_dir)
    if not args.yes:
        answer = input("Säker? [j/N] ").strip().lower()
        if answer not in ("j", "ja", "y", "yes"):
            log.info("Avbrutet")
            return 0
    health.kill_all()
    shutil.rmtree(config.bnet_dir, ignore_errors=True)
    (apps / f"{service.APP_ID}.desktop").unlink(missing_ok=True)
    (apps / "frostfireinstaller.desktop").unlink(missing_ok=True)
    icon.unlink(missing_ok=True)
    log.info("Borttaget")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="frostfireinstaller",
        description="A Battle.net installer helper for Linux (umu-launcher + Proton).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="ensure everything and launch (default)")
    sub.add_parser("ensure", help="set up/verify only, do not launch")
    reinstall = sub.add_parser("reinstall", help="reinstall Battle.net (keeps games by default)")
    reinstall.add_argument("--purge", action="store_true", help="also remove installed games")
    remove = sub.add_parser("remove", help="remove the Battle.net client (keeps games by default)")
    remove.add_argument("--purge", action="store_true", help="also remove installed games")
    sub.add_parser("doctor", help="show environment and status")
    sub.add_parser("logs", help="show the latest run log")
    sub.add_parser("install-logs", help="show the latest installation log")
    sub.add_parser("kill", help="stop all Battle.net processes")
    sub.add_parser("gui", help="open the graphical interface")
    uninstall = sub.add_parser("uninstall", help="remove prefix, shortcut and icon")
    uninstall.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_console(logging.DEBUG if args.verbose else logging.INFO)

    handlers = {
        "run": cmd_run,
        "ensure": cmd_ensure,
        "reinstall": cmd_reinstall,
        "remove": cmd_remove,
        "doctor": cmd_doctor,
        "logs": cmd_logs,
        "install-logs": cmd_install_logs,
        "kill": cmd_kill,
        "gui": cmd_gui,
        "uninstall": cmd_uninstall,
    }
    command = args.command or "run"
    return handlers[command](args)
