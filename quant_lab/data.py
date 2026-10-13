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
                raw = ak.stock_hk_daily(symbol=symbol, adjust=adjustment)
                source, currency = "新浪财经 · AKShare", "HKD"
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
        self._values: dict[tuple, tuple[float, HistoryBundle]] = {}
        self._lock = Lock()

    def get(self, market: str, symbol: str, start: date, end: date,
            adjustment: str = "") -> HistoryBundle:
        key = (market, normalize_symbol(market, symbol), start, end, adjustment)
        with self._lock:
            now = time.monotonic()
            cached = self._values.get(key)
            if cached and now - cached[0] < self.ttl_seconds:
                return replace(cached[1], frame=cached[1].frame.copy(deep=True), cached=True)
            bundle = self.provider.history(*key)
            self._values[key] = (time.monotonic(), bundle)
            if len(self._values) > self.max_entries:
                oldest = min(self._values, key=lambda entry: self._values[entry][0])
                del self._values[oldest]
            return replace(bundle, frame=bundle.frame.copy(deep=True))


HISTORY_CACHE = HistoryCache(DEFAULT_PROVIDER)


def fetch_history_cached(market: str, symbol: str, start: date, end: date,
                         adjustment: str = "") -> HistoryBundle:
    return HISTORY_CACHE.get(market, symbol, start, end, adjustment)


class SnapshotCache:
    """Process-local request throttle; failures never overwrite the last success."""

    def __init__(self, provider: AKShareProvider, ttl_seconds: int = 300,
                 min_request_gap: float = 1.0) -> None:
        self.provider = provider
        self.ttl_seconds = ttl_seconds
        self.min_request_gap = min_request_gap
        self._values: dict[tuple[str, str], tuple[float, MarketSnapshot]] = {}
        self._lock = Lock()
        self._last_request_at = float("-inf")

    def get(self, market: str, symbol: str, force: bool = False) -> tuple[MarketSnapshot, bool]:
        key = (market, normalize_symbol(market, symbol))
        with self._lock:
            now = time.monotonic()
            cached = self._values.get(key)
            minimum_gap = 60 if force else self.ttl_seconds
            if cached and now - cached[0] < minimum_gap:
                return cached[1], True
            remaining = self.min_request_gap - (now - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
            self._last_request_at = time.monotonic()
            snapshot = self.provider.snapshot(*key)
            self._values[key] = (time.monotonic(), snapshot)
            return snapshot, False


SNAPSHOT_CACHE = SnapshotCache(DEFAULT_PROVIDER)
