"""Small, independently testable financial calculations."""

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PriceSummary:
    simple_return: float | None
    period_high: float
    period_low: float
    trading_days: int
    first_close: float
    last_close: float


@dataclass(frozen=True)
class PerformanceStats:
    cumulative_return: float
    annualized_return: float
    annualized_volatility: float | None
    max_drawdown: float
    sharpe: float | None
    ending_equity: float


def simple_price_return(first_close: float, last_close: float) -> float:
    """(End close / start close) - 1; excludes dividends and trading costs."""
    if not math.isfinite(first_close) or not math.isfinite(last_close):
        raise ValueError("收盘价必须为有限数值。")
    if first_close <= 0 or last_close <= 0:
        raise ValueError("不复权收盘价必须大于零。")
    return last_close / first_close - 1.0


def summarize_prices(history: pd.DataFrame) -> PriceSummary:
    """Summarize the selected trading observations in chronological order."""
    if history.empty:
        raise ValueError("没有可计算的交易日。")
    first_close = float(history["close"].iloc[0])
    last_close = float(history["close"].iloc[-1])
    period_return = (
        simple_price_return(first_close, last_close) if len(history) >= 2 else None
    )
    return PriceSummary(
        simple_return=period_return,
        period_high=float(history["high"].max()),
        period_low=float(history["low"].min()),
        trading_days=len(history),
        first_close=first_close,
        last_close=last_close,
    )


def performance_stats(
    equity: pd.Series, annual_risk_free: float = 0.0, periods_per_year: int = 252
) -> PerformanceStats:
    """Evaluate an equity curve; daily returns and Sharpe are sample estimates."""
    values = pd.to_numeric(equity, errors="coerce").astype(float)
    if len(values) < 2 or not np.isfinite(values.to_numpy()).all() or (values <= 0).any():
        raise ValueError("净值序列至少需要两个正的有限值。")
    if not math.isfinite(annual_risk_free) or annual_risk_free <= -1 or periods_per_year < 1:
        raise ValueError("无风险利率或年交易日参数无效。")
    returns = values.pct_change().dropna()
    total = float(values.iloc[-1] / values.iloc[0] - 1)
    annual = float((values.iloc[-1] / values.iloc[0]) ** (periods_per_year / len(returns)) - 1)
    drawdown = values / values.cummax() - 1
    volatility: float | None = None
    sharpe: float | None = None
    if len(returns) >= 2:
        daily_std = float(returns.std(ddof=1))
        if daily_std > 1e-12:
            volatility = daily_std * math.sqrt(periods_per_year)
            daily_rf = (1 + annual_risk_free) ** (1 / periods_per_year) - 1
            sharpe = (float(returns.mean()) - daily_rf) / daily_std * math.sqrt(periods_per_year)
    return PerformanceStats(total, annual, volatility, float(drawdown.min()), sharpe, float(values.iloc[-1]))
