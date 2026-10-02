from __future__ import annotations

from pathlib import Path

import pytest

from frostfireinstaller import config as config_module
from frostfireinstaller.core import umu

EXE = r"C:\Program Files (x86)\Battle.net\Battle.net.exe"


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> config_module.Config:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("FROSTFIREINSTALLER_BNET_DIR", str(tmp_path / "bnet"))
    return config_module.Config.load()


def _tools(monkeypatch: pytest.MonkeyPatch, *present: str) -> None:
    monkeypatch.setattr(
        umu.shutil, "which", lambda name: f"/usr/bin/{name}" if name in present else None
    )


def test_plain_command(config, monkeypatch) -> None:
    _tools(monkeypatch)
    assert umu.launch_command(config, EXE) == ["umu-run", EXE]


def test_gamescope_flags_in_order(config, monkeypatch) -> None:
    _tools(monkeypatch, "gamescope", "mangoapp")
    perf = config.performance
    perf.gamescope = True
    perf.gamescope_width, perf.gamescope_height = 2560, 1440
    perf.gamescope_output = "HDMI-A-1"
    perf.gamescope_grab_cursor = True
    perf.gamescope_force_fullscreen = True
    perf.mangohud = True
    assert umu.launch_command(config, EXE) == [
        "gamescope",
        "-W", "2560", "-H", "1440",
        "-O", "HDMI-A-1",
        "--force-grab-cursor",
        "--force-windows-fullscreen",
        "--mangoapp",
        "-f", "--",
        "umu-run", EXE,
    ]  # fmt: skip


def test_gamescope_skipped_when_missing(config, monkeypatch) -> None:
    _tools(monkeypatch)
    config.performance.gamescope = True
    assert umu.launch_command(config, EXE) == ["umu-run", EXE]


def test_gamemode_wraps_outermost(config, monkeypatch) -> None:
    _tools(monkeypatch, "gamescope", "gamemode")
    config.performance.gamescope = True
    config.performance.gamemode = True
    cmd = umu.launch_command(config, EXE)
    assert cmd[0] == "gamemode"
    assert cmd[1] == "gamescope"


def test_mangohud_env_not_set_under_gamescope(config, monkeypatch) -> None:
    monkeypatch.delenv("MANGOHUD", raising=False)
    config.performance.mangohud = True
    assert umu.build_env(config, Path("/p"))["MANGOHUD"] == "1"
    config.performance.gamescope = True
    assert "MANGOHUD" not in umu.build_env(config, Path("/p"))


def test_user_env_wins(config) -> None:
    config.env["WINEDLLOVERRIDES"] = "custom"
    assert umu.build_env(config, Path("/p"))["WINEDLLOVERRIDES"] == "custom"


def test_inhibit_command_uses_both_tools_and_wineserver(monkeypatch) -> None:
    _tools(monkeypatch, "systemd-inhibit", "kde-inhibit")
    cmd = umu.inhibit_command()
    assert cmd is not None
    assert cmd[0] == "systemd-inhibit" and "--what=idle:sleep" in cmd
    assert "kde-inhibit" in cmd
    assert "wineserver" in cmd[-1]
    # relaunching Battle.net must not end the lock on the first miss
    assert f'"$miss" -lt {umu._GRACE_CHECKS}' in cmd[-1]
    assert umu._GRACE_CHECKS >= 3


def test_inhibit_command_none_without_tools(monkeypatch) -> None:
    _tools(monkeypatch)
    assert umu.inhibit_command() is None
