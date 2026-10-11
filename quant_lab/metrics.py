"""Small, independently testable financial calculations."""

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(frozen=True)
class PriceSummary:
    simple_return: float | None
    period_high: float
    period_low: float
    trading_days: int
    first_close: float
    last_close: float


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
