from __future__ import annotations

from pathlib import Path

from frostfireinstaller.core import proton


def test_find_exact_name(tmp_path: Path, monkeypatch) -> None:
    build = tmp_path / "GE-Proton9-99"
    build.mkdir()
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.find("GE-Proton9-99") == build


def test_find_prefers_ge_proton(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "Proton-Experimental").mkdir()
    ge = tmp_path / "GE-Proton11-7"
    ge.mkdir()
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.find() == ge


def test_find_missing_returns_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.find() is None
