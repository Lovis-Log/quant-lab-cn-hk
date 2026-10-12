"""Descriptive statistics and a chronological next-day-return learning example."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURES = ("return_1", "return_5", "ma_gap_5_20", "volume_change", "volatility_10")


@dataclass(frozen=True)
class ReturnTest:
    observations: int
    mean_daily: float
    sample_variance: float
    sample_std: float
    annualized_volatility: float
    t_statistic: float | None
    p_value: float | None


@dataclass(frozen=True)
class ModelEvaluation:
    predictions: pd.DataFrame
    coefficients: pd.Series
    train_rows: int
    test_rows: int
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    mae: float
    baseline_mae: float
    r_squared: float
    directional_accuracy: float
    cv_mae: float


def one_sample_return_test(history: pd.DataFrame) -> ReturnTest:
    """Test H0: mean daily close-to-close return = 0 under iid assumptions."""
    daily = history["close"].astype(float).pct_change().dropna()
    if len(daily) < 3 or not np.isfinite(daily.to_numpy()).all():
        raise ValueError("均值检验至少需要 3 个有效的日收益率。")
    standard_deviation = float(daily.std(ddof=1))
    if standard_deviation > 0:
        result = stats.ttest_1samp(daily.to_numpy(), popmean=0.0)
        t_value, p_value = float(result.statistic), float(result.pvalue)
    else:
        t_value, p_value = None, None
    return ReturnTest(
        observations=len(daily), mean_daily=float(daily.mean()),
        sample_variance=float(daily.var(ddof=1)), sample_std=standard_deviation,
        annualized_volatility=standard_deviation * np.sqrt(252),
        t_statistic=t_value, p_value=p_value,
    )


def supervised_frame(history: pd.DataFrame) -> pd.DataFrame:
    """Features known after close t; label is close(t+1)/close(t)-1."""
    if not {"date", "close", "volume"}.issubset(history.columns):
        raise ValueError("机器学习样本缺少日期、收盘价或成交量。")
    if history["date"].duplicated().any() or not history["date"].is_monotonic_increasing:
        raise ValueError("机器学习样本必须按唯一交易日升序排列。")
    close = history["close"].astype(float)
    volume = history["volume"].astype(float).replace(0, np.nan)
    result = pd.DataFrame({"feature_date": history["date"]})
    result["target_date"] = history["date"].shift(-1)
    result["return_1"] = close.pct_change()
    result["return_5"] = close.pct_change(5)
    result["ma_gap_5_20"] = close.rolling(5).mean() / close.rolling(20).mean() - 1
    result["volume_change"] = volume.pct_change(fill_method=None)
    result["volatility_10"] = result["return_1"].rolling(10).std(ddof=1)
    result["next_return"] = close.shift(-1) / close - 1
    result = result.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    return result


def evaluate_linear_model(
    history: pd.DataFrame, train_fraction: float = 0.70
) -> ModelEvaluation:
    """Train a standardized linear regression on older rows, evaluate on newer rows."""
    if not 0.55 <= train_fraction <= 0.85:
        raise ValueError("训练比例必须在 55% 到 85% 之间。")
    samples = supervised_frame(history)
    if len(samples) < 60:
        raise ValueError("机器学习实验至少需要 60 个可用样本。")
    split = int(len(samples) * train_fraction)
    # One-row embargo prevents a training label from using the first test day.
    train = samples.iloc[: split - 1]
    test = samples.iloc[split:]
    if len(train) < 30 or len(test) < 10:
        raise ValueError("训练集或样本外测试集过短。")
    pipeline = make_pipeline(StandardScaler(), LinearRegression())
    splitter = TimeSeriesSplit(n_splits=3, gap=1)
    cross_validation_mae: list[float] = []
    for fit_index, validation_index in splitter.split(train):
        fold_model = make_pipeline(StandardScaler(), LinearRegression())
        fold_model.fit(train.iloc[fit_index][list(FEATURES)], train.iloc[fit_index]["next_return"])
        fold_prediction = fold_model.predict(train.iloc[validation_index][list(FEATURES)])
        cross_validation_mae.append(
            float(mean_absolute_error(train.iloc[validation_index]["next_return"], fold_prediction))
        )
    pipeline.fit(train[list(FEATURES)], train["next_return"])
    predicted = pipeline.predict(test[list(FEATURES)])
    actual = test["next_return"].to_numpy(dtype=float)
    predictions = test[["feature_date", "target_date", "next_return"]].rename(
        columns={"next_return": "actual"}
    ).copy()
    predictions["predicted"] = predicted
    coefficients = pd.Series(
        pipeline.named_steps["linearregression"].coef_, index=FEATURES,
        name="standardized_coefficient",
    )
    return ModelEvaluation(
        predictions=predictions, coefficients=coefficients,
        train_rows=len(train), test_rows=len(test),
        train_end=train["target_date"].iloc[-1], test_start=test["feature_date"].iloc[0],
        mae=float(mean_absolute_error(actual, predicted)),
        baseline_mae=float(mean_absolute_error(actual, np.zeros_like(actual))),
        r_squared=float(r2_score(actual, predicted)),
        directional_accuracy=float(np.mean((predicted >= 0) == (actual >= 0))),
        cv_mae=float(np.mean(cross_validation_mae)),
    )
