"""Free US daily price references, isolated from execution-qualified datasets.

References stay in bounded process memory. A returned price never grants
identity, corporate-action completeness, execution, or archival eligibility.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
import hashlib
import re

import pandas as pd
import requests

from quant_lab.us_market import normalize_us_symbol, us_schedule
from quant_lab.us_data import validate_us_prices
from quant_lab.provider_runtime import SINA_RUNTIME_LOCK
from quant_lab.refresh import RefreshCache


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


@dataclass(frozen=True)
class USPriceReference:
    observation: USSourceObservation
    frame: pd.DataFrame
    expected_sessions: int
    missing_sessions: tuple[str, ...]
    non_session_dates: tuple[str, ...]
    excluded_unfinished_rows: int
    cached: bool = False
    update_error: str | None = None
    update_result: str = "取得新数据"
    price_basis: str = "来源声明未复权；执行价格口径未独立核验"
    currency: str = "USD"


_REFERENCE_CACHE = RefreshCache(ttl=300, max_entries=24)


def _request_sina_daily(symbol):
    """AKShare's raw-price endpoint/decoder, with bounded HTTP and no factor fetch.

    stock_us_daily also downloads/evaluates a separate adjustment-factor feed
    even for adjust=''. Raw references need neither that feed nor its eval.
    Only AKShare's bundled decoder is executed, never upstream JavaScript.
    """
    import py_mini_racer
    from akshare.stock.cons import zh_js_decode

    response = requests.get(f"https://finance.sina.com.cn/staticdata/us/{symbol}", timeout=(5, 20))
    response.raise_for_status()
    match = re.fullmatch(r'\s*var\s+[A-Za-z_$][\w$]*\s*=\s*"([^"\r\n]+)"\s*;?\s*', response.text)
    if not match:
        raise ValueError("新浪美股日线响应格式发生变化。")
    # HK fallback and US references must share the native runtime lock.
    with SINA_RUNTIME_LOCK:
        decoder = py_mini_racer.MiniRacer()
        try:
            decoder.eval(zh_js_decode)
            records = decoder.call("d", match.group(1))
        finally:
            decoder.close()
    frame = pd.DataFrame(records)
    # The decoder labels market dates with midnight Z, as in AKShare's
    # date-only conversion. This is not a quote timestamp to shift to New York.
    if "date" in frame:
        dates = pd.to_datetime(frame.date, utc=True, errors="coerce")
        if dates.isna().any() or (dates != dates.dt.normalize()).any():
            raise ValueError("新浪日线交易日期编码异常。")
        frame["date"] = dates.dt.tz_localize(None)
    return frame


def _load_sina_reference(symbol, start, end):
    try:
        frame = _request_sina_daily(symbol)
        received = datetime.now(timezone.utc)
        frame = frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(end))].copy()
        schedule = us_schedule(start, end)
        closed = schedule.loc[schedule["close"] <= pd.Timestamp(received)]
        # Future or in-progress sessions must not appear as finished daily bars.
        unfinished = set(schedule.index.date) - set(closed.index.date)
        excluded = int(frame.date.dt.date.isin(unfinished).sum())
        frame = frame.loc[~frame.date.dt.date.isin(unfinished)].reset_index(drop=True)
        try:
            frame = validate_us_prices(frame)
        except ValueError as error:
            raise USReferenceValidationError(str(error)) from error
        actual = set(frame.date.dt.date)
        expected = set(closed.index.date)
        missing = tuple(str(day) for day in sorted(expected - actual))
        extra = tuple(str(day) for day in sorted(actual - expected))
    except USReferenceValidationError:
        raise
    except Exception as error:
        raise ValueError("新浪美股公开日线请求或校验失败；没有替换为教学数据，也不能据此断言证券不存在。") from error
    observation = USSourceObservation(
        symbol, "新浪财经 · AKShare原始日线接口（仅价格参考）", str(start), str(end),
        str(frame.date.iloc[0].date()), str(frame.date.iloc[-1].date()), len(frame), received.isoformat(),
        hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(),
    )
    return USPriceReference(observation, frame, len(expected), missing, extra, excluded)


def _reference_query(symbol, start, end):
    symbol = normalize_us_symbol(symbol)
    if not isinstance(start, date) or not isinstance(end, date) or start > end:
        raise ValueError("开始日期不能晚于结束日期。")
    if start.year < 1900 or (end - start).days > 3660:
        raise ValueError("美股价格参考单次查询最多十年，日期不得早于1900年。")
    return symbol, start, end


def fetch_sina_reference(symbol, start, end, *, force=False, cache_namespace=""):
    """Single-flight per query/library; manual refresh bypasses the memory TTL."""
    symbol, start, end = _reference_query(symbol, start, end)
    view = _REFERENCE_CACHE.get(
        (cache_namespace, symbol, start, end), lambda: _load_sina_reference(symbol, start, end), force=force,
        same=lambda old, new: old.observation.content_sha256 == new.observation.content_sha256,
        failure_message=lambda error: (
            f"新浪美股日线校验失败：{error}；" if isinstance(error, USReferenceValidationError)
            else "新浪美股请求或校验失败；"
        ) + "保留上次有效日线和成功接收时间，数据可能过期。没有使用教学数据。",
    )
    if view.value is None:
        raise ValueError(view.error or "美股日线尚未返回。")
    return replace(view.value, frame=view.value.frame.copy(deep=True), cached=view.cached,
                   update_error=view.error, update_result=view.result)


def inspect_sina_prices(symbol, start, end):
    """Compatibility: metadata-only explicit probe, without an archival grant."""
    symbol, start, end = _reference_query(symbol, start, end)
    return _load_sina_reference(symbol, start, end).observation


class USReferenceValidationError(ValueError):
    """Safe, explicit OHLCV validation message for a requested reference range."""
