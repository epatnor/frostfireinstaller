from __future__ import annotations

from pathlib import Path

import pytest

from frostfireinstaller import service
from frostfireinstaller.config import Config, _toml_value
from frostfireinstaller.core import umu


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


@pytest.fixture()
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    monkeypatch.setenv("FROSTFIREINSTALLER_BNET_DIR", str(tmp_path / "Games/battlenet"))
    return Config.load()


def test_toml_value_escapes_strings() -> None:
    assert _toml_value('a"b\\c') == '"a\\"b\\\\c"'
    assert _toml_value(True) == "true"
    assert _toml_value(False) == "false"


def test_save_keeps_unmanaged_sections(sandbox: Config) -> None:
    sandbox.config_dir.mkdir(parents=True)
    sandbox.config_file.write_text(
        '[paths]\nbnet_dir = "/mnt/games/battlenet"\n\n[custom]\nfoo = "bar"\n',
        encoding="utf-8",
    )

    sandbox.performance.mangohud = True
    sandbox.save()

    text = sandbox.config_file.read_text(encoding="utf-8")
    assert 'bnet_dir = "/mnt/games/battlenet"' in text
    assert 'foo = "bar"' in text
    assert "mangohud = true" in text
    assert Config.load().performance.mangohud is True


def test_save_roundtrips_quoted_values(sandbox: Config) -> None:
    sandbox.proton_name = 'we"ird\\name'
    sandbox.save()
    assert Config.load().proton_name == 'we"ird\\name'


def test_desktop_exec_quotes_only_when_needed() -> None:
    assert service._desktop_exec("/usr/bin/app", "gui") == "/usr/bin/app gui"
    assert service._desktop_exec("/opt/my apps/app", "gui") == '"/opt/my apps/app" gui'


def test_env_section_is_read_and_applied(sandbox: Config) -> None:
    sandbox.config_dir.mkdir(parents=True, exist_ok=True)
    sandbox.config_file.write_text(
        '[env]\nDXVK_FILTER_DEVICE_NAME = "AMD Radeon"\n', encoding="utf-8"
    )

    config = Config.load()
    assert config.env["DXVK_FILTER_DEVICE_NAME"] == "AMD Radeon"

    env = umu.build_env(config, Path("/usr/lib/proton"))
    assert env["DXVK_FILTER_DEVICE_NAME"] == "AMD Radeon"
    assert env["WINEPREFIX"] == str(config.prefix)

    config.save()
    assert "DXVK_FILTER_DEVICE_NAME" in sandbox.config_file.read_text(encoding="utf-8")


def test_set_persistenced_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_run(cmd: list[str], check: bool = False) -> None:
        calls["cmd"] = cmd
        calls["check"] = check

    monkeypatch.setattr(service.subprocess, "run", fake_run)
    service.set_persistenced(True)
    assert calls["cmd"] == ["systemctl", "enable", "--now", "nvidia-persistenced"]
    service.set_persistenced(False)
    assert calls["cmd"] == ["systemctl", "disable", "--now", "nvidia-persistenced"]


def test_set_gpu_preference_roundtrips(sandbox: Config) -> None:
    service.set_gpu_preference("nvidia")
    assert Config.load().env["DXVK_FILTER_DEVICE_NAME"] == "NVIDIA"

    service.set_gpu_preference("integrated")
    assert Config.load().env["DXVK_FILTER_DEVICE_NAME"]

    service.set_gpu_preference("auto")
    assert "DXVK_FILTER_DEVICE_NAME" not in Config.load().env
