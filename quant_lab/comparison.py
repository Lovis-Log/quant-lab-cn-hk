"""Bounded same-currency collection and full-resolution comparison calculations."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
import hashlib
import math

import numpy as np
import pandas as pd

from quant_lab.data import HistoryBundle, fetch_history_cached
from quant_lab.data_quality import require_completed_close, assess_history
from quant_lab.market_data import normalize_symbol
from quant_lab.processing import clean_stock_history
from quant_lab.metrics import price_risk_metrics


@dataclass(frozen=True)
class ComparisonInputs:
    market: str
    currency: str
    codes: tuple[str, ...]
    start: date
    end: date
    adjustment: str
    bundles: dict[str, HistoryBundle]
    fingerprint: str


@dataclass(frozen=True)
class ComparisonResult:
    closes: pd.DataFrame
    normalized: pd.DataFrame
    drawdowns: pd.DataFrame
    rolling_volatility: pd.DataFrame
    correlation: pd.DataFrame
    risk_return: pd.DataFrame
    coverage: pd.DataFrame
    benchmark: str
    fingerprint: str


def normalize_comparison_codes(market,codes):
    normalized=tuple(normalize_symbol(market,code) for code in codes)
    if not 2<=len(normalized)<=10 or len(set(normalized))!=len(normalized):
        raise ValueError("比较需要2至10只规范化后不重复的同市场股票。")
    return normalized


def collect_comparison(market,codes,start,end,adjustment="",*,force=False,fetcher=None):
    codes=normalize_comparison_codes(market,codes)
    if start>end or adjustment not in {"","qfq","hfq"}:
        raise ValueError("比较的日期顺序或价格口径无效。")
    fetcher=fetcher or fetch_history_cached
    currency={"A 股":"CNY","港股":"HKD"}[market]
    def load(code):
        item=fetcher(market,code,start,end,adjustment,force=force)
        if (item.market,item.symbol,item.currency,item.adjustment)!=(market,code,currency,adjustment):
            raise ValueError(f"{code}来源返回的身份、币种或价格口径与查询不一致。")
        if item.update_error:
            raise ValueError(f"{code}更新失败；不把旧缓存混入本次多股票比较。")
        frame=clean_stock_history(item.frame,start,end)
        if frame.empty:
            raise ValueError(f"{code}所选区间没有有效行情；证券身份与原因未核验。")
        from dataclasses import replace
        from quant_lab import names
        company_name=names.security_name(market,code) or item.company_name
        quality=assess_history(frame,market,start,end,source=item.source,currency=currency,
            adjustment=adjustment,received_at=item.received_at)
        validated=replace(item,frame=frame,quality=quality,company_name=company_name)
        require_completed_close(validated)
        return validated
    # At most two upstream requests within this batch; RefreshCache still merges
    # matching queries across sessions and all workers remain free of Streamlit.
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix="quant-compare") as pool:
        values=list(pool.map(load,codes))
    bundles=dict(zip(codes,values))
    digest=hashlib.sha256(repr((market,codes,start,end,adjustment)).encode())
    for code,item in bundles.items():
        digest.update(repr((code,item.source,item.currency,item.received_at)).encode())
        digest.update(item.frame.to_csv(index=False).encode())
    return ComparisonInputs(market,currency,codes,start,end,adjustment,bundles,digest.hexdigest())


def compare_inputs(inputs: ComparisonInputs,benchmark,window=20):
    if benchmark not in inputs.codes or not isinstance(window,int) or not 2<=window<=252:
        raise ValueError("请选择比较范围内的基准，滚动窗口须为2至252条。")
    series=[inputs.bundles[code].frame.set_index("date").close.rename(code) for code in inputs.codes]
    closes=pd.concat(series,axis=1,join="inner").sort_index()
    if len(closes)<3:
        raise ValueError("共同有效观测不足3条，不能进行统一收益风险比较。")
    if not np.isfinite(closes.to_numpy(dtype=float)).all() or (closes<=0).any().any():
        raise ValueError("比较价格须为正的有限值。")
    normalized=closes.div(closes.iloc[0]).mul(100)
    returns=closes.pct_change(fill_method=None).iloc[1:]
    drawdowns=closes.div(closes.cummax()).sub(1)
    volatility=returns.rolling(window,min_periods=window).std(ddof=1)*math.sqrt(252)
    rows,coverage=[],[]
    for code in inputs.codes:
        vol,drawdown=price_risk_metrics(closes[code])
        bundle=inputs.bundles[code]
        rows.append({"code":code,"price_return":normalized[code].iloc[-1]/100-1,
            "relative_to_benchmark":normalized[code].iloc[-1]/normalized[benchmark].iloc[-1]-1,
            "annualized_volatility":vol,"max_drawdown":drawdown,"observations":len(closes)})
        frame=bundle.frame
        coverage.append({"code":code,"requested_start":inputs.start,"requested_end":inputs.end,
            "actual_start":frame.date.iloc[0].date(),"actual_end":frame.date.iloc[-1].date(),
            "returned_rows":len(frame),"common_rows":len(closes),"excluded_rows":len(frame)-len(closes),
            "source":bundle.source,"received_at":bundle.received_at.isoformat() if bundle.received_at else "未记录",
            "quality":bundle.quality.coverage_label,"cached":bundle.cached})
    return ComparisonResult(closes,normalized,drawdowns,volatility,returns.corr(),pd.DataFrame(rows).set_index("code"),
                            pd.DataFrame(coverage),benchmark,inputs.fingerprint)
