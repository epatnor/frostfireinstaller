from __future__ import annotations

import pytest

from frostfireinstaller import __version__, cli


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "purge", "purge_installer"),
    [
        (["remove"], False, False),
        (["remove", "--purge", "--purge-installer"], True, True),
        (["reinstall", "--purge-installer"], False, True),
    ],
)
def test_remove_and_reinstall_flags(argv, purge, purge_installer) -> None:
    args = cli.build_parser().parse_args(argv)
    assert args.purge is purge
    assert args.purge_installer is purge_installer


def test_doctor_prints_report(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "c"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "s"))
    monkeypatch.setenv("FROSTFIREINSTALLER_BNET_DIR", str(tmp_path / "b"))
    from frostfireinstaller.core import distro, health, recommend

    monkeypatch.setattr(
        distro,
        "detect",
        lambda: distro.HostInfo("TestOS", False, "Wayland", "KDE", "6.0", None),
    )
    monkeypatch.setattr(health, "running", lambda: False)
    monkeypatch.setattr(
        recommend,
        "report",
        lambda _c: [recommend.Recommendation("x", "warn", "Something", commands=("fix it",))],
    )
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "TestOS" in out
    assert "[warn] Something" in out
    assert "$ fix it" in out
