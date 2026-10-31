"""Hand-checkable existing price-risk definitions used by the overview row."""

import math

import pandas as pd
import pytest

from quant_lab.metrics import price_risk_metrics


def test_price_risk_hand_calculation_and_short_or_constant_samples():
    volatility, drawdown = price_risk_metrics(pd.Series([100., 110., 99.]))
    # Returns +10%, -10%; sample variance .02; drawdown 99/110-1.
    assert volatility == pytest.approx(math.sqrt(.02 * 252))
    assert drawdown == pytest.approx(-.1)
    assert price_risk_metrics(pd.Series([], dtype=float)) == (None, None)
    assert price_risk_metrics(pd.Series([100.])) == (None, None)
    assert price_risk_metrics(pd.Series([100., 110.])) == (None, 0.)
    assert price_risk_metrics(pd.Series([100., 100., 100.])) == (0., 0.)


@pytest.mark.parametrize("values", [[1., float('nan')], [1., float('inf')], [0., 1.], [-1., 1.], [1e-300, 1e300]])
def test_invalid_price_risk_is_explicit(values):
    with pytest.raises(ValueError):
        price_risk_metrics(pd.Series(values))
