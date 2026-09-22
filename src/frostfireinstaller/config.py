"""Configuration and XDG paths.

Overridable via ``$XDG_CONFIG_HOME/frostfireinstaller/config.toml``:

    [runtime]
    gameid = "umu-battlenet"
    proton = "GE-Proton11-7-x86_64"   # optional, else auto-detected

    [performance]
    mangohud = false
    gamemode = false
    gamescope = false

    [paths]
    bnet_dir = "~/Games/battlenet"

    [env]
    # extra environment for the Wine session (umu-run + Battle.net + games)
    DXVK_FILTER_DEVICE_NAME = "AMD Radeon"
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

APP = "frostfireinstaller"


def _xdg(var: str, default: str) -> Path:
    return Path(os.environ.get(var, default)).expanduser()


def _toml_value(value: object) -> str:
    """Render a scalar as TOML (strings are escaped; no silent injection)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"cannot serialise {type(value).__name__} to TOML")


@dataclass(slots=True)
class Performance:
    mangohud: bool = False
    gamemode: bool = False
    gamescope: bool = False


@dataclass(slots=True)
class Config:
    gameid: str
    proton_name: str | None
    performance: Performance
    bnet_dir: Path
    prefix: Path
    installer: Path
    config_dir: Path
    log_dir: Path
    env: dict[str, str] = field(default_factory=dict)

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

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"

    # --- factory -----------------------------------------------------------
    @classmethod
    def load(cls) -> Config:
        config_dir = _xdg("XDG_CONFIG_HOME", "~/.config") / APP
        state_dir = _xdg("XDG_STATE_HOME", "~/.local/state") / APP

        bnet_dir = Path(
            os.environ.get("FROSTFIREINSTALLER_BNET_DIR", "~/Games/battlenet")
        ).expanduser()
        gameid = "umu-battlenet"
        proton_name: str | None = None
        performance = Performance()
        env: dict[str, str] = {}

        cfg_file = config_dir / "config.toml"
        if cfg_file.is_file():
            with cfg_file.open("rb") as fh:
                data = tomllib.load(fh)
            runtime = data.get("runtime", {})
            paths = data.get("paths", {})
            perf = data.get("performance", {})
            gameid = str(runtime.get("gameid", gameid))
            proton_name = runtime.get("proton") or None
            env = {str(key): str(value) for key, value in dict(data.get("env", {})).items()}
            bnet_dir = Path(paths.get("bnet_dir", bnet_dir)).expanduser()
            performance = Performance(
                mangohud=bool(perf.get("mangohud", False)),
                gamemode=bool(perf.get("gamemode", False)),
                gamescope=bool(perf.get("gamescope", False)),
            )

        return cls(
            gameid=gameid,
            proton_name=proton_name,
            performance=performance,
            bnet_dir=bnet_dir,
            prefix=bnet_dir / "prefix",
            installer=bnet_dir / "Battle.net-Setup.exe",
            config_dir=config_dir,
            log_dir=state_dir / "logs",
            env=env,
        )

    # --- persistence -------------------------------------------------------
    def save(self) -> Path:
        """Write ``config.toml``, keeping keys and sections we do not manage."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data: dict[str, dict[str, object]] = {}
        if self.config_file.is_file():
            with self.config_file.open("rb") as fh:
                data = tomllib.load(fh)

        runtime = data.setdefault("runtime", {})
        runtime["gameid"] = self.gameid
        if self.proton_name:
            runtime["proton"] = self.proton_name
        data.setdefault("performance", {}).update(
            {
                "mangohud": self.performance.mangohud,
                "gamemode": self.performance.gamemode,
                "gamescope": self.performance.gamescope,
            }
        )
        if self.env:
            data["env"] = dict(self.env)
        else:
            data.pop("env", None)

        lines: list[str] = []
        for section, values in data.items():
            lines.append(f"[{section}]")
            for key, value in values.items():
                lines.append(f"{key} = {_toml_value(value)}")
            lines.append("")
        self.config_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return self.config_file
