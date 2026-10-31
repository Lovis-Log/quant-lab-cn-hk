"""Provider-neutral market data contracts and conservative snapshot semantics."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
import re

import pandas as pd


MARKETS = ("A 股", "港股")
ADJUSTMENTS = ("", "qfq", "hfq")
NAME_UNAVAILABLE = "名称暂不可用"


def display_security(market: str, symbol: str, name: str | None = None) -> str:
    return f"{market} {normalize_symbol(market, symbol)}（{name or NAME_UNAVAILABLE}）"


def normalize_symbol(market: str, symbol: str) -> str:
    """Normalize common user spellings; this does not verify a listing identity."""
    if market not in MARKETS:
        raise ValueError("只支持 A 股股票和港股股票。")
    value = symbol.strip().upper()
    if market == "A 股":
        value = re.sub(r"^(SH|SZ|BJ)[.:]?", "", value)
        value = re.sub(r"[.](SH|SZ|BJ)$", "", value)
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("A 股代码必须是 6 位数字。")
    else:
        value = re.sub(r"^(HK)[.:]?", "", value)
        value = re.sub(r"[.]HK$", "", value)
        if not re.fullmatch(r"\d{1,5}", value):
            raise ValueError("港股代码必须是 1–5 位数字。")
        value = value.zfill(5)
    return value


@dataclass(frozen=True)
class MarketSnapshot:
    market: str
    symbol: str
    last_close: float
    observation_date: date
    received_at: datetime
    source: str
    currency: str
    status: str = "历史日线收盘参考；非实时，延迟未知"
    cached: bool = False
    cache_age_seconds: float = 0.0
    update_result: str = "取得新数据"
    update_error: str | None = None
    last_attempt_at: datetime | None = None
    quality_status: str = "质量覆盖未记录（旧参考或仅报价输入）"


class MarketDataProvider(Protocol):
    """Future licensed adapters can implement this without importing Streamlit."""

    name: str

    def history(self, market: str, symbol: str, start: date, end: date,
                adjustment: str = "") -> "HistoryBundle": ...

    def snapshot(self, market: str, symbol: str) -> MarketSnapshot: ...


class HistoryBundle(Protocol):
    frame: pd.DataFrame
    market: str
    symbol: str
    source: str
    currency: str
    adjustment: str
    received_at: datetime | None
