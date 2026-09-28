"""Logging: colored console output plus per-run and per-installation log files."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

LOGGER_NAME = "frostfireinstaller"

_COLORS = {
    logging.DEBUG: "\033[2m",
    logging.INFO: "\033[34m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;31m",
}
_RESET = "\033[0m"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelno, "")
        label = f"[{record.levelname.lower():>6}]"
        return f"{color}{label}{_RESET} {record.getMessage()}"


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def setup_console(level: int = logging.INFO) -> None:
    logger = get_logger()
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ConsoleFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def _symlink(link: Path, target: Path) -> None:
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(target)
    except OSError:
        pass


def add_file_handler(path: Path) -> logging.FileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    get_logger().addHandler(handler)
    return handler


def setup_run_log(log_dir: Path) -> Path:
    """Tee every run into a timestamped file; update the ``latest.log`` link."""
    path = log_dir / f"run-{_timestamp()}.log"
    add_file_handler(path)
    _symlink(log_dir / "latest.log", path)
    return path


def open_install_log(log_dir: Path) -> Path:
    """Create a fresh, timestamped installation log; update ``latest-install.log``."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"install-{_timestamp()}.log"
    path.write_text("", encoding="utf-8")
    _symlink(log_dir / "latest-install.log", path)
    return path
