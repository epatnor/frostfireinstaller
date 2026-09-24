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


def test_find_rejects_traversal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    for name in ("../etc", "a/b", ".", "..", "", "a\\b"):
        assert proton.find(name) is None


def test_is_codename() -> None:
    assert proton.is_codename("UMU-Proton")
    assert proton.is_codename("GE-Proton")
    assert not proton.is_codename("GE-Proton11-7")
    assert not proton.is_codename(None)


def test_find_codename_without_local_build(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.find("UMU-Proton") == Path("UMU-Proton")


def test_local_build_wins_over_codename(tmp_path: Path, monkeypatch) -> None:
    build = tmp_path / "UMU-Proton"
    build.mkdir()
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.find("UMU-Proton") == build
