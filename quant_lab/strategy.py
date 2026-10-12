"""Transparent close-of-day signals; execution belongs to the backtest engine."""

from dataclasses import dataclass

import pandas as pd


STRATEGY_NAMES = {
    "single_ma": "单均线过滤",
    "dual_ma": "双均线趋势",
    "trend": "价格与均线同向",
}


@dataclass(frozen=True)
class StrategySpec:
    kind: str = "dual_ma"
    short_window: int = 10
    long_window: int = 30

    def __post_init__(self) -> None:
        if self.kind not in STRATEGY_NAMES:
            raise ValueError("未知策略类型。")
        if not 2 <= self.short_window < self.long_window <= 250:
            raise ValueError("均线周期应满足 2 ≤ 短周期 < 长周期 ≤ 250。")


def moving_average(close: pd.Series, window: int) -> pd.Series:
    if not 2 <= window <= 250:
        raise ValueError("均线周期必须在 2 到 250 个交易日之间。")
    return close.astype(float).rolling(window=window, min_periods=window).mean()


def build_signals(history: pd.DataFrame, spec: StrategySpec) -> pd.DataFrame:
    """Signals at close t use only observations through t; no trade is made here."""
    if not {"date", "close"}.issubset(history.columns):
        raise ValueError("历史行情缺少日期或收盘价。")
    if history["date"].duplicated().any() or not history["date"].is_monotonic_increasing:
        raise ValueError("交易日必须唯一且按时间升序排列。")
    result = history[["date", "close"]].copy()
    result["ma_short"] = moving_average(result["close"], spec.short_window)
    result["ma_long"] = moving_average(result["close"], spec.long_window)
    if spec.kind == "single_ma":
        condition = result["close"] > result["ma_long"]
    elif spec.kind == "dual_ma":
        condition = result["ma_short"] > result["ma_long"]
    else:
        condition = (result["close"] > result["ma_long"]) & (
            result["ma_long"].diff() > 0
        )
    result["signal"] = condition.fillna(False).astype(int)
    return result
