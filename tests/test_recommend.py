from __future__ import annotations

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


def test_nvidia_info_without_nvidia(monkeypatch) -> None:
    monkeypatch.setattr(recommend.gpu, "nvidia_driver_info", lambda: (None, False))
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
        recommend, "_check_render_scale", lambda _c: recommend.Recommendation("w", "ok", "o")
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
    ]


# --- Vulkan capability ---------------------------------------------------
def test_vulkan_could_not_be_checked(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: None)
    assert recommend._check_vulkan().level == "info"


def test_vulkan_no_device(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(recommend.gpu, "vulkan_versions_and_names", lambda: ([], []))
    assert recommend._check_vulkan().level == "warn"


def test_vulkan_too_old(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend.gpu, "vulkan_versions_and_names", lambda: ([(1, 2, 200)], ["AMD"])
    )
    monkeypatch.setattr(recommend.gpu, "has_32bit_vulkan", lambda: True)
    item = recommend._check_vulkan()
    assert item.level == "warn"
    assert "old" in item.title.lower()


def test_vulkan_software_only(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend.gpu,
        "vulkan_versions_and_names",
        lambda: ([(1, 4, 354)], ["llvmpipe (LLVM 22)"]),
    )
    monkeypatch.setattr(recommend.gpu, "has_32bit_vulkan", lambda: True)
    assert "software" in recommend._check_vulkan().title.lower()


def test_vulkan_missing_32bit(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend.gpu, "vulkan_versions_and_names", lambda: ([(1, 4, 354)], ["AMD"])
    )
    monkeypatch.setattr(recommend.gpu, "has_32bit_vulkan", lambda: False)
    assert "32-bit" in recommend._check_vulkan().title


def test_vulkan_ok(monkeypatch) -> None:
    monkeypatch.setattr(recommend.shutil, "which", lambda _name: "/usr/bin/vulkaninfo")
    monkeypatch.setattr(
        recommend.gpu, "vulkan_versions_and_names", lambda: ([(1, 4, 354)], ["AMD"])
    )
    monkeypatch.setattr(recommend.gpu, "has_32bit_vulkan", lambda: True)
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


def test_nvidia_fault_warns_without_system_changes(monkeypatch) -> None:
    monkeypatch.setattr(recommend.gpu, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(
        recommend.gpu, "kernel_log", lambda *_: "NVRM: Xid (PCI:0000:01:00): 109, CTX SWITCH"
    )
    item = recommend._check_nvidia()[0]
    assert item.level == "warn"
    assert "Xid 109" in item.title
    assert not any("sudo" in command or "rebase" in command for command in item.commands)


def test_nvidia_memory_error(monkeypatch) -> None:
    monkeypatch.setattr(recommend.gpu, "nvidia_driver_info", lambda: ("615.71.09", False))
    monkeypatch.setattr(recommend.gpu, "kernel_log", lambda *_: "NVRM: ... NV_ERR_NO_MEMORY")
    assert "NV_ERR_NO_MEMORY" in recommend._check_nvidia()[0].title


def test_nvidia_open_module_without_fault_is_ok(monkeypatch) -> None:
    monkeypatch.setattr(recommend.gpu, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend.gpu, "kernel_log", lambda *_: "")
    item = recommend._check_nvidia()[0]
    assert item.level == "ok"
    assert "open kernel module" in item.title


def test_hybrid_is_informational(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recommend.gpu, "nvidia_driver_info", lambda: ("615.71.09", True))
    monkeypatch.setattr(recommend.gpu, "integrated_gpu_name", lambda: "AMD")
    config = make_config(tmp_path)
    item = recommend._check_hybrid_gpu(config)
    assert item.level == "ok"
    assert "games on auto" in item.title
    config.env["DXVK_FILTER_DEVICE_NAME"] = "AMD"
    assert "games on AMD" in recommend._check_hybrid_gpu(config).title


def _wow_config(config, edition: str, text: str) -> Path:
    wtf = config.prefix / f"drive_c/Program Files (x86)/World of Warcraft/{edition}/WTF"
    wtf.mkdir(parents=True)
    path = wtf / "Config.wtf"
    path.write_text(text, encoding="utf-8")
    return path


def test_render_scale_flags_supersampling(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _wow_config(config, "_classic_beta_", 'SET gxApi "D3D11"\nSET RenderScale "1.383333"\n')
    item = recommend._check_render_scale(config)
    assert item.level == "warn"
    assert "138 %" in item.title
    assert "_classic_beta_" in item.title
    assert item.commands == ('SET RenderScale "1"',)


def test_render_scale_ok_at_or_below_native(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _wow_config(config, "_retail_", 'SET RenderScale "1.000000"\n')
    _wow_config(config, "_classic_", 'SET RenderScale "0.8"\n')
    assert recommend._check_render_scale(config).level == "ok"


def test_render_scale_default_when_unset(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _wow_config(config, "_retail_", 'SET gxApi "D3D11"\n')
    assert recommend._check_render_scale(config).level == "ok"
    assert recommend._check_render_scale(make_config(tmp_path / "none")).level == "ok"
