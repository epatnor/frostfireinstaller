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


def _build(root: Path, name: str, version: str | None = None) -> Path:
    build = root / name
    build.mkdir()
    (build / "proton").touch()
    if version:
        (build / "version").write_text(f"1789520217 {version}\n")
    return build


def test_all_builds_newest_first(tmp_path: Path, monkeypatch) -> None:
    umu = _build(tmp_path, "UMU-Proton-10.0-4", "UMU-Proton-10.0-4")
    ge7 = _build(tmp_path, "GE-Proton11-7-x86_64", "GE-Proton11-7")
    ge12 = _build(tmp_path, "GE-Proton11-12-x86_64", "GE-Proton11-12")
    ge2 = _build(tmp_path, "GE-Proton11-2")
    latest = _build(tmp_path, "Proton-GE Latest", "GE-Proton11-5")
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.all_builds() == [ge12, ge7, latest, ge2, umu]


def test_find_picks_newest_in_family(tmp_path: Path, monkeypatch) -> None:
    _build(tmp_path, "GE-Proton11-2")
    newest = _build(tmp_path, "GE-Proton11-12")
    _build(tmp_path, "GE-Proton9-27")
    monkeypatch.setattr(proton, "SEARCH_DIRS", (tmp_path,))
    assert proton.find() == newest


def test_label_shows_hidden_release(tmp_path: Path) -> None:
    latest = _build(tmp_path, "Proton-GE Latest", "GE-Proton11-5")
    plain = _build(tmp_path, "GE-Proton11-12-x86_64", "GE-Proton11-12")
    bare = _build(tmp_path, "UMU-Proton-10.0-4")
    assert proton.label(latest) == "Proton-GE Latest (GE-Proton11-5)"
    assert proton.label(plain) == "GE-Proton11-12-x86_64"
    assert proton.label(bare) == "UMU-Proton-10.0-4"


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
