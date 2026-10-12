"""Small deterministic paths make signal timing and fills independently checkable."""

import pandas as pd
import pytest

from quant_lab.backtest import BacktestConfig, run_backtest, run_buy_and_hold
from quant_lab.metrics import performance_stats
from quant_lab.strategy import StrategySpec, build_signals


def price_path(opens: list[float], closes: list[float],
               volumes: list[float] | None = None) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-05", periods=len(opens), freq="B"),
            "open": opens, "close": closes,
            "volume": volumes if volumes is not None else [1000] * len(opens),
        }
    )


def zero_cost_config(**overrides: object) -> BacktestConfig:
    values = dict(market="A 股", initial_cash=2000, lot_size=100,
                  commission_bps=0, min_commission=0, buy_tax_bps=0,
                  sell_tax_bps=0, slippage_bps=0, limit_pct=None)
    values.update(overrides)
    return BacktestConfig(**values)


def test_signal_uses_only_past_and_present_closes() -> None:
    history = price_path([10, 11, 12, 13], [10, 11, 12, 13])
    spec = StrategySpec(kind="dual_ma", short_window=2, long_window=3)
    before = build_signals(history, spec)
    extended = price_path([10, 11, 12, 13, 1], [10, 11, 12, 13, 1])
    after = build_signals(extended, spec)

    assert before["signal"].tolist() == [0, 0, 1, 1]
    assert after["signal"].iloc[:4].tolist() == before["signal"].tolist()


def test_close_signal_fills_next_open_and_sell_is_later() -> None:
    history = price_path([10, 11, 12, 11], [10, 11, 12, 11])
    result = run_backtest(history, pd.Series([1, 0, 0, 0]), zero_cost_config())
    filled = result.orders[result.orders["status"] == "filled"]

    assert filled["side"].tolist() == ["buy", "sell"]
    assert filled["date"].tolist() == [history["date"].iloc[1], history["date"].iloc[2]]
    assert filled["decision_date"].iloc[0] == history["date"].iloc[0]
    assert filled["shares"].tolist() == [100, 100]
    assert result.equity["equity"].iloc[-1] == pytest.approx(2100)
    assert performance_stats(result.equity["equity"]).cumulative_return == pytest.approx(0.05)


def test_limit_and_zero_volume_block_fills() -> None:
    config = zero_cost_config(limit_pct=0.10)
    limit_path = price_path([10, 11, 11], [10, 11, 11])
    limit_result = run_backtest(limit_path, pd.Series([1, 1, 1]), config)
    assert limit_result.orders["status"].iloc[0] == "blocked"
    assert "涨停" in limit_result.orders["reason"].iloc[0]

    suspended = price_path([10, 10, 10], [10, 10, 10], [1000, 0, 1000])
    suspended_result = run_backtest(suspended, pd.Series([1, 1, 1]), config)
    assert "零成交量" in suspended_result.orders["reason"].iloc[0]
    assert suspended_result.orders["status"].iloc[1] == "filled"


def test_buy_and_hold_uses_same_next_open_rule() -> None:
    history = price_path([10, 11, 12], [10, 11, 12])
    result = run_buy_and_hold(history, zero_cost_config())
    assert len(result.orders) == 1
    assert result.orders["date"].iloc[0] == history["date"].iloc[1]


def test_commission_and_sell_levy_match_hand_calculation() -> None:
    history = price_path([10, 10, 11], [10, 10, 11])
    config = zero_cost_config(
        initial_cash=1020, min_commission=5, sell_tax_bps=10,
    )
    result = run_backtest(history, pd.Series([1, 0, 0]), config)

    assert result.orders["fees"].tolist() == pytest.approx([5.0, 6.1])
    assert result.equity["cash"].iloc[-1] == pytest.approx(1108.9)


def test_max_drawdown_is_relative_to_previous_peak() -> None:
    equity = pd.Series([100.0, 120.0, 90.0, 100.0])
    summary = performance_stats(equity)

    assert summary.max_drawdown == pytest.approx(-0.25)
    assert summary.cumulative_return == pytest.approx(0.0)
