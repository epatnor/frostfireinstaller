"""Tests for host detection helpers."""

from __future__ import annotations

import subprocess

from frostfireinstaller.core import distro


def test_nvidia_formats_name_and_driver(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="NVIDIA GeForce RTX 3050 Ti Laptop GPU, 615.71.09\n",
        )

    monkeypatch.setattr(distro.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(distro.subprocess, "run", fake_run)
    assert distro._nvidia() == "GeForce RTX 3050 Ti (615.71.09)"


def test_nvidia_returns_none_without_tool(monkeypatch) -> None:
    monkeypatch.setattr(distro.shutil, "which", lambda _name: None)
    assert distro._nvidia() is None


def test_pci_strips_vendor_prefix(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="01:00.0 VGA compatible controller: Intel Corporation Raptor Lake-P [Iris Xe]\n",
        )

    monkeypatch.setattr(distro.shutil, "which", lambda _name: "/usr/bin/lspci")
    monkeypatch.setattr(distro.subprocess, "run", fake_run)
    assert distro._pci() == "Raptor Lake-P [Iris Xe]"


def test_session_is_normalised(monkeypatch) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert distro._session() == "Wayland"
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert distro._session() == "X11"
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    assert distro._session() == "unknown"
