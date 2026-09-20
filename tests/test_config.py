from __future__ import annotations

from pathlib import Path

from frostylauncher.config import Config


def test_load_derives_paths() -> None:
    config = Config.load()
    assert config.prefix == config.bnet_dir / "prefix"
    assert config.installer == config.bnet_dir / "Battle.net-Setup.exe"
    assert config.log_dir.name == "logs"
    assert isinstance(config.battlenet_exe_unix, Path)


def test_battlenet_exe_strings() -> None:
    config = Config.load()
    assert config.battlenet_exe == r"C:\Program Files (x86)\Battle.net\Battle.net.exe"
    assert str(config.battlenet_exe_unix).startswith(str(config.prefix))
    assert config.installer_url.startswith("https://")
