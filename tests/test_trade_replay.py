"""Replay explains existing ledgers, with hand-calculated money movements."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from quant_lab.backtest import BacktestConfig, run_backtest
from quant_lab.metrics import performance_stats
from quant_lab.strategy import StrategySpec, build_signals
from quant_lab.trade_replay import build_trade_replay, locate_drawdown, signal_explanation
from quant_lab.us_price_research import USPriceConfig


def history(close=(10, 10, 12, 11, 9, 10, 12), opens=None):
    close = np.asarray(close, dtype=float)
    opening = close.copy() if opens is None else np.asarray(opens, dtype=float)
    return pd.DataFrame({"date": pd.bdate_range("2026-01-05", periods=len(close)),
                         "open": opening, "high": np.maximum(opening, close) + 1,
                         "low": np.minimum(opening, close) - 1, "close": close,
                         "volume": 1000.})


def costs(market="A 股", **overrides):
    values = dict(initial_cash=1100., commission_bps=0., min_commission=5.,
                  buy_tax_bps=0., sell_tax_bps=10., slippage_bps=100.)
    values.update(overrides)
    return USPriceConfig(**values) if market == "美股" else BacktestConfig(market=market, lot_size=100, limit_pct=None, **values)


SPEC = StrategySpec("single_ma", 2, 3)


@pytest.mark.parametrize("market", ["A 股", "港股", "美股"])
def test_replay_money_reconciles_and_never_mutates_inputs(market):
    raw = history(opens=[10, 10, 12, 10, 12, 10, 12])
    config = costs(market)
    signals = build_signals(raw, SPEC)
    result = run_backtest(raw, signals.signal, config)
    snapshots = [value.copy(deep=True) for value in (raw, signals, result.equity, result.orders)]
    replay = build_trade_replay(raw, signals, result, SPEC, config)
    assert replay.events.status.tolist() == ["filled", "filled"]
    if market != "美股":
        # Buy 100 at 10.1, commission 5; sell 100 at 11.88, commission+levy 6.188.
        assert replay.events.price.tolist() == pytest.approx([10.1, 11.88])
        assert replay.events.slippage.tolist() == pytest.approx([10, 12])
        assert replay.daily.equity_change.iloc[3] == pytest.approx(85)
        assert replay.daily.overnight_pnl.iloc[4] == pytest.approx(100)
        assert replay.daily.equity_change.iloc[4] == pytest.approx(81.812)
        assert replay.daily.equity.iloc[-1] == pytest.approx(1266.812)
    pd.testing.assert_series_equal(
        replay.daily.overnight_pnl + replay.daily.intraday_pnl - replay.daily.slippage - replay.daily.fees,
        replay.daily.equity_change, check_names=False, atol=1e-8, rtol=1e-10)
    assert replay.daily.equity_change.sum() == pytest.approx(result.equity.equity.iloc[-1] - config.initial_cash)
    for original, snapshot in zip((raw, signals, result.equity, result.orders), snapshots):
        pd.testing.assert_frame_equal(original, snapshot)


def test_blocked_retry_keeps_reason_and_has_no_cost():
    raw = history([10, 11, 12, 13, 14, 15])
    raw.loc[3, "volume"] = 0
    signals = build_signals(raw, SPEC)
    config = costs(slippage_bps=0, min_commission=0, initial_cash=10000)
    result = run_backtest(raw, signals.signal, config)
    replay = build_trade_replay(raw, signals, result, SPEC, config)
    assert replay.events.status.tolist() == ["blocked", "filled"]
    assert replay.events.reason.iloc[0] == result.orders.reason.iloc[0]
    assert replay.events.iloc[0][["commission", "additional_fees", "slippage"]].eq(0).all()
    assert replay.events.decision_date.iloc[1] == raw.date.iloc[3]


def test_insufficient_cash_and_empty_orders_are_explained():
    raw = history([10, 11, 12, 13, 14])
    config = costs(initial_cash=1)
    signals = build_signals(raw, SPEC)
    replay = build_trade_replay(raw, signals, run_backtest(raw, signals.signal, config), SPEC, config)
    assert replay.events.status.eq("blocked").all()
    assert replay.events.reason.str.contains("资金不足").all()
    assert replay.drawdown is None
    flat = history([10] * 5)
    flat_signals = build_signals(flat, SPEC)
    empty = build_trade_replay(flat, flat_signals, run_backtest(flat, flat_signals.signal, config), SPEC, config)
    assert empty.events.empty and empty.drawdown is None
    assert "尚未形成" in signal_explanation(flat_signals, SPEC, 1)
    assert "现金" in signal_explanation(flat_signals, SPEC, 0)


def test_adjusted_signal_values_remain_separate_from_execution():
    raw = history()
    adjusted = raw.copy()
    adjusted["close"] *= .5
    saved = build_signals(adjusted, SPEC)
    config = costs()
    result = run_backtest(raw, saved.signal, config)
    replay = build_trade_replay(raw, saved, result, SPEC, config)
    assert replay.events.opening_price.iloc[0] == raw.open.iloc[3]
    assert "6.0000" in signal_explanation(saved, SPEC, 3)
    assert saved.close.iloc[2] == 6 and raw.close.iloc[2] == 12


def test_large_balance_roundoff_does_not_block_a_valid_ledger():
    raw = history(np.array([10, 10, 12, 11, 9, 10, 12]) * 10000.123)
    config = costs("美股", initial_cash=1e10, commission_bps=.001, slippage_bps=.0001)
    saved = build_signals(raw, SPEC)
    result = run_backtest(raw, saved.signal, config)
    replay = build_trade_replay(raw, saved, result, SPEC, config)
    assert replay.daily.equity.iloc[-1] == result.equity.equity.iloc[-1]


@pytest.mark.parametrize("path,expected", [
    ([100, 120, 120, 90, 90, 120], (2, 3, 5, -.25)),
    ([100, 120, 90, 100], (1, 2, None, -.25)),
    ([100, 80], (0, 1, None, -.2)),
    ([100, 80, 100, 80], (0, 1, 2, -.2)),
    ([100, 100, 101], None),
])
def test_drawdown_matches_existing_metric_and_deterministic_ties(path, expected):
    series = pd.Series(path)
    period = locate_drawdown(series)
    assert (None if period is None else (period.peak, period.trough, period.recovery)) == (None if expected is None else expected[:3])
    assert (0 if period is None else period.value) == pytest.approx(performance_stats(series).max_drawdown)


@pytest.mark.parametrize("damage", ["dates", "equity", "cash", "fees", "decision", "status", "missing_order", "price"])
def test_inconsistent_saved_ledgers_are_rejected(damage):
    raw = history(opens=[10, 10, 12, 10, 12, 10, 12])
    saved = build_signals(raw, SPEC)
    config = costs()
    result = run_backtest(raw, saved.signal, config)
    if damage == "dates":
        saved.loc[1, "date"] += pd.Timedelta(days=5)
    elif damage == "equity":
        result.equity.loc[3, "equity"] += 1
    elif damage == "cash":
        result.orders.loc[0, "cash_after"] += 1
    elif damage == "fees":
        result.orders.loc[0, "fees"] += 1
    elif damage == "decision":
        saved.loc[2, "signal"] = 0
    elif damage == "status":
        result.orders.loc[0, "status"] = "unknown"
    elif damage == "price":
        result.orders.loc[0, "price"] += 1
    else:
        result = replace(result, orders=result.orders.iloc[0:0])
    with pytest.raises(ValueError):
        build_trade_replay(raw, saved, result, SPEC, config)


@pytest.mark.parametrize("kind", ["single_ma", "dual_ma", "trend"])
def test_signal_explanation_only_reads_previous_close(kind):
    spec = StrategySpec(kind, 2, 3)
    saved = build_signals(history([10, 11, 12, 13, 14, 15]), spec)
    text = signal_explanation(saved, spec, 4)
    saved.loc[4:, ["close", "ma_short", "ma_long"]] = 999
    assert signal_explanation(saved, spec, 4) == text
    assert "下一交易日" in text and "2026-01-08" in text
