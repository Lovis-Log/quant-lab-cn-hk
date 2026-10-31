"""AH price-return portfolios with shared cash, explicit costs and OOS weights.

This version preserves legacy algorithms. It models price changes and execution
costs, not dividends, share distributions, corporate actions or withdrawals.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
import hashlib
import json
import math

import numpy as np
import pandas as pd

from quant_lab.backtest import BacktestConfig
from quant_lab.comparison import ComparisonInputs,compare_inputs
from quant_lab.data import fetch_history_cached
from quant_lab.data_quality import calendar_reference,require_completed_close
from quant_lab.metrics import performance_stats
from quant_lab.portfolio import inverse_volatility_weights
from quant_lab.research_inputs import prepare_inputs


PORTFOLIO_VERSION="ah-cash-price-v1"


@dataclass(frozen=True)
class CashPortfolioConfig:
    execution: BacktestConfig
    lot_sizes: tuple[tuple[str,int],...]
    frequency: str = "monthly"

    def __post_init__(self):
        if self.frequency not in {"monthly","daily"} or len(dict(self.lot_sizes))!=len(self.lot_sizes):
            raise ValueError("调仓频率或逐股交易单位无效。")
        if any(isinstance(lot,bool) or not isinstance(lot,int) or lot<1 for _,lot in self.lot_sizes):
            raise ValueError("每只股票的买入交易单位须为正整数研究参数。")


@dataclass(frozen=True)
class PortfolioExecutionInputs:
    comparison: ComparisonInputs
    raw: dict
    signal: dict
    manifests: dict


@dataclass(frozen=True)
class CashPortfolioRun:
    equity: pd.DataFrame
    positions: pd.DataFrame
    orders: pd.DataFrame
    weights: pd.Series
    stats: object
    audit_id: str
    manifest: dict


@dataclass(frozen=True)
class PortfolioResearch:
    runs: dict[str,CashPortfolioRun]
    weights: pd.DataFrame
    train_last_date: pd.Timestamp
    test_first_date: pd.Timestamp
    inverse_error: str | None


def prepare_portfolio_execution(inputs,*,fetcher=None):
    fetcher=fetcher or fetch_history_cached
    comparison=compare_inputs(inputs,inputs.codes[0])
    first,last=comparison.closes.index[0],comparison.closes.index[-1]
    def prepare(code):
        bundle=inputs.bundles[code]
        require_completed_close(bundle)
        pair=prepare_inputs(bundle,fetch=fetcher)
        raw=pair.raw.loc[pair.raw.date.between(first,last)].reset_index(drop=True)
        signal=pair.signal.loc[pair.signal.date.between(first,last)].reset_index(drop=True)
        if not pd.DatetimeIndex(raw.date).equals(comparison.closes.index):
            raise ValueError(f"{code}共同范围内有缺失成交日；比较可展示交集，现金模型不能删掉交易日或填充价格。")
        teaching=any(token in bundle.source.lower() for token in ("教学","模拟","teaching","simulation","demo"))
        if not teaching:
            reference=calendar_reference(inputs.market,first.date(),last.date())
            if not reference.available or tuple(raw.date.dt.date)!=tuple(day for day,_ in reference.sessions):
                raise ValueError(f"{code}共同区间的完整交易日无法核验；现金模型暂不能运行。")
        if (raw.close.pct_change(fill_method=None).abs()>=.4).any():
            raise ValueError(f"{code}存在需核对的大幅价格跳变；本价格模型不重建公司行动，请核实或缩短区间。")
        return raw,signal,pair.manifest
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix="quant-pair") as pool:
        values=list(pool.map(prepare,inputs.codes))
    return PortfolioExecutionInputs(inputs,dict(zip(inputs.codes,[v[0] for v in values])),
        dict(zip(inputs.codes,[v[1] for v in values])),dict(zip(inputs.codes,[v[2] for v in values])))


def _cost(quantity,price,side,config):
    if quantity<=0:
        return Decimal(0),Decimal(0)
    notional=quantity*price
    tax=config.buy_tax_bps if side=="buy" else config.sell_tax_bps
    fee=max(Decimal(str(config.min_commission)),notional*Decimal(str(config.commission_bps))/10000)
    return notional,fee+notional*Decimal(str(tax))/10000


def _lots_for_budget(desired,lot,price,budget,config):
    lo,hi=0,desired//lot
    while lo<hi:
        mid=(lo+hi+1)//2
        notional,fee=_cost(mid*lot,price,"buy",config)
        if notional+fee<=budget:lo=mid
        else:hi=mid-1
    return lo*lot


def run_cash_portfolio(raw,weights,config: CashPortfolioConfig,*,provenance=None):
    """Frozen training weights; one daily open auction, no same-close execution."""
    symbols=tuple(sorted(raw))
    if set(symbols)!=set(dict(config.lot_sizes)) or set(symbols)!=set(weights.index):
        raise ValueError("组合权重、逐股交易单位与原始行情不一致。")
    if not 2<=len(symbols)<=10 or not np.isfinite(weights.to_numpy(dtype=float)).all() or (weights<0).any() or abs(float(weights.sum())-1)>1e-8:
        raise ValueError("组合须为2至10只、同币种、非负且合计100%的训练权重。")
    execution=config.execution
    dates=raw[symbols[0]].date.reset_index(drop=True)
    if len(dates)<2 or any(not frame.date.reset_index(drop=True).equals(dates) for frame in raw.values()):
        raise ValueError("组合成交日须严格一致且至少两日。")
    for frame in raw.values():
        if not frame.date.is_monotonic_increasing or frame.date.duplicated().any() or not np.isfinite(frame[["open","close","volume"]].to_numpy(dtype=float)).all() or (frame[["open","close"]]<=0).any().any() or (frame.volume<0).any():
            raise ValueError("组合原始价格、日期或成交量无效。")
    cash=Decimal(str(execution.initial_cash))
    held={s:0 for s in symbols}
    lots=dict(config.lot_sizes)
    equity,positions,orders=[],[],[]
    total_fees=Decimal(0)
    total_turnover=Decimal(0)
    for i,stamp in enumerate(dates):
        # Monthly decisions are made at the previous month's last observed close.
        due=i>0 and (i==1 or config.frequency=="daily" or stamp.month!=dates.iloc[i-1].month or stamp.year!=dates.iloc[i-1].year)
        if due:
            prices={s:Decimal(str(raw[s].open.iloc[i])) for s in symbols}
            value=cash+sum(held[s]*prices[s] for s in symbols)
            desired={s:int(value*Decimal(str(weights[s]))/prices[s])//lots[s]*lots[s] for s in symbols}
            def blocked(symbol,side):
                if float(raw[symbol].volume.iloc[i])<=0:return "零成交量，未成交"
                if execution.market=="A 股" and execution.limit_pct is not None:
                    previous=Decimal(str(raw[symbol].close.iloc[i-1]))
                    limit=Decimal(str(execution.limit_pct))
                    if side=="buy" and prices[symbol]>=previous*(1+limit):return "触及假设涨停，未买入"
                    if side=="sell" and prices[symbol]<=previous*(1-limit):return "触及假设跌停，未卖出"
                return ""
            for symbol in symbols:
                quantity=max(0,held[symbol]-desired[symbol])
                if not quantity:continue
                reason=blocked(symbol,"sell")
                price=prices[symbol]*(1-Decimal(str(execution.slippage_bps))/10000)
                notional,fee=_cost(quantity,price,"sell",execution)
                if fee>notional:reason="费用超过卖出金额，未成交"
                filled=0 if reason else quantity
                if filled:
                    held[symbol]-=filled;cash+=notional-fee;total_fees+=fee;total_turnover+=notional
                orders.append({"decision_date":dates.iloc[i-1],"date":stamp,"symbol":symbol,"side":"sell","requested":quantity,
                    "shares":filled,"price":float(price),"fees":float(fee) if filled else 0.,"status":"blocked" if reason else "filled","reason":reason,"cash_after":float(cash)})
            requested={s:max(0,desired[s]-held[s]) for s in symbols}
            buy_prices={s:prices[s]*(1+Decimal(str(execution.slippage_bps))/10000) for s in symbols}
            needed={s:sum(_cost(requested[s],buy_prices[s],"buy",execution)) if not blocked(s,"buy") else Decimal(0) for s in symbols}
            needed_sum=sum(needed.values())
            available=cash
            for symbol in symbols:
                quantity=requested[symbol]
                if not quantity:continue
                reason=blocked(symbol,"buy")
                budget=min(needed[symbol],available*needed[symbol]/needed_sum) if needed_sum else Decimal(0)
                filled=0 if reason else _lots_for_budget(quantity,lots[symbol],buy_prices[symbol],budget,execution)
                notional,fee=_cost(filled,buy_prices[symbol],"buy",execution)
                if filled:
                    cash-=notional+fee;held[symbol]+=filled;total_fees+=fee;total_turnover+=notional
                if not reason and filled<quantity:reason="可用现金/费用或交易单位约束，未完全成交"
                orders.append({"decision_date":dates.iloc[i-1],"date":stamp,"symbol":symbol,"side":"buy","requested":quantity,
                    "shares":filled,"price":float(buy_prices[symbol]),"fees":float(fee),"status":"filled" if filled==quantity else "partial" if filled else "blocked","reason":reason,"cash_after":float(cash)})
        holdings=sum(held[s]*Decimal(str(raw[s].close.iloc[i])) for s in symbols)
        if cash<0 or any(value<0 for value in held.values()):raise ValueError("组合出现负现金或负持仓，计算终止。")
        equity.append({"date":stamp,"equity":float(cash+holdings),"cash":float(cash),"holdings_value":float(holdings),"cumulative_fees":float(total_fees),"cumulative_traded_notional":float(total_turnover)})
        positions.extend({"date":stamp,"symbol":s,"shares":held[s],"close":float(raw[s].close.iloc[i]),"value":held[s]*float(raw[s].close.iloc[i])} for s in symbols)
    from dataclasses import asdict
    manifest={"algorithm":PORTFOLIO_VERSION,"config":asdict(config),"weights":weights.to_dict(),"provenance":provenance or {},
        "raw_sha256":{s:hashlib.sha256(raw[s].to_csv(index=False).encode()).hexdigest() for s in symbols}}
    digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,default=str).encode()).hexdigest()
    curve=pd.DataFrame(equity)
    return CashPortfolioRun(curve,pd.DataFrame(positions),pd.DataFrame(orders),weights,performance_stats(curve.equity),digest,manifest)


def run_portfolio_research(inputs: PortfolioExecutionInputs,config,fraction=.7):
    comparison=inputs.comparison
    if config.execution.market!=comparison.market or not .5<=fraction<=.85:
        raise ValueError("组合市场或样本内比例与输入不匹配。")
    # A price-return cash model trains on raw returns. End-of-sample adjusted
    # levels must not smuggle later adjustment-factor revisions into weights.
    closes=pd.concat([frame.set_index("date").close.rename(code) for code,frame in inputs.raw.items()],axis=1)
    split=int(len(closes)*fraction)
    if split<4 or len(closes)-split<2:
        raise ValueError("训练或样本外区间不足；请增加共同记录。")
    train=closes.iloc[:split].pct_change(fill_method=None).dropna()
    equal=pd.Series(1/len(closes.columns),index=closes.columns,dtype=float)
    weights={"等权":equal}
    inverse_error=None
    try:weights["逆波动率"]=inverse_volatility_weights(train)
    except ValueError as error:inverse_error=str(error)
    raw={s:frame.iloc[split-1:].reset_index(drop=True) for s,frame in inputs.raw.items()}
    provenance={"input_fingerprint":comparison.fingerprint,"currency":comparison.currency,
        "input_manifests":inputs.manifests,"train_fraction":fraction,"train_last_date":str(closes.index[split-1]),
        "training_price_basis":"unadjusted","calendar_versions":{code:{"name":bundle.quality.calendar_name,
            "version":bundle.quality.calendar_version,"available":bundle.quality.calendar_available} for code,bundle in comparison.bundles.items()}}
    runs={name:run_cash_portfolio(raw,weight,config,provenance=provenance) for name,weight in weights.items()}
    return PortfolioResearch(runs,pd.DataFrame(weights),closes.index[split-1],closes.index[split],inverse_error)
