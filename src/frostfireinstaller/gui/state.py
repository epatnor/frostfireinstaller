"""The client state every window shows, read once per refresh.

Widgets used to each load ``config.toml`` and run ``pgrep`` on their own, so a
single refresh hit the disk and spawned processes several times - and widgets
built from a startup snapshot of the config drew stale values. A refresh now
reads one ``ClientState`` and hands it to every widget.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config
from ..core import battlenet, health


@dataclass(frozen=True, slots=True)
class ClientState:
    config: Config
    installed: bool
    running: bool

    @classmethod
    def read(cls) -> ClientState:
        config = Config.load()
        return cls(config, battlenet.installed(config), health.running())

    @property
    def summary(self) -> str:
        if self.running:
            return "Battle.net running"
        return "Battle.net stopped" if self.installed else "Battle.net not installed"
