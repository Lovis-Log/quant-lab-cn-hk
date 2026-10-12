"""Statistics use hand-checkable values and chronological train/test splits."""

import numpy as np
import pandas as pd
import pytest

from quant_lab.statistics import evaluate_linear_model, one_sample_return_test, supervised_frame


def test_sample_mean_variance_and_hypothesis_test() -> None:
    history = pd.DataFrame({"close": [100.0, 110.0, 99.0, 108.9]})
    result = one_sample_return_test(history)

    assert result.observations == 3
    assert result.mean_daily == pytest.approx(1 / 30)
    assert result.sample_variance == pytest.approx(0.013333333333333334)
    assert result.p_value is not None and 0 <= result.p_value <= 1


def sample_history() -> pd.DataFrame:
    dates = pd.date_range("2026-01-02", periods=130, freq="B")
    daily = 0.002 + 0.012 * np.sin(np.arange(130) * 0.37)
    close = 100 * np.cumprod(1 + daily)
    volume = 100_000 + 3000 * np.arange(130) + 20_000 * np.sin(np.arange(130) * 0.23)
    return pd.DataFrame({"date": dates, "close": close, "volume": volume})


def test_features_precede_their_next_day_labels() -> None:
    samples = supervised_frame(sample_history())
    first = samples.iloc[0]
    assert first["target_date"] > first["feature_date"]
    original = sample_history()
    matching = original.loc[original["date"] == first["target_date"], "close"].iloc[0]
    current = original.loc[original["date"] == first["feature_date"], "close"].iloc[0]
    assert first["next_return"] == pytest.approx(matching / current - 1)


def test_model_never_trains_on_held_out_dates() -> None:
    evaluation = evaluate_linear_model(sample_history())
    assert evaluation.train_end < evaluation.test_start
    assert evaluation.train_rows >= 30 and evaluation.test_rows >= 10
    assert np.isfinite(evaluation.mae)
    assert np.isfinite(evaluation.baseline_mae)
    assert 0 <= evaluation.directional_accuracy <= 1
