"""Preset/custom date edits are local until explicit history submission."""

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_ten_year_preset_custom_dates_and_invalid_order_do_not_fetch(monkeypatch):
    calls = []
    monkeypatch.setattr("quant_lab.ui.fetch_history", lambda *args, **kwargs: calls.append(args))
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=10).run()
    app.sidebar.selectbox(key="history_preset").set_value("10 年").run()
    end = app.session_state["history_end"]
    start = app.session_state["history_start"]
    assert start.year == end.year-10 and not calls
    app.sidebar.date_input(key="history_start").set_value(date(2020,1,2)).run()
    assert app.session_state["history_preset"] == "自定义"
    assert app.session_state["history_start"] == date(2020,1,2)
    app.run()
    assert app.session_state["history_start"] == date(2020,1,2) and not calls
    app.sidebar.date_input(key="history_end").set_value(date(2019,1,2)).run()
    load = next(item for item in app.sidebar.button if item.label == "加载真实历史日线")
    assert load.disabled
    assert any("开始日期不能晚于" in item.value for item in app.warning)
    assert not calls and not app.exception
