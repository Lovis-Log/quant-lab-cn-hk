"""US security identities, sessions and explicitly covered settlement dates."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import re
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd


NY = ZoneInfo("America/New_York")
US_RULES_VERSION = "us-cash-regular-v1"


def normalize_us_symbol(value):
    """Canonical dots identify share classes; never guess a source namespace."""
    symbol = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{0,9}(?:\.[A-Z0-9]{1,2})?", symbol):
        raise ValueError("美股平台代码应为大写字母/数字，类别股使用点号；来源代码需经证券映射，不能直接猜测。")
    return symbol


@dataclass(frozen=True)
class USInstrument:
    symbol: str
    name: str
    exchange: str
    security_type: str = "common_stock"
    currency: str = "USD"
    source_codes: tuple[tuple[str, str], ...] = ()
    identity_evidence: str = ""

    def __post_init__(self):
        if self.symbol != normalize_us_symbol(self.symbol):
            raise ValueError("证券身份必须使用规范平台代码。")
        if self.exchange not in {"XNYS", "XNAS"} or self.currency != "USD":
            raise ValueError("首版只处理NYSE/Nasdaq的美元证券身份。")
        if len(dict(self.source_codes)) != len(self.source_codes):
            raise ValueError("同一来源的证券代码映射不能重复。")

    def source_symbol(self, source):
        try:
            return dict(self.source_codes)[source]
        except KeyError as exc:
            raise ValueError("此证券尚无该来源的已核对代码映射。") from exc


@lru_cache(maxsize=16)
def _us_schedule(start: date, end: date):
    """Regular NYSE/Nasdaq reference sessions; UTC clocks include DST/early close."""
    if start > end:
        raise ValueError("开始日期不能晚于结束日期。")
    calendar = xcals.get_calendar("XNYS", start=start-timedelta(days=10), end=end+timedelta(days=10))
    schedule = calendar.schedule.loc[str(start):str(end), ["open", "close"]].copy()
    return schedule


def us_schedule(start: date,end: date):
    return _us_schedule(start,end).copy(deep=True)


def session_information(day):
    schedule = us_schedule(day, day)
    if schedule.empty:
        return {"date": day.isoformat(), "is_session": False, "timezone": "America/New_York"}
    row = schedule.iloc[0]
    opening, closing = row.open.to_pydatetime(), row.close.to_pydatetime()
    return {"date": day.isoformat(), "is_session": True, "timezone": "America/New_York",
        "open_utc": opening.isoformat(), "close_utc": closing.isoformat(),
        "open_new_york": opening.astimezone(NY).isoformat(), "close_new_york": closing.astimezone(NY).isoformat(),
        "early_close": closing.astimezone(NY).hour < 16}


def settlement_lag(trade_day):
    if trade_day < date(2016, 1, 1):
        raise ValueError("当前规则版本未核验2016年以前的研究区间。")
    if trade_day >= date(2024, 5, 28):
        return 1, "sec-t1-20240528"
    if trade_day >= date(2017, 9, 5):
        return 2, "sec-t2-20170905"
    return 3, "sec-t3-before-20170905"


@dataclass(frozen=True)
class SettlementCalendar:
    start: date
    end: date
    dates: tuple[date, ...]
    version: str
    evidence: str
    verified: bool = False

    def __post_init__(self):
        if self.start > self.end or tuple(sorted(set(self.dates))) != self.dates:
            raise ValueError("结算日期必须唯一升序且有明确覆盖区间。")
        if any(day < self.start or day > self.end for day in self.dates):
            raise ValueError("结算日期超出声明覆盖范围。")

    def due(self, trade_day):
        if not self.start <= trade_day <= self.end:
            raise ValueError("结算日历未覆盖成交日期。")
        lag, rule = settlement_lag(trade_day)
        following = [day for day in self.dates if day > trade_day]
        if len(following) < lag:
            raise ValueError("结算日历未覆盖本笔交易的完整结算期。")
        return following[lag-1], rule
