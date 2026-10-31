"""Common market controls must keep US input and active research in sync."""
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import finish_background_jobs, navigate
from quant_lab.ui_security_picker import commit_selection
from quant_lab.workspaces import restore_values

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_us_picker_validates_manual_tickers_and_class_shares():
    assert commit_selection("美股", "us_price_symbol", False, ["brk.b"]) == "BRK.B"
    assert commit_selection("美股", "us_compare_codes", True, ["aapl", "MSFT", "AAPL"]) == "AAPL,MSFT"
    assert commit_selection("美股", "us_price_symbol", False, []) == ""
    for invalid in (["../AAPL"], ["AAPL", "MSFT"], [42]):
        with pytest.raises(ValueError):
            commit_selection("美股", "us_price_symbol", False, invalid)


def test_legacy_us_preset_restores_shared_controls_without_overwriting_new_values():
    legacy = {"market_selection": "美股", "us_price_start": "2024-01-02",
              "us_price_end": "2025-01-02", "us_price_period": 3, "us_price_page": "统计分析"}
    values = restore_values(legacy)
    assert values["history_start"] == date(2024, 1, 2)
    assert values["history_preset"] == "3 年"
    assert values["research_page"] == "统计与机器学习"
    values = restore_values({**legacy, "history_start": "2025-02-03", "research_page": "历史回测"})
    assert values["history_start"] == date(2025, 2, 3)
    assert values["research_page"] == "历史回测"


def test_shared_controls_no_automatic_fetch_and_us_research_rejects_old_query(monkeypatch):
    from test_us_price_research import reference
    calls = []
    def fetch(symbol, *args, **kwargs):
        calls.append((symbol, kwargs["force"]))
        return reference(symbol)
    monkeypatch.setattr("quant_lab.us_sources.fetch_sina_reference", fetch)
    app = AppTest.from_file(APP, default_timeout=30).run()
    for market in ("A 股", "港股", "美股"):
        app.sidebar.selectbox(key="market_selection").set_value(market).run()
        assert {"开始日期", "结束日期"} <= {item.label for item in app.sidebar.date_input}
        assert any(item.label == "快捷历史区间" for item in app.sidebar.selectbox)
        assert any(item.label == "加载真实历史日线" for item in app.sidebar.button)
        assert not app.exception
    navigate(app, "美股研究")
    assert app.radio(key="research_page").options == ["策略信号", "历史回测", "风险与组合", "统计分析", "专业验证"]
    assert not calls
    next(item for item in app.sidebar.button if item.label == "加载真实历史日线").click().run()
    finish_background_jobs(app)
    assert calls == [("AAPL", False)] and not app.error
    assert app.session_state["_current_ai_context"]["symbol"] == "AAPL"
    original = app.session_state["us_price_reference"]
    app.session_state["us_price_symbol"] = "MSFT"
    app.run()
    assert "symbol" not in app.session_state["_current_ai_context"]
    assert app.session_state["us_price_reference"] == original
    assert len(calls) == 1
    app.button(key="us_history_refresh").click().run()
    finish_background_jobs(app)
    assert calls[-1] == ("MSFT", True)
    app.sidebar.date_input(key="history_start").set_value(date(2020, 1, 2)).run()
    assert "symbol" not in app.session_state["_current_ai_context"]
    assert len(calls) == 2 and not app.exception
    # A first failed load on the research page must surface the actual error.
    def fail(*args, **kwargs):
        raise ValueError("测试来源错误")
    monkeypatch.setattr("quant_lab.us_sources.fetch_sina_reference", fail)
    next(item for item in app.sidebar.button if item.label == "加载真实历史日线").click().run()
    finish_background_jobs(app)
    assert any("测试来源错误" in item.value for item in app.error)
    assert "symbol" not in app.session_state["_current_ai_context"]
