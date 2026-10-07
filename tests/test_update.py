from __future__ import annotations

from frostfireinstaller.core import update


def test_parse_version_orders() -> None:
    assert update.parse_version("v0.2.15") == (0, 2, 15)
    assert update.parse_version("0.2.9") < update.parse_version("0.2.10")
    assert update.parse_version("1.0.0-rc1") == (1, 0, 0)


def test_check_returns_newer(monkeypatch) -> None:
    payload = {
        "tag_name": "v99.0.0",
        "html_url": "https://example.test/tag",
        "body": "notes",
        "assets": [
            {
                "name": "frostfireinstaller-99.0.0-py3-none-any.whl",
                "browser_download_url": "https://example.test/x.whl",
            }
        ],
    }
    monkeypatch.setattr(update, "_get_json", lambda _url: payload)
    release = update.check()
    assert release is not None
    assert release.version == "99.0.0"
    assert release.wheel_url == "https://example.test/x.whl"


def test_check_none_when_current(monkeypatch) -> None:
    monkeypatch.setattr(update, "_get_json", lambda _url: {"tag_name": "v0.0.1", "assets": []})
    assert update.check() is None


def test_can_self_update_false_without_venv(monkeypatch) -> None:
    monkeypatch.setattr(update.sys, "prefix", update.sys.base_prefix)
    assert update.can_self_update() is False


def test_auto_check_enabled_env(monkeypatch) -> None:
    monkeypatch.setenv("FROSTFIREINSTALLER_NO_UPDATE_CHECK", "1")
    assert update.auto_check_enabled() is False
    monkeypatch.delenv("FROSTFIREINSTALLER_NO_UPDATE_CHECK")
    assert update.auto_check_enabled() is True
