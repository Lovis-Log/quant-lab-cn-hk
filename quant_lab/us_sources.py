"""Unqualified free-price diagnostics, isolated from the US execution provider."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

import akshare as ak
import pandas as pd

from quant_lab.us_market import normalize_us_symbol
from quant_lab.us_data import validate_us_prices
from quant_lab.provider_runtime import SINA_RUNTIME_LOCK


@dataclass(frozen=True)
class USSourceObservation:
    symbol: str
    source: str
    requested_start: str
    requested_end: str
    actual_start: str
    actual_end: str
    observations: int
    received_at: str
    content_sha256: str
    raw_execution_verified: bool = False
    identity_verified: bool = False
    actions_complete: bool = False
    retention_verified: bool = False
    settlement_calendar_verified: bool = False


def inspect_sina_prices(symbol,start,end):
    """Metadata only; no raw archive, no inferred amount, no company-action grant."""
    symbol=normalize_us_symbol(symbol)
    if start>end:
        raise ValueError("开始日期不能晚于结束日期。")
    try:
        with SINA_RUNTIME_LOCK:
            frame=ak.stock_us_daily(symbol=symbol,adjust="")
        if "date" not in frame.columns:
            frame=frame.reset_index()
        frame["date"]=pd.to_datetime(frame.date)
        frame=frame.loc[frame.date.between(pd.Timestamp(start),pd.Timestamp(end))].sort_values("date").reset_index(drop=True)
        valid=validate_us_prices(frame)
    except Exception as error:
        raise ValueError("新浪美股公开日线请求或校验失败；没有替换为教学数据，也不能据此断言证券不存在。") from error
    return USSourceObservation(symbol,"AKShare / 新浪（未通过生产回测验证）",str(start),str(end),
        str(valid.date.iloc[0].date()),str(valid.date.iloc[-1].date()),len(valid),datetime.now(timezone.utc).isoformat(),
        hashlib.sha256(valid.to_csv(index=False).encode()).hexdigest())
