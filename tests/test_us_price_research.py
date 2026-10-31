"""US price-only fidelity is explicit; AH and strict-US contracts stay intact."""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from quant_lab.backtest import BacktestConfig
from quant_lab.comparison import compare_inputs
from quant_lab.research_validation import ValidationRecipe
from quant_lab.strategy import StrategySpec
from quant_lab.us_market import us_schedule
from quant_lab.us_sources import USPriceReference, USSourceObservation
from quant_lab.us_price_research import (
    USPriceConfig, validate_price_input, run_us_price_experiment, collect_us_price_comparison,
    run_us_price_portfolio, run_us_price_validation, price_report,
)
from conftest import finish_background_jobs, navigate


def reference(symbol="AAPL", n=210, scale=1.):
    dates = us_schedule(pd.Timestamp("2025-01-02").date(), pd.Timestamp("2025-12-01").date()).index[:n]
    close = (10 + np.arange(len(dates))*.1)*scale
    frame = pd.DataFrame({"date": dates, "open": close, "high": close+.1*scale,
                          "low": close-.1*scale, "close": close, "volume": 1000})
    return ref_frame(frame, symbol)


def ref_frame(frame, symbol="AAPL"):
    digest = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    return USPriceReference(USSourceObservation(symbol, "隔离单元测试输入（不是实际市场行情）",
        "2025-01-02", "2025-12-01", str(frame.date.iloc[0].date()), str(frame.date.iloc[-1].date()),
        len(frame), "2026-10-30T00:00:00+00:00", digest), frame, len(frame), (), (), 0)


def test_us_price_single_hand_calculation_and_distinct_strict_contract():
    item = reference(n=35)
    config = USPriceConfig(initial_cash=100, slippage_bps=0)
    result = run_us_price_experiment(item, StrategySpec("single_ma", 2, 3), config)
    # Close of row 2 is first > 3-day MA; earliest fill is row 3 at 10.3.
    buy = result.strategy.orders.iloc[0]
    assert buy.decision_date == item.frame.date.iloc[2]
    assert buy.date == item.frame.date.iloc[3] and buy.shares == 9
    assert result.strategy.equity.equity.iloc[-1] == pytest.approx(127.9)
    assert result.audit_id.startswith("us-price-v1:")
    assert not item.observation.actions_complete and not item.observation.retention_verified
    with pytest.raises(ValueError):
        BacktestConfig(market="美股")  # AH validation has not been weakened
    with pytest.raises(ValueError):
        USPriceConfig(lot_size=100)
    summary = json.loads(price_report(item, result, StrategySpec("single_ma", 2, 3), config, .7))
    assert not summary["raw_prices_included"] and not summary["offline_replay_available"]
    assert summary["costs"]["market"] == "美股" and not summary["retention"]["allowed"]


def test_us_price_rejects_stale_tampered_missing_unfinished_and_jumps():
    item = reference(n=40)
    with pytest.raises(ValueError, match="失败"):
        validate_price_input(replace(item, update_error="offline"))
    with pytest.raises(ValueError, match="USD"):
        validate_price_input(replace(item, currency="HKD"))
    with pytest.raises(ValueError, match="指纹"):
        validate_price_input(replace(item, observation=replace(item.observation, content_sha256="bad")))
    with pytest.raises(ValueError, match="缺失"):
        validate_price_input(ref_frame(item.frame.drop(index=10).reset_index(drop=True)))
    assert len(validate_price_input(ref_frame(item.frame.drop(index=10).reset_index(drop=True)), execution=False)) == 39
    unfinished = replace(item, observation=replace(item.observation, received_at="2025-01-02T12:00:00+00:00"))
    with pytest.raises(ValueError, match="收市"):
        validate_price_input(unfinished)
    frame = item.frame.copy()
    frame.loc[20:, ["open", "high", "low", "close"]] *= .25
    with pytest.raises(ValueError, match="40%"):
        validate_price_input(ref_frame(frame))


def test_us_price_comparison_portfolio_train_only_weights_and_gap_guard(monkeypatch):
    from quant_lab import us_price_research as service
    refs = {"AAPL": reference(), "MSFT": reference("MSFT", scale=2)}
    calls = []
    def fetch(symbol, start, end, **kwargs):
        calls.append((symbol, kwargs))
        return refs[symbol]
    monkeypatch.setattr(service, "fetch_sina_reference", fetch)
    inputs = collect_us_price_comparison(("aapl", "msft"), pd.Timestamp("2025-01-02").date(),
                                         pd.Timestamp("2025-12-01").date(), force=True, cache_namespace="isolated")
    assert all(kwargs == {"force": True, "cache_namespace": "isolated"} for _, kwargs in calls)
    compared = compare_inputs(inputs, "AAPL", 20)
    assert inputs.currency == "USD" and compared.normalized.iloc[0].eq(100).all()
    assert compared.risk_return.price_return["AAPL"] == pytest.approx(2.09)
    output = run_us_price_portfolio(inputs, USPriceConfig(initial_cash=1000, slippage_bps=0), .7, "monthly")
    assert set(output.runs) == {"等权", "逆波动率"}
    assert output.weights["等权"].to_list() == [.5, .5]
    for run in output.runs.values():
        assert run.equity.cash.ge(0).all()
        assert (run.positions.shares % 1).eq(0).all()
        assert run.manifest["algorithm"] == "us-price-portfolio-v1"
        assert run.orders.date.iloc[0] == pd.Timestamp(output.test_first_date)
        assert run.orders.decision_date.iloc[0] == pd.Timestamp(output.train_last_date)
    damaged = dict(inputs.bundles)
    damaged["MSFT"] = replace(damaged["MSFT"], frame=damaged["MSFT"].frame.drop(index=180))
    with pytest.raises(ValueError, match="缺失"):
        run_us_price_portfolio(replace(inputs, bundles=damaged))


def test_us_price_validation_uses_ohlcv_without_inventing_turnover():
    item = reference(n=155)
    recipe = ValidationRecipe(StrategySpec("single_ma", 2, 5), USPriceConfig(),
                               (2, 3), (5, 10), .7, 60, 20, 2)
    result = run_us_price_validation(item, recipe)
    assert "amount" not in item.frame
    assert len(result.scan) == 4 and len(result.folds) == 2
    assert result.stress.status.eq("success").all()
    assert result.manifest["versions"]["execution"] == "us-price-cost-v1"
    assert result.audit_id.startswith("us-price-validation-v1:")
    assert (result.folds.train_end < result.folds.test_start).all()


def test_us_price_workspace_whitelist_keeps_parameters_without_data(tmp_path):
    from quant_lab.workspaces import WorkspaceStore
    store = WorkspaceStore(tmp_path/"workspaces.json")
    store.save("多股票比较", {"market_selection":"美股", "compare_market":"美股",
        "us_compare_codes":"aapl，msft", "us_compare_baseline":"msft", "us_compare_window":20,
        "us_price_bt_cash":20000., "us_research_mode":"真实行情价格研究",
        "us_compare_start":"2025-01-02", "raw_history":"private", "api_key":"secret"})
    saved = store.load()["profiles"]["多股票比较"]
    assert saved["us_compare_codes"] == "AAPL,MSFT" and saved["us_compare_baseline"] == "MSFT"
    assert saved["us_price_bt_cash"] == 20000.
    assert "raw_history" not in saved and "api_key" not in saved
    with pytest.raises(ValueError, match="整数"):
        store.save("多股票比较", {"us_compare_window": 20.5})


def test_real_us_ui_backtest_comparison_portfolio_and_teaching_separation(monkeypatch):
    from quant_lab import us_price_research as service
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py", default_timeout=30).run()
    item = reference()
    monkeypatch.setattr("quant_lab.us_sources.fetch_sina_reference", lambda *args, **kwargs: item)
    navigate(app, "美股研究")
    next(button for button in app.sidebar.button if button.label == "加载真实历史日线").click().run()
    finish_background_jobs(app)
    assert app.radio(key="us_research_mode").value == "真实行情价格研究"
    app.radio(key="research_page").set_value("历史回测").run()
    app.button(key="FormSubmitter:us_price_backtest-运行真实美股价格回测").click().run()
    finish_background_jobs(app, timeout=30)
    assert not app.exception and not app.error
    assert any(metric.label == "策略价格收益" for metric in app.metric)
    assert "公司行动/结算未模拟" in app.session_state["_current_ai_context"]["data_status"]
    monkeypatch.setattr(service, "fetch_sina_reference", lambda symbol, *args, **kwargs: reference(symbol, scale=2 if symbol == "MSFT" else 1))
    app.sidebar.radio(key="nav_section").set_value("多股票比较").run()
    app.button(key="FormSubmitter:us_price_comparison-加载比较").click().run()
    finish_background_jobs(app, timeout=30)
    assert not app.exception and not app.error
    assert app.session_state["us_price_comparison_result"][1][0].currency == "USD"
    app.button(key="FormSubmitter:us_price_portfolio-运行真实美元价格组合").click().run()
    finish_background_jobs(app, timeout=30)
    assert not app.exception and not app.error
    assert set(app.session_state["us_price_portfolio_result"][1].runs) == {"等权", "逆波动率"}
    app.selectbox(key="us_compare_detail").set_value("MSFT").run()
    app.session_state["us_compare_codes"] = "AAPL,BRK.B"
    app.run()
    app.button(key="FormSubmitter:us_price_comparison-加载比较").click().run()
    finish_background_jobs(app, timeout=30)
    assert not app.exception and not app.error
    assert app.selectbox(key="us_compare_detail").value == "AAPL"
    navigate(app, "美股研究")
    app.radio(key="us_research_mode").set_value("离线教学样本").run()
    assert any("非真实美股行情" in item.value for item in app.info)
    assert app.session_state["_current_ai_context"]["data_status"].startswith("离线教学")
