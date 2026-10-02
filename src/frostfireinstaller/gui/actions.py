"""Background actions behind the buttons: repair, reinstall, remove, choices."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from .. import service  # noqa: E402
from ..config import Config  # noqa: E402
from ..core import battlenet, health, proton  # noqa: E402
from .helpers import run_async  # noqa: E402
from .widgets import Surface, reporter  # noqa: E402


def run_action(
    surface: Surface,
    button: Gtk.Button,
    busy: str,
    work: Callable[[Callable[[str], None]], Any],
    finished: Callable[[Any], str],
) -> None:
    """Run *work* off the GTK thread with the activity strip and toasts around it.

    *work* receives a thread-safe progress reporter; *finished* turns its result
    into the success toast.
    """
    button.set_sensitive(False)
    surface.set_activity(busy)
    surface.toast(busy)

    def done(result: Any) -> None:
        button.set_sensitive(True)
        surface.clear_activity()
        surface.refresh_state()
        surface.toast(finished(result))

    def error(exc: Exception) -> None:
        button.set_sensitive(True)
        surface.clear_activity()
        surface.refresh_state()
        surface.toast(f"Error: {exc}")

    report = reporter(surface)
    run_async(lambda: work(report), done, error)


def start(surface: Surface, button: Gtk.Button) -> None:
    """Install if needed, then launch Battle.net."""

    def work(report: Callable[[str], None]) -> None:
        config = Config.load()
        service.launch(config, service.ensure(config, on_progress=report))

    run_action(surface, button, "Starting Battle.net ...", work, lambda _: "Starting Battle.net")


def repair(surface: Surface, button: Gtk.Button) -> None:
    def work(report: Callable[[str], None]) -> None:
        config = Config.load()
        health.remediate(config)
        service.launch(config, service.ensure(config, on_progress=report))

    run_action(surface, button, "Repairing ...", work, lambda _: "Repaired and started")


def reinstall(surface: Surface, button: Gtk.Button, keep_games: bool, keep_installer: bool) -> None:
    def work(report: Callable[[str], None]) -> None:
        config = Config.load()
        build = proton.find(config.proton_name)
        if build is None:
            raise RuntimeError("No Proton found")
        battlenet.reinstall(
            config,
            build,
            keep_games=keep_games,
            remove_installer=not keep_installer,
            on_progress=report,
        )

    run_action(
        surface,
        button,
        "Reinstalling Battle.net ...",
        work,
        lambda _: "Reinstalled" + (" (games kept)" if keep_games else ""),
    )


def remove(surface: Surface, button: Gtk.Button, keep_games: bool, keep_installer: bool) -> None:
    def work(report: Callable[[str], None]) -> None:
        battlenet.remove(
            Config.load(),
            keep_games=keep_games,
            remove_installer=not keep_installer,
            on_progress=report,
        )

    run_action(
        surface,
        button,
        "Removing Battle.net ...",
        work,
        lambda _: "Battle.net removed" + (" (games kept)" if keep_games else ""),
    )


def pick_runner(surface: Surface, name: str) -> None:
    config = Config.load()
    config.proton_name = name
    config.save()
    surface.refresh_state()
    surface.toast(f"Runner set to {name}")


def pick_gpu(surface: Surface, preference: str) -> None:
    try:
        service.set_gpu_preference(preference)
    except (OSError, ValueError) as exc:
        surface.toast(f"Failed: {exc}")
        return
    surface.refresh_state()
    surface.toast("Graphics choice saved - restart Battle.net and the game.")
