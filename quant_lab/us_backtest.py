"""Versioned US cash-account simulator; no UI, provider I/O or legacy changes."""

from dataclasses import asdict, dataclass
from datetime import datetime, time
from decimal import Decimal, ROUND_FLOOR
from fractions import Fraction
import hashlib
import json

import numpy as np
import pandas as pd

from quant_lab.us_data import USDataset, money, eligibility_issues, validate_us_prices
from quant_lab.us_market import NY, US_RULES_VERSION, SettlementCalendar, us_schedule


US_ALGORITHM_VERSION = "us-cash-v1"


@dataclass(frozen=True)
class USExecutionConfig:
    initial_cash: Decimal = Decimal("10000")
    commission_bps: Decimal = Decimal("0")
    minimum_commission: Decimal = Decimal("0")
    sell_fee_bps: Decimal = Decimal("0")
    slippage_bps: Decimal = Decimal("2")
    currency: str = "USD"

    def __post_init__(self):
        for field in ("initial_cash","commission_bps","minimum_commission","sell_fee_bps","slippage_bps"):
            object.__setattr__(self,field,money(getattr(self,field)))
        if self.initial_cash<=0 or any(getattr(self,f)<0 for f in ("commission_bps","minimum_commission","sell_fee_bps","slippage_bps")):
            raise ValueError("初始美元资金须为正，费用与滑点不能为负。")
        if self.slippage_bps>=10000 or self.currency!="USD":
            raise ValueError("美股现金模型仅使用USD，滑点须小于100%。")


@dataclass(frozen=True)
class USRunResult:
    equity: pd.DataFrame
    orders: pd.DataFrame
    cash_ledger: pd.DataFrame
    positions: pd.DataFrame
    manifest: dict
    audit_id: str


def _cost(quantity, price, side, config):
    if quantity<=0:
        return Decimal(0),Decimal(0)
    notional=quantity*price
    fee=max(config.minimum_commission,notional*config.commission_bps/10000)
    if side=="sell":
        fee+=notional*config.sell_fee_bps/10000
    return notional,fee


def _affordable(desired,price,budget,config):
    lo,hi=0,desired
    while lo<hi:
        mid=(lo+hi+1)//2
        notional,fee=_cost(mid,price,"buy",config)
        if notional+fee<=budget:
            lo=mid
        else:
            hi=mid-1
    return lo


def _event_dict(event):
    return {key:(value.isoformat() if hasattr(value,"isoformat") else str(value) if isinstance(value,Decimal) else value)
            for key,value in asdict(event).items()}


def run_us_portfolio(datasets: dict[str, USDataset], targets: pd.DataFrame,
                     settlement: SettlementCalendar, config=USExecutionConfig(), *,
                     teaching=False, include_dividends=True) -> USRunResult:
    """Close-date target weights execute only at the next normal session open.

    NaN rows mean no rebalancing instruction. Complete rows request that day's
    target at the next open; partially funded requests are not filled early.
    Dividend income is recognized at ex-date, spendable only at verified pay_at.
    This research model has no tax/ADR, lending, fractional share or due-bill model.
    """
    if not 1<=len(datasets)<=10:
        raise ValueError("美元组合需要1至10只同币种证券。")
    symbols=tuple(sorted(datasets))
    frames={}
    for symbol,data in datasets.items():
        if symbol!=data.instrument.symbol:
            raise ValueError("组合键与证券身份不匹配。")
        issues=eligibility_issues(data,settlement,teaching=teaching)
        if issues:
            raise ValueError(f"{symbol}禁止回测："+"；".join(issues))
        frames[symbol]=validate_us_prices(data.raw).reset_index(drop=True)
    dates=frames[symbols[0]].date
    if any(not frame.date.equals(dates) for frame in frames.values()):
        raise ValueError("美元组合要求相同完整交易日，不取交集或填充成交价格。")
    if len(dates)<2 or tuple(sorted(targets.columns))!=symbols or not targets.index.equals(pd.DatetimeIndex(dates)):
        raise ValueError("目标权重必须与全部证券和交易日期严格对齐，至少两个交易日。")
    weights=targets.loc[:,list(symbols)].apply(pd.to_numeric,errors="raise")
    partial=weights.isna().any(axis=1)&~weights.isna().all(axis=1)
    finite=weights.dropna()
    if partial.any() or not np.isfinite(finite.to_numpy(dtype=float)).all() or (finite<0).any().any() or (finite.sum(axis=1)>1+1e-12).any():
        raise ValueError("每行权重须全部给定或全部留空；只做多、无杠杆，权重合计不能超过1。")
    schedule=us_schedule(dates.iloc[0].date(),dates.iloc[-1].date())
    cash=config.initial_cash
    holdings={symbol:0 for symbol in symbols}
    pending=[]  # (available timestamp, amount, kind, symbol, event id)
    rows,orders,ledger,positions=[],[],[],[]

    def record(day,kind,symbol,amount,event_id="",available=None,share_delta=0):
        ledger.append({"date":day,"kind":kind,"symbol":symbol,"amount_usd":float(amount),
                       "event_id":event_id,"available_at":available.isoformat() if available else None,"share_delta":share_delta})

    def release(until,day):
        nonlocal cash,pending
        remaining=[]
        for available,amount,kind,symbol,event_id in pending:
            if available<=until:
                cash+=amount
                record(day,kind+"_available",symbol,amount,event_id,available)
            else:
                remaining.append((available,amount,kind,symbol,event_id))
        pending=remaining

    for i,stamp in enumerate(dates):
        day=stamp.date()
        opening=schedule.loc[str(day),"open"].to_pydatetime()
        closing=schedule.loc[str(day),"close"].to_pydatetime()
        release(opening,day)
        for symbol in symbols:
            for event in datasets[symbol].actions.events:
                if event.effective_date!=day:
                    continue
                if event.kind=="split":
                    changed=Fraction(holdings[symbol])*event.split_ratio
                    if changed.denominator!=1:
                        raise ValueError(f"{day} {symbol}拆股产生碎股，首版未验证现金替代，阻止跨事件回测。")
                    before=holdings[symbol]
                    holdings[symbol]=changed.numerator
                    record(day,"split_shares",symbol,Decimal(0),event.event_id,share_delta=holdings[symbol]-before)
                elif event.kind=="dividend" and include_dividends:
                    if event.pay_at<opening:
                        raise ValueError("普通股息支付时刻早于除息开盘，需特殊分派/到期交割适配。")
                    amount=holdings[symbol]*money(event.amount_per_share)
                    pending.append((event.pay_at,amount,"dividend",symbol,event.event_id))
                    record(day,"dividend_receivable",symbol,amount,event.event_id,event.pay_at)
        release(opening,day)
        if i>0 and not weights.iloc[i-1].isna().all():
            mid={s:money(frames[s].open.iloc[i]) for s in symbols}
            total=cash+sum((item[1] for item in pending),Decimal(0))+sum((holdings[s]*mid[s] for s in symbols),Decimal(0))
            desired={s:int((total*money(weights[s].iloc[i-1])/mid[s]).to_integral_value(rounding=ROUND_FLOOR)) for s in symbols}
            for symbol in symbols:
                quantity=max(0,holdings[symbol]-desired[symbol])
                if not quantity:
                    continue
                price=mid[symbol]*(1-config.slippage_bps/10000)
                notional,fee=_cost(quantity,price,"sell",config)
                reason="零成交量" if frames[symbol].volume.iloc[i]<=0 else "费用超过卖出金额" if fee>notional else ""
                due,rule=settlement.due(day)
                if not reason:
                    holdings[symbol]-=quantity
                    available=datetime.combine(due,time.min,NY)
                    pending.append((available,notional-fee,"sale",symbol,""))
                    record(day,"sale_unsettled",symbol,notional-fee,available=available)
                orders.append({"decision_date":dates.iloc[i-1],"date":stamp,"symbol":symbol,"side":"sell",
                    "requested_shares":quantity,"shares":0 if reason else quantity,"price":float(price),
                    "fees":0. if reason else float(fee),"status":"blocked" if reason else "filled","reason":reason,
                    "settlement_date":str(due),"rule_version":rule})
            requests={s:max(0,desired[s]-holdings[s]) for s in symbols}
            prices={s:mid[s]*(1+config.slippage_bps/10000) for s in symbols}
            costs={s:sum(_cost(requests[s],prices[s],"buy",config)) for s in symbols}
            total_cost=sum(costs.values(),Decimal(0))
            available_cash=cash
            for symbol in symbols:
                requested=requests[symbol]
                if not requested:
                    continue
                budget=min(costs[symbol],available_cash*costs[symbol]/total_cost) if total_cost else Decimal(0)
                quantity=_affordable(requested,prices[symbol],budget,config)
                reason="零成交量" if frames[symbol].volume.iloc[i]<=0 else "仅使用已结算现金，资金不足" if quantity<requested else ""
                if frames[symbol].volume.iloc[i]<=0:
                    quantity=0
                notional,fee=_cost(quantity,prices[symbol],"buy",config)
                cash-=notional+fee
                holdings[symbol]+=quantity
                due,rule=settlement.due(day)
                if quantity:
                    record(day,"buy_cash",symbol,-notional-fee)
                orders.append({"decision_date":dates.iloc[i-1],"date":stamp,"symbol":symbol,"side":"buy",
                    "requested_shares":requested,"shares":quantity,"price":float(prices[symbol]),"fees":float(fee),
                    "status":"filled" if quantity==requested else "partial" if quantity else "blocked","reason":reason,
                    "settlement_date":str(due),"rule_version":rule})
        release(closing,day)
        unsettled=sum((item[1] for item in pending if item[2]=="sale"),Decimal(0))
        receivable=sum((item[1] for item in pending if item[2]=="dividend"),Decimal(0))
        value=sum((holdings[s]*money(frames[s].close.iloc[i]) for s in symbols),Decimal(0))
        if cash<0 or any(shares<0 for shares in holdings.values()):
            raise ValueError("现金账户出现负现金或负持仓，计算终止。")
        rows.append({"date":stamp,"equity":float(cash+unsettled+receivable+value),"settled_cash":float(cash),
                     "unsettled_sale_cash":float(unsettled),"dividend_receivable":float(receivable),"holdings_value":float(value)})
        positions.extend({"date":stamp,"symbol":s,"shares":holdings[s],"close":float(frames[s].close.iloc[i])} for s in symbols)
    manifest={"algorithm":US_ALGORITHM_VERSION,"rules":US_RULES_VERSION,"currency":"USD","teaching":teaching,
        "include_dividends":include_dividends,"config":{k:str(v) for k,v in asdict(config).items()},
        "settlement_calendar":{"version":settlement.version,"evidence":settlement.evidence,
            "start":str(settlement.start),"end":str(settlement.end),"dates":[str(d) for d in settlement.dates]},
        "inputs":{s:{"identity":asdict(datasets[s].instrument),"source":datasets[s].source,
            "received_at":datasets[s].received_at.isoformat(),"price_basis":datasets[s].price_basis,
            "raw_price_evidence":datasets[s].raw_price_evidence,"input_version":datasets[s].input_version,
            "actions":{"start":str(datasets[s].actions.start),"end":str(datasets[s].actions.end),
                "known":datasets[s].actions.known,"evidence":datasets[s].actions.evidence,
                "events":[_event_dict(e) for e in datasets[s].actions.events]},
            "retention":datasets[s].retention.to_dict(),
            "raw_sha256":hashlib.sha256(frames[s].to_csv(index=False).encode()).hexdigest()} for s in symbols},
        "targets_sha256":hashlib.sha256(targets.to_csv().encode()).hexdigest()}
    audit=hashlib.sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return USRunResult(pd.DataFrame(rows),pd.DataFrame(orders),pd.DataFrame(ledger),pd.DataFrame(positions),manifest,"us-v1:"+audit[:24])
