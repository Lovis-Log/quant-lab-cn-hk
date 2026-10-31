"""Historical CN/HK stock data access with explicit provider metadata."""

from datetime import date, datetime, timedelta, timezone
from dataclasses import dataclass, replace
import logging
import math
import sqlite3
from threading import Lock
from numbers import Real
import time
import traceback
from zoneinfo import ZoneInfo
from uuid import uuid4

import akshare as ak
import pandas as pd

from quant_lab.processing import DataValidationError, clean_stock_history
from quant_lab.market_data import MarketSnapshot, normalize_symbol, ADJUSTMENTS
from quant_lab.paths import user_data_dir
from quant_lab.refresh import RefreshCache
from quant_lab.data_quality import HistoryQuality, assess_history
from quant_lab.security import redact
from quant_lab.source_rights import RetentionPolicy, UNVERIFIED_RETENTION
from quant_lab.provider_runtime import SINA_RUNTIME_LOCK


LOGGER = logging.getLogger(__name__)
# Optional compatibility override; resolve the active library at write time.
LOG_PATH = None
ADJUSTMENT_LABELS = {"": "不复权", "qfq": "前复权", "hfq": "后复权"}


def _refresh_failure(error):
    if isinstance(error, DataValidationError):
        return "行情校验失败：" + redact(str(error))[:300] + "；上次有效数据不变。"
    return "历史行情更新失败；保留上次有效数据，数据可能过期。"


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
    quality: HistoryQuality | None = None
    batch_id: str = ""
    retention: RetentionPolicy = UNVERIFIED_RETENTION
    snapshot_id: str = ""
    persistence_note: str = ""
    segments: tuple = ()

    @property
    def adjustment_label(self) -> str:
        return ADJUSTMENT_LABELS[self.adjustment]


class DataUnavailableError(RuntimeError):
    """The live provider could not deliver a usable response."""


def _record_failure(symbol: str, exc: Exception) -> None:
    LOGGER.exception("Historical daily request failed for %s", symbol)
    try:
        log_path = LOG_PATH or user_data_dir() / "logs" / "data_errors.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log_file:
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
    retention_policy = UNVERIFIED_RETENTION

    def history(self, market: str, symbol: str, start: date, end: date,
                adjustment: str = "") -> HistoryBundle:
        """Segment only raw prices; adjusted histories stay a single response.

        Overlaps must agree before concatenation. A changed source/basis or a
        failed segment invalidates the entire request, never a partial success.
        """
        symbol = normalize_symbol(market, symbol)
        if adjustment or (end-start).days <= 1096:
            return self._history_once(market, symbol, start, end, adjustment)
        segments, bundles = [], []
        cursor = start
        while cursor <= end:
            stop = min(cursor+timedelta(days=1095), end)
            bundles.append(self._history_once(market, symbol, cursor, stop, ""))
            segments.append((cursor.isoformat(), stop.isoformat()))
            if stop == end:
                break
            cursor = stop-timedelta(days=30)
        first = bundles[0]
        combined = first.frame
        for bundle in bundles[1:]:
            if (bundle.source, bundle.currency) != (first.source, first.currency):
                raise DataValidationError("长区间分段来源或币种发生变化，不能拼接；请重试或缩短区间。")
            overlap = combined.merge(bundle.frame, on="date", suffixes=("_old", "_new"))
            for column in ("open", "high", "low", "close", "volume", "amount"):
                if not overlap[f"{column}_old"].equals(overlap[f"{column}_new"].rename(f"{column}_old")):
                    # Numeric dtypes may differ; compare values, never round prices.
                    if not (overlap[f"{column}_old"].to_numpy() == overlap[f"{column}_new"].to_numpy()).all():
                        raise DataValidationError("分段重叠记录不一致，可能发生历史修订；本次不拼接、不替换旧数据。")
            combined = pd.concat([combined, bundle.frame], ignore_index=True).drop_duplicates("date")
        frame = clean_stock_history(combined, start, end)
        received = bundles[-1].received_at
        quality = assess_history(frame, market, start, end, source=first.source, currency=first.currency,
                                 adjustment="", received_at=received)
        return replace(first, frame=frame, received_at=received, quality=quality, batch_id=uuid4().hex,
                       segments=tuple(segments))

    def _history_once(self, market: str, symbol: str, start: date, end: date,
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
                    with SINA_RUNTIME_LOCK:
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
        quality = assess_history(frame, market, start, end, source=source, currency=currency,
                                 adjustment=adjustment, received_at=received_at)
        return HistoryBundle(frame, market, symbol, source, currency, adjustment, received_at,
                             quality=quality, batch_id=uuid4().hex, retention=self.retention_policy)

    def snapshot(self, market: str, symbol: str) -> MarketSnapshot:
        """Latest daily close only; observation date has no verified quote clock."""
        end = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        bundle = self.history(market, symbol, end - timedelta(days=21), end)
        if bundle.frame.empty:
            raise DataUnavailableError("最近 21 天没有可用的历史日线收盘价。")
        quality = bundle.quality or assess_history(bundle.frame, market, end-timedelta(days=21), end,
            source=bundle.source, currency=bundle.currency, adjustment=bundle.adjustment, received_at=bundle.received_at)
        complete = bundle.frame.loc[~bundle.frame.date.dt.date.isin(quality.unfinished_sessions)]
        if complete.empty:
            raise DataUnavailableError("当前日线尚未结束，没有可确认的历史收盘参考。")
        if not quality.calendar_available and complete.date.iloc[-1].date() >= end:
            raise DataUnavailableError("末日日线的收市状态无法核验，不能作为已确认的收盘参考。")
        last = complete.iloc[-1]
        return MarketSnapshot(
            market=bundle.market, symbol=bundle.symbol, last_close=float(last["close"]),
            observation_date=last["date"].date(),
            received_at=bundle.received_at or datetime.now(timezone.utc),
            source=bundle.source, currency=bundle.currency,
            status="历史日线收盘参考；未结束日线不纳入，确切延迟未知" if quality.unfinished_sessions else
                   "历史日线收盘参考；非实时，延迟未知",
            quality_status="来源区间："+quality.coverage_label,
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
        query = (market, normalize_symbol(market, symbol), start, end, adjustment)
        key = (str(user_data_dir()), *query)
        policy = getattr(self.provider, "retention_policy", UNVERIFIED_RETENTION)
        snapshot_error = None
        store = None
        if policy.allowed:
            from quant_lab.history_snapshots import HistorySnapshotStore
            store = HistorySnapshotStore()
            try:
                saved = store.load(*query, policy=policy)
                if saved is not None:
                    age = (datetime.now(timezone.utc)-saved.received_at).total_seconds()
                    self.cache.seed(key, saved, age_seconds=age)
            except (OSError, ValueError, sqlite3.Error) as exc:
                snapshot_error = "本地快照不可用：" + redact(str(exc))[:150]
        def load():
            bundle = self.provider.history(*query)
            if (bundle.market, bundle.symbol, bundle.adjustment) != (query[0], query[1], query[4]):
                raise DataValidationError("行情包的市场、代码或价格口径与查询不匹配。")
            if bundle.currency != {"A 股": "CNY", "港股": "HKD"}.get(market):
                raise DataValidationError("行情币种与市场不匹配。")
            frame = clean_stock_history(bundle.frame, start, end)
            if frame.empty:
                raise DataValidationError("源端未返回该区间记录；原因或证券身份未核验，不覆盖上次有效数据。")
            quality = assess_history(frame, market, start, end, source=bundle.source,
                currency=bundle.currency, adjustment=adjustment, received_at=bundle.received_at)
            if not quality.structural_valid:
                raise DataValidationError("；".join(quality.errors))
            validated = replace(bundle, frame=frame, quality=quality, batch_id=bundle.batch_id or uuid4().hex)
            if store is not None and validated.retention == policy:
                try:
                    snapshot_id = store.save(validated, start, end)
                    validated = replace(validated, snapshot_id=snapshot_id)
                except (OSError, ValueError, sqlite3.Error) as exc:
                    validated = replace(validated, persistence_note="磁盘快照保存失败，旧快照不变：" + redact(str(exc))[:150])
            return validated
        view = self.cache.get(key, load, force=force, failure_message=_refresh_failure,
                              same=lambda a, b: a.frame.equals(b.frame))
        if view.value is None:
            raise DataUnavailableError((view.error or "历史行情暂时无法获取。") + "；当前没有可复用的有效数据。")
        return replace(view.value, frame=view.value.frame.copy(deep=True), cached=view.cached,
                       cache_age_seconds=view.age_seconds, update_result=view.result,
                       update_error=view.error, last_attempt_at=view.attempted_at,
                       persistence_note="；".join(filter(None, (view.value.persistence_note, snapshot_error))))


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
        from quant_lab.security_identity import normalize_security
        key = (market, normalize_security(market, symbol))
        def load():
            with self._lock:
                remaining = self.min_request_gap - (time.monotonic()-self._last_request_at)
                if remaining > 0:
                    time.sleep(remaining)
                self._last_request_at = time.monotonic()
                quote = self.provider.snapshot(*key)
                if not isinstance(quote, MarketSnapshot) or (quote.market, quote.symbol) != key:
                    raise DataValidationError("收盘参考的市场或规范代码与查询不匹配。")
                if quote.currency != {"A 股":"CNY", "港股":"HKD", "美股":"USD"}.get(market):
                    raise DataValidationError("收盘参考币种与市场不匹配。")
                if isinstance(quote.last_close, bool) or not isinstance(quote.last_close, Real) or not math.isfinite(quote.last_close) or quote.last_close <= 0:
                    raise DataValidationError("收盘参考价格不是正的有限值。")
                if not isinstance(quote.received_at, datetime) or quote.received_at.tzinfo is None:
                    raise DataValidationError("收盘参考接收时间缺少时区。")
                if not isinstance(quote.observation_date, date) or isinstance(quote.observation_date, datetime):
                    raise DataValidationError("收盘参考交易日期字段无效。")
                if quote.observation_date > quote.received_at.astimezone(ZoneInfo("Asia/Shanghai")).date():
                    raise DataValidationError("收盘参考交易日期晚于接收日期。")
                return quote
        view = self.cache.get(key, load, force=force, failure_message=_refresh_failure,
                              same=lambda a, b: (a.observation_date,a.last_close) == (b.observation_date,b.last_close))
        if view.value is None:
            raise DataUnavailableError((view.error or "行情参考暂时无法获取。") + "；当前没有可复用的有效数据。")
        quote = replace(view.value, cached=view.cached, cache_age_seconds=view.age_seconds,
                        update_result=view.result, update_error=view.error, last_attempt_at=view.attempted_at)
        return quote, quote.cached


from quant_lab.watchlist_data import WatchlistProvider

SNAPSHOT_CACHE = SnapshotCache(WatchlistProvider(DEFAULT_PROVIDER))


def snapshot_batch(items):
    """Keep per-symbol failures visible; rate limiting stays in SnapshotCache."""
    quotes, errors = {}, {}
    for item in items:
        try:
            quote, _ = SNAPSHOT_CACHE.get(*item, force=True)
            quotes[item] = quote
        except (DataUnavailableError, ValueError):
            errors[item] = "更新失败；保留上次有效参考价格和成功获取时间。"
    return quotes, errors
