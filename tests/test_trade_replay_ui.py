"""Offline replay controls and production entrypoints share immutable results."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import finish_background_jobs, navigate


REPLAY_APP = '''
import numpy as np
import pandas as pd
import streamlit as st
from quant_lab.backtest import BacktestConfig
from quant_lab.us_price_research import USPriceConfig
from quant_lab.strategy import StrategySpec
from quant_lab.research import run_experiment
from quant_lab.ui_trade_replay import render_trade_replay
market = st.session_state.get("test_market", "A 股")
if "fixture" not in st.session_state:
    close = 20 + np.sin(np.arange(80) / 3) * 3
    raw = pd.DataFrame({"date": pd.bdate_range("2026-01-05", periods=80),
        "open": close - .2, "high": close + 1, "low": close - 1,
        "close": close, "volume": 1000., "amount": close * 1000})
    raw.loc[3, "volume"] = 0
    spec = StrategySpec("single_ma", 2, 3)
    config = USPriceConfig() if market == "美股" else BacktestConfig(market=market, lot_size=1, limit_pct=None)
    result = run_experiment(raw, raw, spec, config)
    st.session_state["fixture"] = (raw, spec, config, result)
raw, spec, config, result = st.session_state["fixture"]
symbol = st.selectbox("实验", ("ONE", "TWO"))
show = st.checkbox("显示结果", value=True)
stale = st.checkbox("上次成功结果", value=False)
if show:
    render_trade_replay(raw, result, spec, config, market=market, symbol=symbol,
        currency={"A 股":"CNY", "港股":"HKD", "美股":"USD"}[market],
        adjustment="前复权", query=symbol, slot="test", stale=stale)
'''


def button(app, label):
    return next(item for item in app.button if item.label == label)


def date_control(app):
    return next(item for item in app.selectbox if item.label == "交易日")


def test_empty_orders_still_allow_daily_review():
    source = REPLAY_APP.replace("20 + np.sin(np.arange(80) / 3) * 3", "np.full(80, 20.)")
    app = AppTest.from_string(source, default_timeout=20).run()
    raw = app.session_state["fixture"][0]
    assert not app.exception and not app.error
    assert date_control(app).value == raw.date.iloc[0].date()
    assert all(button(app, label).disabled for label in ("上一笔", "下一笔", "定位最大回撤"))
    assert any("此区间没有订单" in item.value for item in app.info)
    date_control(app).set_value(raw.date.iloc[-1].date()).run()
    assert date_control(app).value == raw.date.iloc[-1].date() and not app.exception


@pytest.mark.parametrize("market", ["A 股", "港股", "美股"])
def test_manual_controls_drawdown_page_restore_and_isolation(monkeypatch, market):
    from quant_lab import ui_trade_replay
    calls = []
    original = ui_trade_replay.build_trade_replay
    def counted(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(ui_trade_replay, "build_trade_replay", counted)
    app = AppTest.from_string(REPLAY_APP, default_timeout=20)
    app.session_state["test_market"] = market
    app.run()
    assert not app.exception and not app.error
    first = date_control(app).value
    assert button(app, "上一笔").disabled
    assert any("零成交量" in item.value for item in app.warning)
    button(app, "下一笔").click().run()
    second = date_control(app).value
    assert second > first and not app.exception
    button(app, "上一笔").click().run()
    assert date_control(app).value == first
    raw, spec, config, result = app.session_state["fixture"]
    day = raw.date.iloc[10].date()
    date_control(app).set_value(day).run()
    assert date_control(app).value == day
    next(item for item in app.checkbox if item.label == "显示结果").uncheck().run()
    next(item for item in app.checkbox if item.label == "显示结果").check().run()
    assert date_control(app).value == day
    button(app, "定位最大回撤").click().run()
    replay = app.session_state["_trade_replay_test"][2]
    assert date_control(app).value == raw.date.iloc[replay.drawdown.trough].date()
    assert any("最大回撤区间" in item.value for item in app.markdown)
    next(item for item in app.checkbox if item.label == "上次成功结果").check().run()
    assert any("上次成功计算" in item.value for item in app.warning)
    assert len(calls) == 1
    app.selectbox[0].set_value("TWO").run()
    assert date_control(app).value == first
    assert len(calls) == 2 and not app.exception


@pytest.mark.parametrize("market", ["A 股", "港股", "美股"])
def test_actual_backtest_entrypoint_exposes_replay_without_new_fetches(monkeypatch, market):
    from quant_lab.data import HistoryBundle
    from test_us_price_research import reference
    item = reference(n=80)
    calls = []
    def fetch(*args, **kwargs):
        calls.append(1)
        frame = item.frame.copy()
        frame["amount"] = frame.close * frame.volume
        return HistoryBundle(frame, market, "600519" if market == "A 股" else "00700",
                             "离线回放验收", "CNY" if market == "A 股" else "HKD", "")
    monkeypatch.setattr("quant_lab.ui.fetch_history", fetch)
    monkeypatch.setattr("quant_lab.us_sources.fetch_sina_reference", lambda *args, **kwargs: item)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    app.sidebar.selectbox(key="market_selection").set_value(market).run()
    next(item for item in app.sidebar.button if item.label == "加载真实历史日线").click().run()
    finish_background_jobs(app)
    navigate(app, "历史回测")
    button(app, "运行真实美股价格回测" if market == "美股" else "运行历史回测").click().run()
    finish_background_jobs(app, timeout=30)
    assert not app.exception and not app.error
    assert any(item.value == "#### 交易回放" for item in app.markdown)
    fetched = len(calls)
    date_control(app).set_value(item.frame.date.iloc[-1].date()).run()
    assert len(calls) == fetched
    assert not app.session_state["_task_tickets"] and not app.exception
