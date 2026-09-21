from __future__ import annotations

from pathlib import Path

from frostfireinstaller.config import Config, Performance
from frostfireinstaller.core import battlenet


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


def test_remove_keeps_installer_by_default(tmp_path: Path, monkeypatch) -> None:
    prefix = tmp_path / "prefix"
    (prefix / "drive_c/Program Files (x86)/Battle.net").mkdir(parents=True)
    config = make_config(prefix)
    config.installer.write_bytes(b"stub")
    monkeypatch.setattr(battlenet.health, "kill_all", lambda: None)

    battlenet.remove(config)

    assert not (prefix / "drive_c/Program Files (x86)/Battle.net").exists()
    assert config.installer.is_file()


def test_remove_purge_installer(tmp_path: Path, monkeypatch) -> None:
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    config = make_config(prefix)
    config.installer.write_bytes(b"stub")
    config.installer.with_suffix(".exe.part").write_bytes(b"partial")
    monkeypatch.setattr(battlenet.health, "kill_all", lambda: None)

    battlenet.remove(config, remove_installer=True)

    assert not config.installer.exists()
    assert not config.installer.with_suffix(".exe.part").exists()
