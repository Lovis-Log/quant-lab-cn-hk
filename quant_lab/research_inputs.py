"""Capture paired signal/raw inputs without mixing cached adjustment batches."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from quant_lab.data_quality import require_completed_close
from quant_lab.history_snapshots import frame_sha
from quant_lab.processing import DataValidationError


@dataclass(frozen=True)
class ResearchInputs:
    raw: pd.DataFrame
    signal: pd.DataFrame
    manifest: dict


def _metadata(bundle):
    return {"source": bundle.source, "currency": bundle.currency, "adjustment": bundle.adjustment,
        "received_at": bundle.received_at.isoformat() if bundle.received_at else None,
        "sha256": frame_sha(bundle.frame), "batch_id": bundle.batch_id,
        "retention": bundle.retention.to_dict(), "snapshot_id": bundle.snapshot_id}


def prepare_inputs(displayed, *, fetch=None):
    """Adjusted inputs are checked before and after a fresh raw request.

    This detects revisions during acquisition and refuses to apply a new raw
    response to an old chart. It does not certify provider adjustment factors
    or implement company actions. Original unadjusted inputs need no network.
    """
    require_completed_close(displayed)
    if displayed.frame.empty:
        raise DataValidationError("研究输入为空。")
    started = datetime.now(timezone.utc)
    signal = raw = displayed
    if displayed.adjustment:
        if fetch is None:
            from quant_lab.data import fetch_history_cached
            fetch = fetch_history_cached
        quality = displayed.quality
        start = quality.requested_start if quality else displayed.frame.date.iloc[0].date()
        end = quality.requested_end if quality else displayed.frame.date.iloc[-1].date()
        query = (displayed.market, displayed.symbol, start, end)
        signal = fetch(*query, displayed.adjustment, force=True)
        raw = fetch(*query, "", force=True)
        verify = fetch(*query, displayed.adjustment, force=True)
        for item in (signal, raw, verify):
            if item.update_error or item.cached or item.received_at is None or item.received_at.tzinfo is None:
                raise DataValidationError("本批研究输入获取失败或返回旧缓存，不能混用原始价与复权价；请重试。")
            if (item.market, item.symbol, item.source, item.currency) != (
                    displayed.market, displayed.symbol, displayed.source, displayed.currency):
                raise DataValidationError("研究输入来源、市场、代码或币种变化，请更新当前行情后重试。")
            require_completed_close(item)
        if signal.adjustment != displayed.adjustment or verify.adjustment != displayed.adjustment or raw.adjustment:
            raise DataValidationError("研究输入的价格口径不匹配。")
        if frame_sha(signal.frame) != frame_sha(verify.frame) or frame_sha(signal.frame) != frame_sha(displayed.frame):
            raise DataValidationError("复权历史已变化或获取期间发生修订；请先更新当前行情，不能沿用旧信号价格。")
    if not raw.frame.date.equals(signal.frame.date):
        raise DataValidationError("原始价与信号价交易日不一致；不能前值填充成交价格或静默取交集。")
    manifest = {"format": 1, "batch_id": uuid4().hex, "market": displayed.market,
        "symbol": displayed.symbol, "started_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(), "raw": _metadata(raw),
        "signal": _metadata(signal), "revision_check": "adjusted-before/raw/adjusted-after" if displayed.adjustment else "same-unadjusted-input",
        "scope": "输入配对与修订检查，不认证复权因子或公司行动"}
    return ResearchInputs(raw.frame.copy(deep=True), signal.frame.copy(deep=True), manifest)
