from __future__ import annotations

from frostylauncher.core import profiles


def test_load_all_contains_known_games() -> None:
    games = profiles.load_all()
    assert "battlenet" in games
    assert "wow" in games
    assert games["wow"].name.startswith("World of Warcraft")


def test_get_unknown_returns_none() -> None:
    assert profiles.get("does-not-exist") is None
