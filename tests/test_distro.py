"""Tests for host detection helpers."""

from __future__ import annotations

from frostfireinstaller.core import distro


def test_gpu_prefers_nvidia_summary(monkeypatch) -> None:
    monkeypatch.setattr(distro.gpu, "nvidia_summary", lambda: "GeForce RTX 4070 (550.54.14)")
    assert distro._gpu() == "GeForce RTX 4070 (550.54.14)"


def test_gpu_falls_back_to_pci(monkeypatch) -> None:
    monkeypatch.setattr(distro.gpu, "nvidia_summary", lambda: None)
    monkeypatch.setattr(distro.gpu, "pci_gpus", lambda: ["Raptor Lake-P [Iris Xe]", "x"])
    assert distro._gpu() == "Raptor Lake-P [Iris Xe]"
    monkeypatch.setattr(distro.gpu, "pci_gpus", lambda: [])
    assert distro._gpu() is None


def test_session_is_normalised(monkeypatch) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    assert distro.session() == "Wayland"
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    assert distro.session() == "X11"
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    assert distro.session() == "unknown"
