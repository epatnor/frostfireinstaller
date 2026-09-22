"""Per-game profiles (bundled JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources


@dataclass(slots=True)
class GameProfile:
    id: str
    name: str
    product: str | None = None
    proton: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    args: list[str] = field(default_factory=list)
    anti_cheat: str | None = None
    notes: str = ""


def _games_dir():
    return resources.files("frostfireinstaller.data").joinpath("games")


def load_all() -> dict[str, GameProfile]:
    result: dict[str, GameProfile] = {}
    directory = _games_dir()
    for entry in directory.iterdir():
        if not entry.name.endswith(".json"):
            continue
        data = json.loads(entry.read_text(encoding="utf-8"))
        profile = GameProfile(
            id=data["id"],
            name=data["name"],
            product=data.get("product"),
            proton=data.get("proton"),
            env=dict(data.get("env", {})),
            args=list(data.get("args", [])),
            anti_cheat=data.get("anti_cheat"),
            notes=data.get("notes", ""),
        )
        result[profile.id] = profile
    return result
