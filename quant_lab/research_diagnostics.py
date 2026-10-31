"""Derived costs, notional turnover and market exposure; no execution changes."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestDiagnostics:
    summary: dict
    costs: pd.DataFrame
    blocked: pd.DataFrame
    exposure: pd.DataFrame


def backtest_diagnostics(raw,result,config):
    equity=result.equity
    if len(equity)!=len(raw) or not equity.date.reset_index(drop=True).equals(raw.date.reset_index(drop=True)):
        raise ValueError("诊断净值与原始行情日期不一致。")
    value=equity.shares.to_numpy(dtype=float)*raw.close.to_numpy(dtype=float)
    exposure=pd.DataFrame({"date":equity.date,"position_value":value,"cash":equity.cash,
                           "exposure":value/equity.equity.to_numpy(dtype=float)})
    orders=result.orders
    filled=orders.loc[orders.status.eq("filled")] if not orders.empty else orders
    rows=[]
    opening=raw.set_index("date").open
    for order in filled.itertuples(index=False):
        notional=float(order.shares)*float(order.price)
        commission=max(config.min_commission,notional*config.commission_bps/10000)
        rate=config.buy_tax_bps if order.side=="buy" else config.sell_tax_bps
        fee=notional*rate/10000
        if not np.isclose(commission+fee,order.fees,atol=1e-8,rtol=1e-10):
            raise ValueError("成本诊断与原成交费用不一致。")
        rows.append({"date":order.date,"side":order.side,"notional":notional,"commission":commission,
            "additional_fees":fee,"charged_fees":float(order.fees),
            "slippage_estimate":float(order.shares)*abs(float(order.price)-float(opening.loc[order.date]))})
    costs=pd.DataFrame(rows,columns=("date","side","notional","commission","additional_fees","charged_fees","slippage_estimate"))
    blocked=orders.loc[orders.status.eq("blocked")].groupby("reason").size().rename("attempts").reset_index() if not orders.empty else pd.DataFrame(columns=("reason","attempts"))
    traded=float(costs.notional.sum())
    average=float(equity.equity.mean())
    summary={"order_attempts":len(orders),"filled_orders":len(filled),"blocked_orders":int(blocked.attempts.sum()),
        "commission":float(costs.commission.sum()),"additional_fees":float(costs.additional_fees.sum()),
        "charged_fees":float(costs.charged_fees.sum()),"slippage_estimate":float(costs.slippage_estimate.sum()),
        "traded_notional":traded,"notional_turnover":traded/average if average>0 else None,
        "average_exposure":float(exposure.exposure.mean()),"maximum_exposure":float(exposure.exposure.max())}
    return BacktestDiagnostics(summary,costs,blocked,exposure)
