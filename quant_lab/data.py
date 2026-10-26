"""Historical CN/HK stock data access with explicit provider metadata."""

from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass, replace
import logging
from threading import Lock
import time
import traceback
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

from quant_lab.processing import DataValidationError, clean_stock_history
from quant_lab.market_data import MarketSnapshot, normalize_symbol, ADJUSTMENTS
from quant_lab.paths import user_data_dir
from quant_lab.refresh import RefreshCache


LOGGER = logging.getLogger(__name__)
LOG_PATH = user_data_dir() / "logs" / "data_errors.log"
ADJUSTMENT_LABELS = {"": "不复权", "qfq": "前复权", "hfq": "后复权"}


@dataclass(frozen=True)
class HistoryBundle:
    frame: pd.DataFrame
    market: str
    symbol: str
    source: str
    currency: str
    adjustment: str
    received_at: datetime | None = None
    cached: bool = False
    cache_age_seconds: float = 0.0
    update_result: str = "取得新数据"
    update_error: str | None = None
    last_attempt_at: datetime | None = None
    company_name: str = ""

    @property
    def adjustment_label(self) -> str:
        return ADJUSTMENT_LABELS[self.adjustment]


class DataUnavailableError(RuntimeError):
    """The live provider could not deliver a usable response."""


def _record_failure(symbol: str, exc: Exception) -> None:
    LOGGER.exception("Historical daily request failed for %s", symbol)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{datetime.now(timezone.utc).isoformat()} symbol={symbol}\n")
            traceback.print_exception(exc, file=log_file)
    except OSError:
        LOGGER.warning("Could not write data error log", exc_info=True)


def fetch_a_share_daily(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Compatibility wrapper for the first A-share research lesson."""
    return fetch_history("A 股", symbol, start, end).frame


class AKShareProvider:
    """Free historical daily adapter. It does not claim exchange real-time quotes."""

    name = "AKShare"

    def history(self, market: str, symbol: str, start: date, end: date,
                adjustment: str = "") -> HistoryBundle:
        symbol = normalize_symbol(market, symbol)
        if start > end:
            raise ValueError("开始日期不能晚于结束日期。")
        if adjustment not in ADJUSTMENTS:
            raise ValueError("复权方式必须为不复权、前复权或后复权。")
        try:
            if market == "A 股":
                raw = ak.stock_zh_a_hist_tx(
                    symbol=symbol, start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"), adjust=adjustment, timeout=15,
                )
                source, currency = "腾讯证券 · AKShare", "CNY"
            else:
                try:
                    raw = ak.stock_hk_hist(
                        symbol=symbol, period="daily",
                        start_date=start.strftime("%Y%m%d"),
                        end_date=end.strftime("%Y%m%d"), adjust=adjustment,
                    ).rename(columns={
                        "日期": "date", "开盘": "open", "最高": "high",
                        "最低": "low", "收盘": "close", "成交量": "volume",
                        "成交额": "amount",
                    })
                    source, currency = "东方财富 · AKShare", "HKD"
                except Exception as primary_exc:
                    _record_failure(symbol, primary_exc)
                    raw = ak.stock_hk_daily(symbol=symbol, adjust=adjustment)
                    source = "新浪财经 · AKShare（东方财富请求失败后回退）"
                    currency = "HKD"
        except Exception as exc:
            _record_failure(symbol, exc)
            raise DataUnavailableError(f"{market}历史行情暂时无法获取，请稍后重试。") from exc
        received_at = datetime.now(timezone.utc)
        try:
            frame = clean_stock_history(raw, start, end)
        except DataValidationError as exc:
            _record_failure(symbol, exc)
            raise
        return HistoryBundle(frame, market, symbol, source, currency, adjustment, received_at)

    def snapshot(self, market: str, symbol: str) -> MarketSnapshot:
        """Latest daily close only; observation date has no verified quote clock."""
        end = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        bundle = self.history(market, symbol, end - timedelta(days=21), end)
        if bundle.frame.empty:
            raise DataUnavailableError("最近 21 天没有可用的历史日线收盘价。")
        last = bundle.frame.iloc[-1]
        return MarketSnapshot(
            market=bundle.market, symbol=bundle.symbol, last_close=float(last["close"]),
            observation_date=last["date"].date(),
            received_at=bundle.received_at or datetime.now(timezone.utc),
            source=bundle.source, currency=bundle.currency,
        )


DEFAULT_PROVIDER = AKShareProvider()


def fetch_history(
    market: str, symbol: str, start: date, end: date, adjustment: str = ""
) -> HistoryBundle:
    """Compatibility facade for existing research modules."""
    return DEFAULT_PROVIDER.history(market, symbol, start, end, adjustment)


class HistoryCache:
    """Short-lived, bounded cache of validated historical responses."""

    def __init__(self, provider: AKShareProvider, ttl_seconds: int = 900,
                 max_entries: int = 64) -> None:
        self.provider = provider
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.cache = RefreshCache(ttl_seconds, max_entries)

    def get(self, market: str, symbol: str, start: date, end: date,
            adjustment: str = "", *, force: bool = False) -> HistoryBundle:
        key = (market, normalize_symbol(market, symbol), start, end, adjustment)
        view = self.cache.get(key, lambda: self.provider.history(*key), force=force,
                              same=lambda a, b: a.frame.equals(b.frame))
        if view.value is None:
            raise DataUnavailableError("历史行情暂时无法获取；没有上次有效数据。")
        return replace(view.value, frame=view.value.frame.copy(deep=True), cached=view.cached,
                       cache_age_seconds=view.age_seconds, update_result=view.result,
                       update_error=view.error, last_attempt_at=view.attempted_at)


HISTORY_CACHE = HistoryCache(DEFAULT_PROVIDER)


def fetch_history_cached(market: str, symbol: str, start: date, end: date,
                         adjustment: str = "", *, force: bool = False) -> HistoryBundle:
    return HISTORY_CACHE.get(market, symbol, start, end, adjustment, force=force)


class SnapshotCache:
    """Process-local request throttle; failures never overwrite the last success."""

    def __init__(self, provider: AKShareProvider, ttl_seconds: int = 300,
                 min_request_gap: float = 1.0) -> None:
        self.provider = provider
        self.ttl_seconds = ttl_seconds
        self.min_request_gap = min_request_gap
        self.cache = RefreshCache(ttl_seconds)
        self._lock = Lock()
        self._last_request_at = float("-inf")

    def get(self, market: str, symbol: str, force: bool = False) -> tuple[MarketSnapshot, bool]:
        key = (market, normalize_symbol(market, symbol))
        def load():
            with self._lock:
                remaining = self.min_request_gap - (time.monotonic()-self._last_request_at)
                if remaining > 0:
                    time.sleep(remaining)
                self._last_request_at = time.monotonic()
                return self.provider.snapshot(*key)
        view = self.cache.get(key, load, force=force,
                              same=lambda a, b: (a.observation_date,a.last_close) == (b.observation_date,b.last_close))
        if view.value is None:
            raise DataUnavailableError("行情参考暂时无法获取；没有上次有效数据。")
        quote = replace(view.value, cached=view.cached, cache_age_seconds=view.age_seconds,
                        update_result=view.result, update_error=view.error, last_attempt_at=view.attempted_at)
        return quote, quote.cached


SNAPSHOT_CACHE = SnapshotCache(DEFAULT_PROVIDER)
