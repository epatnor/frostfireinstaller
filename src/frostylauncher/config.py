"""Configuration and XDG paths.

Overridable via ``$XDG_CONFIG_HOME/frostylauncher/config.toml``:

    [runtime]
    gameid = "umu-battlenet"
    proton = "GE-Proton11-7-x86_64"   # optional, else auto-detected

    [paths]
    bnet_dir = "~/Games/battlenet"
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

APP = "frostylauncher"


def _xdg(var: str, default: str) -> Path:
    return Path(os.environ.get(var, default)).expanduser()


@dataclass(slots=True)
class Config:
    gameid: str
    proton_name: str | None
    bnet_dir: Path
    prefix: Path
    installer: Path
    data_dir: Path
    config_dir: Path
    state_dir: Path
    log_dir: Path

    # --- derived paths -----------------------------------------------------
    @property
    def battlenet_exe(self) -> str:
        """Windows path passed to umu-run."""
        return r"C:\Program Files (x86)\Battle.net\Battle.net.exe"

    @property
    def battlenet_exe_unix(self) -> Path:
        return self.prefix / "drive_c" / "Program Files (x86)" / "Battle.net" / "Battle.net.exe"

    @property
    def installer_url(self) -> str:
        return (
            "https://www.battle.net/download/getInstallerForGame"
            "?os=win&installer=Battle.net-Setup.exe"
        )

    # --- factory -----------------------------------------------------------
    @classmethod
    def load(cls) -> Config:
        data_dir = _xdg("XDG_DATA_HOME", "~/.local/share") / APP
        config_dir = _xdg("XDG_CONFIG_HOME", "~/.config") / APP
        state_dir = _xdg("XDG_STATE_HOME", "~/.local/state") / APP

        bnet_dir = Path(os.environ.get("FROSTYLAUNCHER_BNET_DIR", "~/Games/battlenet")).expanduser()
        gameid = "umu-battlenet"
        proton_name: str | None = None

        cfg_file = config_dir / "config.toml"
        if cfg_file.is_file():
            with cfg_file.open("rb") as fh:
                data = tomllib.load(fh)
            runtime = data.get("runtime", {})
            paths = data.get("paths", {})
            gameid = str(runtime.get("gameid", gameid))
            proton_name = runtime.get("proton") or None
            bnet_dir = Path(paths.get("bnet_dir", bnet_dir)).expanduser()

        return cls(
            gameid=gameid,
            proton_name=proton_name,
            bnet_dir=bnet_dir,
            prefix=bnet_dir / "prefix",
            installer=bnet_dir / "Battle.net-Setup.exe",
            data_dir=data_dir,
            config_dir=config_dir,
            state_dir=state_dir,
            log_dir=state_dir / "logs",
        )


def save_proton_override(name: str | None) -> Path:
    """Write a minimal config.toml selecting a Proton build by directory name."""
    config_dir = _xdg("XDG_CONFIG_HOME", "~/.config") / APP
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.toml"
    lines = ["[runtime]"]
    if name:
        lines.append(f'proton = "{name}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
