"""Finite same-market price screens, independent of UI and trading eligibility."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Lock
import time

import numpy as np
import pandas as pd

from quant_lab.security_identity import normalize_security
from quant_lab.data_quality import calendar_reference, assess_history
from quant_lab.processing import clean_stock_history
from quant_lab.security import redact

METRICS = ("return20", "return60", "volatility20", "drawdown60", "volume_ratio", "above_ma30", "ma10_above_ma30")
LABELS = dict(zip(METRICS, ("20期收益", "60期收益", "20期年化波动", "60期最大回撤幅度", "5/20日均量比", "收盘高于MA30", "MA10高于MA30")))


@dataclass(frozen=True)
class ScreenRecipe:
    market: str
    codes: tuple[str, ...]
    adjustment: str = ""
    bounds: tuple = ()  # (metric, lower or None, upper or None), booleans use 0/1.
    sort: str = "return20"
    ascending: bool = False

    def validate(self):
        if self.market not in {"A 股", "港股", "美股"}:
            raise ValueError("请选择支持的市场。")
        normalized = tuple(normalize_security(self.market, code) for code in self.codes)
        if normalized != self.codes or not 1 <= len(normalized) <= 20 or len(set(normalized)) != len(normalized):
            raise ValueError("候选须为1–20只规范化后不重复的同市场股票。")
        if self.adjustment not in {"", "qfq", "hfq"} or self.market == "美股" and self.adjustment:
            raise ValueError("价格口径不受支持。")
        if self.sort not in METRICS or type(self.ascending) is not bool:
            raise ValueError("排序设置无效。")
        seen = set()
        for metric, lower, upper in self.bounds:
            if metric not in METRICS or metric in seen:
                raise ValueError("筛选条件无效或重复。")
            seen.add(metric)
            for value in (lower, upper):
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                    raise ValueError("筛选阈值须为有限数值。")
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("条件下限不能大于上限。")


def price_metrics(frame):
    close = frame.close.reset_index(drop=True)
    volume = frame.volume.reset_index(drop=True)
    if (not np.isfinite(close.to_numpy(dtype=float)).all() or (close <= 0).any()
            or not np.isfinite(volume.to_numpy(dtype=float)).all() or (volume < 0).any()):
        raise ValueError("筛选价格须为正的有限值，成交量须为非负有限值。")
    result = {key: None for key in METRICS}
    for n in (20, 60):
        if len(close) >= n + 1:
            values = close.iloc[-n-1:]
            result[f"return{n}"] = float(values.iloc[-1] / values.iloc[0] - 1)
            if n == 20:
                result["volatility20"] = float(values.pct_change(fill_method=None).iloc[1:].std(ddof=1) * math.sqrt(252))
            else:
                result["drawdown60"] = -float((values / values.cummax() - 1).min())
    if len(volume) >= 20 and volume.iloc[-20:].mean() > 0:
        result["volume_ratio"] = float(volume.iloc[-5:].mean() / volume.iloc[-20:].mean())
    if len(close) >= 30:
        result["above_ma30"] = int(close.iloc[-1] > close.iloc[-30:].mean())
        result["ma10_above_ma30"] = int(close.iloc[-10:].mean() > close.iloc[-30:].mean())
    if any(value is not None and not math.isfinite(value) for value in result.values()):
        raise ValueError("指标计算溢出。")
    return result


def evaluate_screen(rows, recipe):
    recipe.validate()
    table = pd.DataFrame(rows)
    matches, notes = [], []
    for row in rows:
        passed = row["status"] == "合格"
        reasons = []
        for key, low, high in recipe.bounds:
            value = row.get(key)
            if value is None or pd.isna(value):
                passed = False
                reasons.append(LABELS[key]+"不可计算")
            elif (low is not None and value < low) or (high is not None and value > high):
                passed = False
                reasons.append(LABELS[key]+"不满足")
        matches.append(passed)
        notes.append("；".join(reasons) or row.get("error", ""))
    table["matched"] = matches
    table["condition_note"] = notes
    return table.sort_values(["matched", recipe.sort, "code"], ascending=[False, recipe.ascending, True], na_position="last").reset_index(drop=True)


@dataclass(frozen=True)
class ScreenResult:
    table: pd.DataFrame
    cutoff: str
    fingerprint: str


_request_lock = Lock()
_last_start = 0.0


def collect_screen(recipe, start, end, namespace, *, force=False, cancelled=lambda: False, fetcher=None, spacing=1.):
    """Two active requests at most; never enqueue the remainder after cancellation."""
    recipe.validate()
    if start > end:
        raise ValueError("开始日期不能晚于结束日期。")
    now = datetime.now(timezone.utc)
    calendar = calendar_reference(recipe.market, start, end)
    completed = [day for day, closing in calendar.sessions if closing <= now]
    if not calendar.available or not completed:
        raise ValueError("无法核验统一已收市截止日，请检查日期范围。")
    cutoff = completed[-1]
    currency = {"A 股": "CNY", "港股": "HKD", "美股": "USD"}[recipe.market]
    def load(code):
        global _last_start
        with _request_lock:
            while time.monotonic() - _last_start < spacing:
                if cancelled():
                    return None
                time.sleep(max(0., min(.05, spacing - (time.monotonic() - _last_start))))
            if cancelled():
                return None
            _last_start = time.monotonic()
        row = {"code": code, "name": "名称暂不可用", "status": "失败", "error": "", **{key: None for key in METRICS}}
        try:
            if fetcher:
                bundle = fetcher(recipe.market, code, start, cutoff, recipe.adjustment, force=force)
            elif recipe.market == "美股":
                from quant_lab.us_sources import fetch_sina_reference
                from quant_lab.us_price_research import validate_price_input, USPriceBundle, USPriceCoverage
                ref = fetch_sina_reference(code, start, cutoff, force=force, cache_namespace=namespace)
                if ref.observation.symbol != code:
                    raise ValueError("返回证券代码与候选不一致。")
                frame = validate_price_input(ref, execution=False)
                bundle = USPriceBundle(frame, code, ref.observation.source, datetime.fromisoformat(ref.observation.received_at), USPriceCoverage("筛选日线"), cached=ref.cached)
            else:
                from quant_lab.data import fetch_history_cached
                bundle = fetch_history_cached(recipe.market, code, start, cutoff, recipe.adjustment, force=force)
            if (bundle.market, bundle.symbol, bundle.currency, bundle.adjustment) != (recipe.market, code, currency, recipe.adjustment):
                raise ValueError("来源身份、币种或价格口径不一致。")
            if getattr(bundle, "update_error", None):
                raise ValueError("本次更新失败，不能使用旧缓存筛选。")
            frame = bundle.frame.copy()
            if recipe.market == "美股":
                from quant_lab.us_data import validate_us_prices
                frame = validate_us_prices(frame)
                frame = frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(cutoff))].reset_index(drop=True)
                actual_end = frame.date.iloc[-1].date() if not frame.empty else None
                if tuple(frame.date.dt.date) != tuple(completed):
                    raise ValueError("截止日或交易日覆盖缺少行情，原因未核实。")
                quality_label = "按参考日历未见已结束交易日缺口"
            else:
                frame = clean_stock_history(frame, start, cutoff)
                quality = assess_history(frame, recipe.market, start, cutoff, source=bundle.source, currency=currency,
                                         adjustment=recipe.adjustment, received_at=bundle.received_at)
                actual_end = quality.actual_end
                quality_label = quality.coverage_label
                if (not quality.structural_valid or quality.unfinished_sessions or not quality.asof_known
                        or tuple(frame.date.dt.date) != tuple(completed)):
                    raise ValueError("交易日覆盖或接收时间未通过校验。")
            row.update(source=bundle.source, received_at=bundle.received_at.isoformat() if bundle.received_at else "未记录",
                       currency=currency, adjustment=recipe.adjustment or "不复权", cached=bundle.cached,
                       quality=quality_label, actual_start=str(frame.date.iloc[0].date()) if not frame.empty else "", actual_end=str(actual_end))
            if bundle.received_at is None or bundle.received_at.tzinfo is None:
                raise ValueError("来源接收时间未核实。")
            closing = next(closing for day, closing in calendar.sessions if day == cutoff)
            if bundle.received_at < closing or bundle.received_at > datetime.now(timezone.utc):
                raise ValueError("接收时间不能证明截止日日线已收市。")
            if frame.empty or actual_end != cutoff:
                raise ValueError("截止日缺少行情，原因未核实。")
            if (frame.close.pct_change(fill_method=None).abs() >= .4).any():
                raise ValueError("存在至少40%价格跳变，需核验公司行动或缩短区间。")
            row.update(price_metrics(frame), status="合格")
            try:
                from quant_lab import names
                row["name"] = names.cached_security_name(recipe.market, code) or getattr(bundle, "company_name", "") or "名称暂不可用"
            except Exception:
                pass
        except Exception as error:
            row["status"] = "失败"
            row["error"] = redact(str(error))[:300]
        return row
    rows = []
    pending = {}
    iterator = iter(recipe.codes)
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="quant-screen")
    try:
        while not cancelled():
            while len(pending) < 2:
                code = next(iterator, None)
                if code is None:
                    break
                pending[pool.submit(load, code)] = code
            if not pending:
                break
            done, _ = wait(pending, timeout=.05, return_when=FIRST_COMPLETED)
            for future in done:
                pending.pop(future)
                row = future.result()
                if row is not None:
                    rows.append(row)
        if cancelled():
            raise ValueError("批量筛选已取消或超时；未发布部分结果。")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    table = evaluate_screen(rows, recipe)
    digest = hashlib.sha256((repr((asdict(recipe), start, end, cutoff)) + table.to_json(date_format="iso")).encode()).hexdigest()
    return ScreenResult(table, str(cutoff), digest)
