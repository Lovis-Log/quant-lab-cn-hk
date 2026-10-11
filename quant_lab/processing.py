"""Validate provider rows before they can reach charts or calculations."""

from datetime import date

import numpy as np
import pandas as pd


COLUMNS = ("date", "open", "high", "low", "close", "volume", "amount")
PRICE_COLUMNS = ("open", "high", "low", "close")


class DataValidationError(ValueError):
    """The provider returned data that cannot be safely interpreted."""


def clean_tencent_history(raw: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Normalize Tencent's daily stock rows to a validated, ascending table.

    Prices are unadjusted yuan per share, volume is shares, amount is yuan.
    """
    if not isinstance(raw, pd.DataFrame):
        raise DataValidationError("数据源没有返回表格。")
    if raw.empty:
        return pd.DataFrame(columns=COLUMNS)

    missing = set(COLUMNS) - set(raw.columns)
    if missing:
        raise DataValidationError(f"数据源缺少必要字段：{', '.join(sorted(missing))}")

    result = raw.loc[:, list(COLUMNS)].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    for column in COLUMNS[1:]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    if result.isna().any().any():
        raise DataValidationError("历史行情包含无法解析的日期或数值。")
    if not np.isfinite(result.loc[:, list(COLUMNS[1:])].to_numpy(dtype=float)).all():
        raise DataValidationError("历史行情包含无穷大数值。")

    result = result.loc[result["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
    result = result.sort_values("date").reset_index(drop=True)
    if result.empty:
        return result
    if result["date"].duplicated().any():
        raise DataValidationError("历史行情包含重复交易日。")
    if (result.loc[:, list(PRICE_COLUMNS)] <= 0).any().any():
        raise DataValidationError("不复权价格必须大于零。")
    if (result["volume"] < 0).any() or (result["amount"] < 0).any():
        raise DataValidationError("成交量或成交额不能为负。")
    if (result["high"] < result["low"]).any():
        raise DataValidationError("最高价小于最低价。")
    if (result["high"] + 0.01 < result[["open", "close"]].max(axis=1)).any():
        raise DataValidationError("开盘价或收盘价高于最高价。")
    if (result["low"] - 0.01 > result[["open", "close"]].min(axis=1)).any():
        raise DataValidationError("开盘价或收盘价低于最低价。")
    return result
