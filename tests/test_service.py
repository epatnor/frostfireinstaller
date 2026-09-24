from __future__ import annotations

from pathlib import Path

import pytest

from frostfireinstaller import service
from frostfireinstaller.config import Config, Performance


def make_config(root: Path) -> Config:
    return Config(
        gameid="umu-battlenet",
        proton_name=None,
        performance=Performance(),
        bnet_dir=root,
        prefix=root / "prefix",
        installer=root / "Battle.net-Setup.exe",
        config_dir=root,
        log_dir=root,
    )


def test_find_proton_returns_local_build(tmp_path: Path, monkeypatch) -> None:
    build = tmp_path / "GE-Proton11-7"
    monkeypatch.setattr(service.proton, "find", lambda _name: build)
    assert service.find_proton(make_config(tmp_path)) == build


def test_find_proton_falls_back_to_codename(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(service.proton, "find", lambda _name: None)
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/umu-run")
    assert service.find_proton(make_config(tmp_path)) == Path("UMU-Proton")


def test_find_proton_raises_without_umu(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(service.proton, "find", lambda _name: None)
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError):
        service.find_proton(make_config(tmp_path))
