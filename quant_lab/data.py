"""Historical A-share stock data access through AKShare's Tencent adapter."""

from datetime import date, datetime, timezone
import logging
from pathlib import Path
import re
import traceback

import akshare as ak
import pandas as pd

from quant_lab.processing import DataValidationError, clean_tencent_history


LOGGER = logging.getLogger(__name__)
SOURCE_LABEL = "腾讯证券 · AKShare"
ADJUSTMENT_LABEL = "不复权（原始价格）"
LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "data_errors.log"


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
    """Fetch actual daily stock observations; never substitute demo rows."""
    if not re.fullmatch(r"\d{6}", symbol):
        raise ValueError("A 股股票代码必须是 6 位数字。")
    if start > end:
        raise ValueError("开始日期不能晚于结束日期。")

    try:
        raw = ak.stock_zh_a_hist_tx(
            symbol=symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="",
            timeout=15,
        )
    except Exception as exc:
        _record_failure(symbol, exc)
        raise DataUnavailableError("腾讯证券历史行情暂时无法获取，请稍后重试。") from exc
    try:
        return clean_tencent_history(raw, start, end)
    except DataValidationError as exc:
        _record_failure(symbol, exc)
        raise
