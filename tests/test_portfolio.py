"""Portfolio weights may not use held-out returns."""

import pandas as pd
import pytest

from quant_lab.portfolio import analyze_portfolio


def history(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"date": pd.date_range("2026-01-05", periods=len(closes), freq="B"),
         "close": closes}
    )


def test_weights_are_trained_before_out_of_sample_returns() -> None:
    first = history([100, 110, 100, 105, 100, 110, 120, 115, 125, 130])
    second = history([100, 95, 100, 90, 100, 105, 110, 100, 95, 90])
    original = analyze_portfolio({"A": first, "B": second}, train_fraction=0.70)
    altered = second.copy()
    altered.loc[8:, "close"] = [500, 900]
    changed = analyze_portfolio({"A": first, "B": altered}, train_fraction=0.70)

    assert original.weights["等权"].tolist() == [0.5, 0.5]
    assert original.weights["逆波动率"].sum() == pytest.approx(1)
    pd.testing.assert_series_equal(original.weights["逆波动率"], changed.weights["逆波动率"])
    assert original.test_equity.iloc[0].tolist() == [1.0, 1.0]
    assert not original.test_equity.equals(changed.test_equity)


def test_portfolio_rejects_too_few_common_dates() -> None:
    first = history([100] * 10)
    second = history([100] * 10)
    second["date"] = pd.date_range("2026-03-02", periods=10, freq="B")
    with pytest.raises(ValueError, match="共同交易日"):
        analyze_portfolio({"A": first, "B": second})
