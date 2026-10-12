"""Historical CN/HK stock data access with explicit provider metadata."""

from datetime import date, datetime, timezone
from dataclasses import dataclass
import logging
from pathlib import Path
import re
import traceback

import akshare as ak
import pandas as pd

from quant_lab.processing import DataValidationError, clean_stock_history


LOGGER = logging.getLogger(__name__)
LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "data_errors.log"
ADJUSTMENT_LABELS = {"": "不复权", "qfq": "前复权", "hfq": "后复权"}


@dataclass(frozen=True)
class HistoryBundle:
    frame: pd.DataFrame
    market: str
    symbol: str
    source: str
    currency: str
    adjustment: str

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


def fetch_history(
    market: str, symbol: str, start: date, end: date, adjustment: str = ""
) -> HistoryBundle:
    """Fetch stock history with no demo fallback or cross-currency conversion."""
    if market not in {"A 股", "港股"}:
        raise ValueError("只支持 A 股股票和港股股票。")
    symbol_pattern = r"\d{6}" if market == "A 股" else r"\d{5}"
    if not re.fullmatch(symbol_pattern, symbol):
        raise ValueError("A 股代码必须是 6 位数字，港股代码必须是 5 位数字。")
    if start > end:
        raise ValueError("开始日期不能晚于结束日期。")
    if adjustment not in ADJUSTMENT_LABELS:
        raise ValueError("复权方式必须为不复权、前复权或后复权。")

    try:
        if market == "A 股":
            raw = ak.stock_zh_a_hist_tx(
                symbol=symbol,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=adjustment,
                timeout=15,
            )
            source, currency = "腾讯证券 · AKShare", "CNY"
        else:
            raw = ak.stock_hk_daily(symbol=symbol, adjust=adjustment)
            source, currency = "新浪财经 · AKShare", "HKD"
    except Exception as exc:
        _record_failure(symbol, exc)
        raise DataUnavailableError(f"{market}历史行情暂时无法获取，请稍后重试。") from exc
    try:
        frame = clean_stock_history(raw, start, end)
    except DataValidationError as exc:
        _record_failure(symbol, exc)
        raise
    return HistoryBundle(frame, market, symbol, source, currency, adjustment)
