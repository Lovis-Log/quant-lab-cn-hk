"""US price/cost research at the existing AH model's declared fidelity.

No corporate-action cash flows, settlement simulation or licensed retention
grant. The strict us-cash-v1 model and all legacy AH defaults stay unchanged.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import math

import numpy as np
import pandas as pd

from quant_lab.comparison import ComparisonInputs, compare_inputs
from quant_lab.portfolio_cash import CashPortfolioConfig, PortfolioExecutionInputs, run_portfolio_research
from quant_lab.research import run_experiment
from quant_lab.research_validation import run_validation
from quant_lab.source_rights import UNVERIFIED_RETENTION
from quant_lab.us_data import validate_us_prices
from quant_lab.us_market import normalize_us_symbol, us_schedule
from quant_lab.us_sources import USPriceReference, fetch_sina_reference


PRICE_VERSION = "us-price-cost-v1"
ASSUMPTIONS = ("历史日线价格与成本研究；USD、只做多、无杠杆、整数股；收盘信号最早下一开盘成交。"
               "不核算拆合股/送转、现金分红、税务或结算现金，卖出款按成交记账；不是含分红总回报或真实现金账户模拟。")


@dataclass(frozen=True)
class USPriceConfig:
    market: str = "美股"
    initial_cash: float = 10000.
    lot_size: int = 1
    commission_bps: float = 0.
    min_commission: float = 0.
    buy_tax_bps: float = 0.
    sell_tax_bps: float = 0.
    slippage_bps: float = 2.
    limit_pct: None = None

    def __post_init__(self):
        if self.market != "美股" or type(self.lot_size) is not int or self.lot_size != 1 or self.limit_pct is not None:
            raise ValueError("美股价格模型须为USD整数股、交易单位1且无固定涨跌停假设。")
        if not math.isfinite(self.initial_cash) or not 0 < self.initial_cash <= 1e10:
            raise ValueError("美元资金须为正的有限数值且不超过100亿。")
        costs = (self.commission_bps, self.min_commission, self.buy_tax_bps, self.sell_tax_bps, self.slippage_bps)
        if any(isinstance(value, bool) or not math.isfinite(value) or value < 0 for value in costs) or self.slippage_bps >= 10000:
            raise ValueError("费用须为非负有限值，滑点须小于100%。")


@dataclass(frozen=True)
class USPriceCoverage:
    coverage_label: str
    calendar_name: str = "XNYS"
    calendar_version: str = ""
    calendar_available: bool = True


@dataclass(frozen=True)
class USPriceBundle:
    frame: pd.DataFrame
    symbol: str
    source: str
    received_at: datetime
    quality: USPriceCoverage
    market: str = "美股"
    currency: str = "USD"
    adjustment: str = ""
    company_name: str = ""
    cached: bool = False


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def reference_manifest(reference):
    return {**asdict(reference.observation), "currency": reference.currency,
            "price_basis": reference.price_basis, "model": PRICE_VERSION, "assumptions": ASSUMPTIONS}


def validate_price_input(reference: USPriceReference, *, execution=True):
    """Price-only eligibility, independent of strict corporate-action eligibility."""
    if not isinstance(reference, USPriceReference) or reference.currency != "USD":
        raise ValueError("研究输入必须为美股USD日线引用，不能混入其他币种。")
    if reference.update_error:
        raise ValueError("最近日线更新失败；旧行情保留查看，重新成功获取后再运行新研究。")
    info = reference.observation
    if info.symbol != normalize_us_symbol(info.symbol) or reference.price_basis != USPriceReference.__dataclass_fields__["price_basis"].default:
        raise ValueError("美股代码或价格口径与价格研究合同不一致。")
    data = validate_us_prices(reference.frame)
    received = datetime.fromisoformat(info.received_at)
    if received.tzinfo is None or info.content_sha256 != hashlib.sha256(data.to_csv(index=False).encode()).hexdigest():
        raise ValueError("美股来源时间或价格指纹与输入不一致。")
    schedule = us_schedule(data.date.iloc[0].date(), data.date.iloc[-1].date())
    if schedule.empty or schedule.iloc[-1]["close"] > pd.Timestamp(received):
        raise ValueError("末日日线尚未完成收市，不能生成研究结论。")
    if not set(data.date.dt.date).issubset(set(schedule.index.date)):
        raise ValueError("行情包含非参考交易日。")
    if execution:
        if tuple(data.date.dt.date) != tuple(schedule.index.date):
            raise ValueError("成交区间有缺失交易日；不能删日或填价进行回测。")
        if (data.close.pct_change(fill_method=None).abs() >= .4).any():
            raise ValueError("存在至少40%的原始价格跳变；当前价格模型不处理公司行动，请核验或缩短区间。")
    return data


def run_us_price_experiment(reference, spec, config=USPriceConfig(), fraction=.7):
    raw = validate_price_input(reference)
    if not isinstance(config, USPriceConfig):
        raise ValueError("美股研究须使用独立USD价格模型参数。")
    if config.initial_cash / raw.open.min() > 1_000_000:
        raise ValueError("预计买入股数超过100万，请减少研究资金。")
    result = run_experiment(raw, raw, spec, config, fraction)
    digest = _hash({"model": PRICE_VERSION, "legacy_kernel": result.audit_id,
                    "source": reference_manifest(reference)})
    return replace(result, audit_id="us-price-v1:" + digest[:24])


def normalize_us_codes(codes):
    result = tuple(normalize_us_symbol(code) for code in codes)
    if not 2 <= len(result) <= 10 or len(set(result)) != len(result):
        raise ValueError("请输入2至10只规范化后不重复的美股代码。")
    return result


def collect_us_price_comparison(codes, start, end, *, force=False, cache_namespace=""):
    from importlib.metadata import version
    codes = normalize_us_codes(codes)
    def load(code):
        reference = fetch_sina_reference(code, start, end, force=force, cache_namespace=cache_namespace)
        if reference.observation.symbol != code:
            raise ValueError("来源代码与比较请求不一致。")
        raw = validate_price_input(reference, execution=False)
        quality = USPriceCoverage(f"参考缺口{len(reference.missing_sessions)}；价格引用，事件未重建",
                                  calendar_version=version("exchange_calendars"))
        return USPriceBundle(raw, code, reference.observation.source,
                             datetime.fromisoformat(reference.observation.received_at), quality, cached=reference.cached)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="quant-us-prices") as pool:
        bundles = dict(zip(codes, pool.map(load, codes)))
    digest = _hash({"model": PRICE_VERSION, "codes": codes, "start": start, "end": end,
                    "inputs": {code: {"source": item.source, "received_at": item.received_at,
                    "sha256": hashlib.sha256(item.frame.to_csv(index=False).encode()).hexdigest()} for code, item in bundles.items()}})
    return ComparisonInputs("美股", "USD", codes, start, end, "", bundles, digest)


def calculate_us_price_comparison(codes, start, end, benchmark, window, force=False, cache_namespace=""):
    inputs = collect_us_price_comparison(codes, start, end, force=force, cache_namespace=cache_namespace)
    return inputs, compare_inputs(inputs, benchmark, window)


def run_us_price_portfolio(inputs, config=USPriceConfig(), fraction=.7, frequency="monthly"):
    if inputs.market != "美股" or inputs.currency != "USD" or not isinstance(config, USPriceConfig):
        raise ValueError("美元组合只接收同市场USD价格输入与独立美股参数。")
    comparison = compare_inputs(inputs, inputs.codes[0])
    common = comparison.closes.index
    raw, manifests = {}, {}
    for code, bundle in inputs.bundles.items():
        if (bundle.symbol, bundle.market, bundle.currency) != (code, "美股", "USD"):
            raise ValueError("组合代码、市场或币种不一致。")
        frame = validate_us_prices(bundle.frame.loc[bundle.frame.date.between(common[0], common[-1])].reset_index(drop=True))
        schedule = us_schedule(common[0].date(), common[-1].date())
        if not pd.DatetimeIndex(frame.date).equals(common) or not common.equals(pd.DatetimeIndex(schedule.index).tz_localize(None)):
            raise ValueError("共同范围有缺失交易日；现金持仓模型不能删除交易日。")
        if schedule.iloc[-1]["close"] > pd.Timestamp(bundle.received_at) or (frame.close.pct_change(fill_method=None).abs() >= .4).any():
            raise ValueError("存在未结束日线或至少40%的价格跳变；请更新或缩短区间。")
        if config.initial_cash / frame.open.min() > 1_000_000:
            raise ValueError("预计交易股数超过100万，请减少研究资金。")
        raw[code] = frame
        manifests[code] = {"source": bundle.source, "received_at": bundle.received_at.isoformat(), "price_basis": "unadjusted-source-declared"}
    prepared = PortfolioExecutionInputs(inputs, raw, raw, manifests)
    settings = CashPortfolioConfig(config, tuple((code, 1) for code in inputs.codes), frequency)
    result = run_portfolio_research(prepared, settings, fraction)
    runs = {}
    for name, run in result.runs.items():
        manifest = {**run.manifest, "algorithm": "us-price-portfolio-v1", "shared_kernel": "ah-cash-price-v1", "assumptions": ASSUMPTIONS}
        runs[name] = replace(run, manifest=manifest, audit_id="us-price-portfolio-v1:" + _hash(manifest)[:24])
    return replace(result, runs=runs)


def run_us_price_validation(reference, recipe):
    if not isinstance(recipe.costs, USPriceConfig):
        raise ValueError("美股验证须使用USD价格模型参数。")
    raw = validate_price_input(reference)
    suite = run_validation(raw, recipe, provenance=reference_manifest(reference), price_validator=validate_us_prices)
    manifest = {**suite.manifest, "versions": {"algorithm": "us-price-validation-v1", "execution": PRICE_VERSION,
                 "shared_kernel": "research-validation-v1"},
                "company_actions": {"status": "not-modelled", "scope": ASSUMPTIONS}}
    return replace(suite, manifest=manifest, audit_id="us-price-validation-v1:" + _hash(manifest)[:24])


def price_report(reference, experiment, spec, config, fraction, *, company_name=""):
    """Summary only, like live AH inputs without a durable-retention grant."""
    return json.dumps({"format": "quantlab-us-price-summary-v1", "audit_id": experiment.audit_id,
                       "inputs": {**reference_manifest(reference), "company_name": company_name}, "strategy": asdict(spec), "costs": asdict(config),
                       "train_fraction": fraction, "strategy_stats": asdict(experiment.full_stats),
                       "benchmark_stats": asdict(experiment.benchmark_stats), "test_stats": asdict(experiment.test_stats),
                       "raw_prices_included": False, "offline_replay_available": False,
                       "retention": UNVERIFIED_RETENTION.to_dict()}, ensure_ascii=False, indent=2).encode()
