from __future__ import annotations

import subprocess

from frostfireinstaller.core import health


def test_running_true_when_pgrep_finds_client(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout="1234\n")
    )
    assert health.running() is True


def test_running_false_without_match_or_pgrep(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 1, stdout="")
    )
    assert health.running() is False

    def missing(*_a, **_k):
        raise FileNotFoundError("pgrep")

    monkeypatch.setattr(subprocess, "run", missing)
    assert health.running() is False


def test_kill_all_terms_before_kills(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **_k: calls.append(cmd))
    monkeypatch.setattr(health.time, "sleep", lambda _s: None)
    health.kill_all()
    patterns = len(health._KILL_PATTERNS)
    assert all("-9" not in cmd for cmd in calls[:patterns])
    assert all("-9" in cmd for cmd in calls[patterns:])
    assert len(calls) == 2 * patterns


def test_ui_check_assumes_fine_without_x(monkeypatch) -> None:
    # Pure Wayland: never read "cannot tell" as "the client is broken".
    monkeypatch.delenv("DISPLAY", raising=False)
    assert health.ui_window_present() is True


def test_ui_check_reads_window_tree(monkeypatch) -> None:
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(health.shutil, "which", lambda _name: "/usr/bin/xwininfo")
    tree = '0x1 "Battle.net": ("battle.net.exe" "battle.net.exe")\n'
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout=tree)
    )
    assert health.ui_window_present() is True
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout="other\n")
    )
    assert health.ui_window_present() is False


def test_remediate_clears_cef_and_cache(monkeypatch, tmp_path) -> None:
    from frostfireinstaller.config import Config

    monkeypatch.setenv("FROSTFIREINSTALLER_BNET_DIR", str(tmp_path))
    monkeypatch.setattr(health, "kill_all", lambda: None)
    monkeypatch.setattr(health.time, "sleep", lambda _s: None)
    config = Config.load()
    base = config.prefix / "drive_c/users/steamuser/AppData/Local/Battle.net"
    for name in ("Cache", "CEF", "Logs"):
        (base / name).mkdir(parents=True)
    health.remediate(config)
    assert not (base / "Cache").exists()
    assert not (base / "CEF").exists()
    assert (base / "Logs").exists()
