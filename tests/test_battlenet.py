from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

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
        config_dir=prefix.parent,
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


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._sent = False

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self, _size: int = -1) -> bytes:
        if self._sent:
            return b""
        self._sent = True
        return self._data


def test_ensure_installer_retries_transient_error(tmp_path: Path, monkeypatch) -> None:
    config = make_config(tmp_path / "prefix")
    calls = {"n": 0}

    def fake_urlopen(_url: str, timeout: int = 0) -> _FakeResponse:
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("bad gateway")
        return _FakeResponse(b"installer-bytes")

    monkeypatch.setattr(battlenet.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(battlenet.time, "sleep", lambda _s: None)

    assert battlenet.ensure_installer(config) == config.installer
    assert calls["n"] == 3
    assert config.installer.read_bytes() == b"installer-bytes"


def test_ensure_installer_fails_fast_on_404(tmp_path: Path, monkeypatch) -> None:
    config = make_config(tmp_path / "prefix")
    calls = {"n": 0}

    def fake_urlopen(url: str, timeout: int = 0) -> _FakeResponse:
        calls["n"] += 1
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(battlenet.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(battlenet.time, "sleep", lambda _s: None)

    with pytest.raises(RuntimeError):
        battlenet.ensure_installer(config)
    assert calls["n"] == 1


def test_ensure_installer_reports_progress(tmp_path: Path, monkeypatch) -> None:
    config = make_config(tmp_path / "prefix")
    seen: list[str] = []

    monkeypatch.setattr(
        battlenet.urllib.request, "urlopen", lambda _url, timeout=0: _FakeResponse(b"x")
    )

    battlenet.ensure_installer(config, on_progress=seen.append)

    assert any("Laddar ner" in message for message in seen)
