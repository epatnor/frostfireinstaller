from __future__ import annotations

import subprocess
from pathlib import Path

from frostfireinstaller.config import Config, Performance
from frostfireinstaller.core import recommend


def make_config(root: Path) -> Config:
    return Config(
        gameid="umu-battlenet",
        proton_name=None,
        performance=Performance(),
        bnet_dir=root,
        prefix=root / "prefix",
        installer=root / "Battle.net-Setup.exe",
        config_dir=root,
        log_dir=root,
    )


def test_recent_xids_parses_kernel_log(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                "NVRM: Xid (PCI:0000:01:00): 109, pid=1, name=WowB.exe, CTX SWITCH TIMEOUT\n"
                "unrelated line\n"
                "NVRM: Xid (PCI:0000:01:00): 13, pid=2\n"
            ),
        )

    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/journalctl")
    monkeypatch.setattr(recommend.subprocess, "run", fake_run)
    assert recommend.recent_xids() == ["109", "13"]


def test_recent_xids_without_journalctl(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: None)
    assert recommend.recent_xids() == []


def test_nvidia_warns_on_serious_xid(monkeypatch) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(
        recommend, "_kernel_log", lambda *_: "NVRM: Xid (PCI:0000:01:00): 109, CTX SWITCH TIMEOUT"
    )
    monkeypatch.setattr(recommend, "persistenced_state", lambda: "inactive")
    monkeypatch.setattr(recommend, "_nvidia_pci", lambda: "0000:01:00.0")
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/rpm-ostree")

    items = recommend._check_nvidia()

    assert items[0].level == "warn"
    assert "bazzite-nvidia" in " ".join(items[0].commands)
    assert any("nvidia-persistenced" in command for command in items[0].commands)
    assert any("power/control" in command for command in items[0].commands)
    assert items[0].action_id == "persistenced"


def test_nvidia_warns_on_memory_error(monkeypatch) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend, "_kernel_log", lambda *_: "NVRM: ... NV_ERR_NO_MEMORY ...")
    monkeypatch.setattr(recommend, "persistenced_state", lambda: None)

    items = recommend._check_nvidia()

    assert items[0].level == "warn"
    assert "NV_ERR_NO_MEMORY" in items[0].title


def test_nvidia_info_when_open_without_fault(monkeypatch) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend, "_kernel_log", lambda *_: "")
    monkeypatch.setattr(recommend, "persistenced_state", lambda: None)
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: None)

    items = recommend._check_nvidia()

    assert len(items) == 1
    assert items[0].level == "info"


def test_nvidia_info_without_nvidia(monkeypatch) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: (None, False))
    items = recommend._check_nvidia()
    assert items[0].level == "info"


def test_collect_filters_ok(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        recommend,
        "report",
        lambda _config: [
            recommend.Recommendation("a", "ok", "ok"),
            recommend.Recommendation("b", "warn", "warn"),
            recommend.Recommendation("c", "info", "info"),
        ],
    )
    levels = [item.level for item in recommend.collect(make_config(tmp_path))]
    assert levels == ["warn", "info"]


def test_report_sorts_most_severe_first(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        recommend, "_check_nvidia", lambda: [recommend.Recommendation("n", "info", "i")]
    )
    monkeypatch.setattr(recommend, "_check_vram", lambda: recommend.Recommendation("v", "ok", "o"))
    monkeypatch.setattr(
        recommend, "_check_vulkan", lambda: recommend.Recommendation("k", "ok", "o")
    )
    monkeypatch.setattr(recommend, "_check_umu", lambda: recommend.Recommendation("u", "warn", "w"))
    monkeypatch.setattr(
        recommend, "_check_hybrid_gpu", lambda _c: recommend.Recommendation("h", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_wow_tuning", lambda _c: recommend.Recommendation("w", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_wow_forever", lambda _c: recommend.Recommendation("f", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_proton", lambda: recommend.Recommendation("p", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_disk", lambda _c: recommend.Recommendation("d", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_prefix_fs", lambda _c: recommend.Recommendation("f", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_perf_tools", lambda _c: recommend.Recommendation("t", "ok", "o")
    )
    monkeypatch.setattr(
        recommend, "_check_runner", lambda _c: recommend.Recommendation("r", "ok", "o")
    )

    levels = [item.level for item in recommend.report(make_config(tmp_path))]
    assert levels == [
        "warn",
        "info",
        "ok",
        "ok",
        "ok",
        "ok",
        "ok",
        "ok",
        "ok",
        "ok",
        "ok",
        "ok",
    ]


def test_persistenced_state_active(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        recommend.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, stdout="active\n"),
    )
    assert recommend.persistenced_state() == "active"


def test_persistenced_state_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: None)
    assert recommend.persistenced_state() is None


def test_integrated_gpu_name(monkeypatch) -> None:
    monkeypatch.setattr(recommend, "_integrated_gpu", lambda: "AMD")
    assert recommend.integrated_gpu_name() == "AMD Radeon"
    monkeypatch.setattr(recommend, "_integrated_gpu", lambda: "Intel")
    assert recommend.integrated_gpu_name() == "Intel"
    monkeypatch.setattr(recommend, "_integrated_gpu", lambda: None)
    assert recommend.integrated_gpu_name() is None


def test_hybrid_warns_and_points_to_graphics(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend, "integrated_gpu_name", lambda: "AMD Radeon")
    monkeypatch.setattr(
        recommend, "_kernel_log", lambda *_: "NVRM: Xid (PCI:0000:01:00): 109, CTX SWITCH TIMEOUT"
    )
    item = recommend._check_hybrid_gpu(make_config(tmp_path))
    assert item.level == "warn"
    assert item.action_id == ""
    assert "Graphics" in item.action
    assert any("DXVK_FILTER_DEVICE_NAME" in command for command in item.commands)


def test_gpu_preference(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    assert recommend.gpu_preference(config) == "auto"
    config.env["DXVK_FILTER_DEVICE_NAME"] = "NVIDIA"
    assert recommend.gpu_preference(config) == "nvidia"
    config.env["DXVK_FILTER_DEVICE_NAME"] = "AMD Radeon"
    assert recommend.gpu_preference(config) == "integrated"


def test_hybrid_ok_when_pinned(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend, "integrated_gpu_name", lambda: "AMD Radeon")
    config = make_config(tmp_path)
    config.env["DXVK_FILTER_DEVICE_NAME"] = "AMD Radeon"
    assert recommend._check_hybrid_gpu(config).level == "ok"


def test_hybrid_info_without_trouble(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recommend, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend, "integrated_gpu_name", lambda: "AMD Radeon")
    monkeypatch.setattr(recommend, "_kernel_log", lambda *_: "")
    assert recommend._check_hybrid_gpu(make_config(tmp_path)).level == "info"


def test_wow_tuning_tip_when_maxfpsbk_missing(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    wtf = config.prefix / "drive_c/Program Files (x86)/World of Warcraft/_classic_beta_/WTF"
    wtf.mkdir(parents=True)
    (wtf / "Config.wtf").write_text('SET GxApi "D3D11"\n', encoding="utf-8")
    item = recommend._check_wow_tuning(config)
    assert item.level == "info"
    assert any("maxFPSBK" in command for command in item.commands)


def test_wow_tuning_ok_without_install(tmp_path: Path) -> None:
    assert recommend._check_wow_tuning(make_config(tmp_path)).level == "ok"


def test_wow_forever_flags_known_bugs(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    wtf = config.prefix / "drive_c/Program Files (x86)/World of Warcraft/_classic_beta_/WTF"
    wtf.mkdir(parents=True)
    (wtf / "Config.wtf").write_text('SET GxApi "D3D11"\n', encoding="utf-8")
    item = recommend._check_wow_forever(config)
    assert item.level == "info"
    assert "69913" in item.title


def test_wow_forever_ok_without_beta(tmp_path: Path) -> None:
    assert recommend._check_wow_forever(make_config(tmp_path)).level == "ok"


# --- Vulkan capability ---------------------------------------------------
def test_vulkan_could_not_be_checked(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: None)
    assert recommend._check_vulkan().level == "info"


def test_vulkan_no_device(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(recommend, "_vulkan_versions_and_names", lambda: ([], []))
    assert recommend._check_vulkan().level == "warn"


def test_vulkan_too_old(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend, "_vulkan_versions_and_names", lambda: ([(1, 2, 200)], ["AMD Radeon"])
    )
    monkeypatch.setattr(recommend, "_has_32bit_vulkan", lambda: True)
    item = recommend._check_vulkan()
    assert item.level == "warn"
    assert "old" in item.title.lower()


def test_vulkan_software_only(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend,
        "_vulkan_versions_and_names",
        lambda: ([(1, 4, 354)], ["llvmpipe (LLVM 22)"]),
    )
    monkeypatch.setattr(recommend, "_has_32bit_vulkan", lambda: True)
    assert "software" in recommend._check_vulkan().title.lower()


def test_vulkan_missing_32bit(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend, "_vulkan_versions_and_names", lambda: ([(1, 4, 354)], ["AMD Radeon"])
    )
    monkeypatch.setattr(recommend, "_has_32bit_vulkan", lambda: False)
    assert "32-bit" in recommend._check_vulkan().title


def test_vulkan_ok(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend, "_vulkan_versions_and_names", lambda: ([(1, 4, 354)], ["AMD Radeon"])
    )
    monkeypatch.setattr(recommend, "_has_32bit_vulkan", lambda: True)
    assert recommend._check_vulkan().level == "ok"


# --- Proton auto-download fallback ---------------------------------------
def test_proton_auto_download_when_umu_present(monkeypatch) -> None:
    monkeypatch.setattr(recommend.proton, "all_builds", lambda: [])
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/umu-run")
    item = recommend._check_proton()
    assert item.level == "info"
    assert "download" in (item.detail + item.action).lower()


def test_proton_warns_without_umu(monkeypatch) -> None:
    monkeypatch.setattr(recommend.proton, "all_builds", lambda: [])
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: None)
    assert recommend._check_proton().level == "warn"
