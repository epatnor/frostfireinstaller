from __future__ import annotations

import pytest

from frostfireinstaller.core import battlenet, health
from frostfireinstaller.gui.state import ClientState


def test_read_checks_once(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "c"))
    monkeypatch.setenv("FROSTFIREINSTALLER_BNET_DIR", str(tmp_path / "b"))
    calls = []
    monkeypatch.setattr(health, "running", lambda: calls.append(1) or False)
    monkeypatch.setattr(battlenet, "installed", lambda _config: True)
    state = ClientState.read()
    assert calls == [1]
    assert state.config.bnet_dir == tmp_path / "b"
    assert state.summary == "Battle.net stopped"


@pytest.mark.parametrize(
    ("running", "installed", "text"),
    [
        (True, True, "Battle.net running"),
        (False, True, "Battle.net stopped"),
        (False, False, "Battle.net not installed"),
    ],
)
def test_summary(running: bool, installed: bool, text: str) -> None:
    assert ClientState(config=None, installed=installed, running=running).summary == text  # type: ignore[arg-type]
