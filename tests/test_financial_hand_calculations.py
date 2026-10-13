"""Independently hand-check the core risk statistics."""

import math

import pandas as pd
import pytest

from quant_lab.metrics import performance_stats


def test_compound_return_drawdown_and_sharpe() -> None:
    # Daily returns are +10% and -10%; the peak-to-trough loss is 10%.
    stats = performance_stats(pd.Series([100.0, 110.0, 99.0]), periods_per_year=1)
    assert stats.cumulative_return == pytest.approx(-0.01)
    assert stats.annualized_return == pytest.approx(math.sqrt(0.99) - 1)
    assert stats.max_drawdown == pytest.approx(-0.10)
    assert stats.annualized_volatility == pytest.approx(math.sqrt(0.02))
    assert stats.sharpe == pytest.approx(0.0)


def test_constant_returns_do_not_produce_fake_infinite_sharpe() -> None:
    stats = performance_stats(pd.Series([100.0, 110.0, 121.0]), periods_per_year=252)
    assert stats.sharpe is None
    assert stats.annualized_volatility is None
