from __future__ import annotations

from pathlib import Path

from frostylauncher.config import Config, Performance
from frostylauncher.core import battlenet


def make_config(prefix: Path) -> Config:
    return Config(
        gameid="umu-battlenet",
        proton_name=None,
        performance=Performance(),
        bnet_dir=prefix.parent,
        prefix=prefix,
        installer=prefix.parent / "Battle.net-Setup.exe",
        data_dir=prefix.parent,
        config_dir=prefix.parent,
        state_dir=prefix.parent,
        log_dir=prefix.parent,
    )


def test_installed_games_detects_wow(tmp_path: Path) -> None:
    prefix = tmp_path / "prefix"
    wow = prefix / "drive_c/Program Files (x86)/World of Warcraft"
    wow.mkdir(parents=True)
    games = battlenet.installed_games(make_config(prefix))
    assert wow in games


def test_installed_games_empty(tmp_path: Path) -> None:
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    assert battlenet.installed_games(make_config(prefix)) == []
