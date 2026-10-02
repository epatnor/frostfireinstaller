from __future__ import annotations

import subprocess

from frostfireinstaller.core import sysinfo


def _stdout(monkeypatch, text: str) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout=text)
    )


def test_disks_skips_virtual_devices(monkeypatch) -> None:
    _stdout(
        monkeypatch,
        'NAME="nvme0n1" SIZE="476.9G" MODEL="Samsung SSD" ROTA="0" TYPE="disk"\n'
        'NAME="sda" SIZE="1.8T" MODEL="WDC HDD" ROTA="1" TYPE="disk"\n'
        'NAME="zram0" SIZE="8G" MODEL="" ROTA="0" TYPE="disk"\n'
        'NAME="nvme0n1p1" SIZE="1G" MODEL="" ROTA="0" TYPE="part"\n',
    )
    assert sysinfo.disks() == ["Samsung SSD (476.9G, SSD)", "WDC HDD (1.8T, HDD)"]


def test_memory_without_dmidecode(monkeypatch) -> None:
    monkeypatch.setattr(sysinfo.shutil, "which", lambda _name: None)
    assert sysinfo.memory().endswith("GB") or sysinfo.memory() == "unknown"


def test_memory_dmi_types_and_speeds(monkeypatch) -> None:
    monkeypatch.setattr(sysinfo.shutil, "which", lambda _name: "/usr/sbin/dmidecode")
    _stdout(
        monkeypatch,
        "Memory Device\n\tType: DDR4\n\tSpeed: 3200 MT/s\n"
        "Memory Device\n\tType: Unknown\n\tSpeed: Unknown\n",
    )
    assert sysinfo._memory_dmi() == "DDR4 3200 MT/s"


def test_cpu_includes_clock(monkeypatch) -> None:
    monkeypatch.setattr(sysinfo, "_cpu_model", lambda: "AMD Ryzen 5 5600H")
    monkeypatch.setattr(sysinfo, "_cpu_nominal_khz", lambda: 3_300_000)
    assert sysinfo.cpu() == "AMD Ryzen 5 5600H (3.3 GHz)"
    monkeypatch.setattr(sysinfo, "_cpu_nominal_khz", lambda: 0)
    assert sysinfo.cpu() == "AMD Ryzen 5 5600H"
