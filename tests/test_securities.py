"""Directory search is offline, normalized and preserves verified snapshots."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from conftest import select_security

from quant_lab import securities


def test_bundled_directory_has_major_stocks_and_separate_markets(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    a = securities.security_directory("A 股")
    hk = securities.security_directory("港股")
    assert len(a.rows) > 5000 and len(hk.rows) > 2000
    assert dict(a.rows)["600519"] == "贵州茅台"
    assert dict(hk.rows)["00700"] == "腾讯控股"
    assert all(len(code) == 6 for code, _ in a.rows)
    assert all(len(code) == 5 for code, _ in hk.rows)
    assert a.rows[0][0] == "600519" and hk.rows[0][0] == "00700"


def test_failed_refresh_keeps_timestamp_and_can_retry(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    old = securities.security_directory("A 股")
    def fail(*args):
        raise ConnectionError("offline")
    monkeypatch.setattr(securities, "fetch_directory", fail)
    failed = securities.security_directory("A 股", force=True)
    assert failed.rows == old.rows and failed.received_at == old.received_at and failed.error
    new = securities.validate_directory({"market": "A 股", "source": "test basic info",
        "received_at": datetime.now(timezone.utc).isoformat(), "rows": [["SZ000001", "平安银行"]]}, "A 股")
    monkeypatch.setattr(securities, "fetch_directory", lambda *args: new)
    refreshed = securities.security_directory("A 股", force=True)
    assert refreshed == new
    assert (tmp_path / "securities" / "a_shares.json").exists()


def test_conflicting_identities_rejected():
    with pytest.raises(ValueError, match="冲突"):
        securities.validate_directory({"market": "港股", "source": "test",
            "received_at": datetime.now(timezone.utc).isoformat(),
            "rows": [["700", "腾讯控股"], ["00700.HK", "错误名称"]]}, "港股")


def test_corrupt_user_directory_is_visible_and_not_reused(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    path = tmp_path / "securities" / "a_shares.json"
    path.parent.mkdir()
    path.write_text('{"market":"港股"}', encoding="utf-8")
    directory = securities.security_directory("A 股")
    assert directory.error and "校验失败" in directory.error
    assert dict(directory.rows)["600519"] == "贵州茅台"
    assert path.read_text(encoding="utf-8") == '{"market":"港股"}'


def test_candidate_fills_code_and_market_switch_is_isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    select_security(app, "symbol_A 股", "000001")
    assert not app.exception and app.session_state["symbol_A 股"] == "000001"
    app.sidebar.selectbox(key="market_selection").select("港股").run()
    select_security(app, "symbol_港股", "00941")
    assert not app.exception and app.session_state["symbol_港股"] == "00941"
    app.sidebar.selectbox(key="market_selection").select("A 股").run()
    assert app.session_state["symbol_A 股"] == "000001"
    assert not app.sidebar.text_input
    assert not app.exception


@pytest.mark.parametrize("code,can_load", [("700", True), ("HK09988", True), ("不是代码", False)])
def test_custom_code_validation_without_directory(monkeypatch, code, can_load):
    def unavailable(*args):
        raise OSError("目录暂不可用")
    monkeypatch.setattr("quant_lab.ui_security_picker.security_directory", unavailable)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30)
    # Seed a fresh widget state; real typing is covered by WebView acceptance.
    app.session_state["market_selection"] = "港股"
    app.session_state["symbol_港股"] = code
    app.run()
    assert not app.exception
    assert any("目录暂不可用" in item.value for item in app.warning)
    assert next(w for w in app.button if w.label == "加载真实历史日线").disabled != can_load
    if not can_load:
        assert any("港股可输入 1–5 位数字" in item.value for item in app.caption)
