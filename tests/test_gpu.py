from __future__ import annotations

import subprocess
from pathlib import Path

from test_recommend import make_config

from frostfireinstaller.core import gpu


def test_integrated_gpu_name(monkeypatch) -> None:
    monkeypatch.setattr(gpu, "_integrated_vendor", lambda: "AMD")
    assert gpu.integrated_gpu_name() == "AMD"
    monkeypatch.setattr(gpu, "_integrated_vendor", lambda: "Intel")
    assert gpu.integrated_gpu_name() == "Intel"
    monkeypatch.setattr(gpu, "_integrated_vendor", lambda: None)
    assert gpu.integrated_gpu_name() is None


def test_gpu_preference(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    assert gpu.gpu_preference(config) == "auto"
    config.env["DXVK_FILTER_DEVICE_NAME"] = "NVIDIA"
    assert gpu.gpu_preference(config) == "nvidia"
    config.env["DXVK_FILTER_DEVICE_NAME"] = "AMD"
    assert gpu.gpu_preference(config) == "integrated"


def test_pci_gpus_strips_vendor_and_revision(monkeypatch) -> None:
    out = (
        "00:02.0 VGA compatible controller: Intel Corporation Raptor Lake-P [Iris Xe] (rev 04)\n"
        "01:00.0 3D controller: NVIDIA Corporation GA107M [GeForce RTX 3050 Ti] (rev a1)\n"
        "00:1f.3 Audio device: Intel Corporation Something\n"
    )
    monkeypatch.setattr(gpu.shutil, "which", lambda _name: "/usr/bin/lspci")
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout=out)
    )
    assert gpu.pci_gpus() == ["Raptor Lake-P [Iris Xe]", "GA107M [GeForce RTX 3050 Ti]"]


def test_nvidia_summary_formats_name_and_driver(monkeypatch) -> None:
    out = "NVIDIA GeForce RTX 4070 Laptop GPU, 550.54.14\n"
    monkeypatch.setattr(gpu.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout=out)
    )
    assert gpu.nvidia_summary() == "GeForce RTX 4070 (550.54.14)"


def test_nvidia_summary_none_without_tool(monkeypatch) -> None:
    monkeypatch.setattr(gpu.shutil, "which", lambda _name: None)
    assert gpu.nvidia_summary() is None


def test_vulkan_parsing(monkeypatch) -> None:
    out = "apiVersion = 1.4.354\ndeviceName = AMD Radeon Graphics\napiVersion = 1.3.0\n"
    monkeypatch.setattr(gpu.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout=out)
    )
    assert gpu.vulkan_versions_and_names() == ([(1, 4, 354), (1, 3, 0)], ["AMD Radeon Graphics"])
