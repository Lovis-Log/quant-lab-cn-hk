"""Slow-provider integration proves the UI returns before network completion."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import pandas as pd
from streamlit.testing.v1 import AppTest
from conftest import navigate

from quant_lab.data import HistoryBundle
from conftest import finish_background_jobs


def bundle(symbol="600519"):
    frame = pd.DataFrame({"date": pd.to_datetime(["2026-10-08", "2026-10-09"]),
        "open": [10., 11.], "high": [12., 13.], "low": [9., 10.],
        "close": [11., 12.], "volume": [100., 100.], "amount": [1100., 1200.]})
    return HistoryBundle(frame, "A 股", symbol, "离线教学样本", "CNY", "",
                         received_at=datetime(2026, 10, 9, tzinfo=timezone.utc))


def test_slow_request_allows_page_switch_and_late_old_query_is_discarded(monkeypatch):
    gate, entered = Event(), Event()
    def slow(market, symbol, *args, **kwargs):
        entered.set()
        gate.wait(8)
        return bundle(symbol)
    monkeypatch.setattr("quant_lab.ui.fetch_history", slow)
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=5).run()
    try:
        app.sidebar.button[0].click().run()
        assert entered.wait(1)
        assert not app.exception
        assert "history" in app.session_state["_task_tickets"]
        assert any("ql-loading-placeholder" in item.value for item in app.get("html"))
        navigate(app, "Quant Academy")
        assert any("Quant Academy" in item.value for item in app.subheader)
        app.sidebar.selectbox(key="symbol_A 股").set_value("000001").run()
        gate.set()
        finish_background_jobs(app)
        assert "loaded_bundle" not in app.session_state or app.session_state["loaded_bundle"] is None
        assert not app.exception
    finally:
        gate.set()


def test_cancel_retains_previous_success_and_its_timestamp(monkeypatch):
    first = bundle()
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args, **kwargs: first)
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=5).run()
    app.sidebar.button[0].click().run()
    finish_background_jobs(app)
    gate, entered = Event(), Event()
    def slow(*args, **kwargs):
        entered.set()
        gate.wait(8)
        return replace(first, received_at=datetime.now(timezone.utc))
    monkeypatch.setattr("quant_lab.ui.fetch_history", slow)
    try:
        app.button(key="history_refresh").click().run()
        assert entered.wait(1)
        app.button(key="cancel_job_history").click().run()
        gate.set()
        app.run()
        assert app.session_state["loaded_bundle"].received_at == first.received_at
        assert "history" not in app.session_state["_task_tickets"]
        assert not app.exception
    finally:
        gate.set()


def test_completed_research_on_another_page_stops_polling_and_can_be_opened(monkeypatch):
    data = pd.DataFrame({"date": pd.bdate_range("2026-01-02", periods=100),
        "open": 100., "high": 101., "low": 99., "close": 100., "volume": 100., "amount": 10000.})
    history = replace(bundle(), frame=data)
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args, **kwargs: history)
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=8).run()
    app.sidebar.button[0].click().run()
    finish_background_jobs(app)
    navigate(app, "历史回测")
    next(item for item in app.button if item.label == "运行历史回测").click().run()
    navigate(app, "Quant Academy")
    finish_background_jobs(app)
    assert not app.session_state["_task_tickets"]
    assert "backtest" in app.session_state["_finished_task_tickets"]
    navigate(app, "历史回测")
    assert any(item.label == "保存实验" for item in app.button)
    assert "backtest" not in app.session_state["_finished_task_tickets"]
    assert not app.exception


def test_maximized_workspace_switches_to_requested_dock():
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=8).run()
    app.button(key="manual_panel_maximize").click().run()
    assert app.session_state["maximized_panel"] == "manual"
    app.button(key="deepseek_panel_toggle").click().run()
    assert app.session_state["maximized_panel"] == "deepseek"
    assert app.button(key="deepseek_panel_close")
    app.button(key="manual_panel_toggle").click().run()
    assert app.session_state["maximized_panel"] == "manual"
    assert app.button(key="manual_panel_close")
    assert not app.exception
