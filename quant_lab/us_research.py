"""Point-in-time US signals and comparable cash-account research results."""

from collections import deque
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_lab.strategy import StrategySpec
from quant_lab.metrics import performance_stats
from quant_lab.us_backtest import USExecutionConfig, USRunResult, run_us_portfolio
from quant_lab.us_data import validate_us_prices


@dataclass(frozen=True)
class USExperiment:
    strategy: USRunResult
    benchmark: USRunResult
    price_benchmark: USRunResult
    signals: pd.DataFrame
    stats: dict


def build_us_signals(data, spec: StrategySpec):
    """Scale only the observed prefix at each split; never use future qfq factors.

    Cash dividends are not adjusted out of this price-only MA signal. Published
    event dates affect holdings independently of the strategy's target decision.
    """
    raw=validate_us_prices(data.raw)
    previous=deque(maxlen=spec.long_window)
    rows=[]
    last_long=None
    for row in raw.itertuples(index=False):
        for event in data.actions.events:
            if event.kind=="split" and event.effective_date==row.date.date():
                scale=event.denominator/event.numerator
                previous=deque((value*scale for value in previous),maxlen=spec.long_window)
                if last_long is not None:
                    last_long*=scale
        previous.append(float(row.close))
        short=sum(list(previous)[-spec.short_window:])/spec.short_window if len(previous)>=spec.short_window else None
        long=sum(previous)/spec.long_window if len(previous)>=spec.long_window else None
        active=False
        if long is not None:
            active=float(row.close)>long if spec.kind=="single_ma" else short>long if spec.kind=="dual_ma" else float(row.close)>long and last_long is not None and long>last_long
        rows.append({"date":row.date,"close":float(row.close),"ma_short":short,"ma_long":long,"signal":int(active)})
        last_long=long
    return pd.DataFrame(rows)


def run_us_experiment(data, settlement, spec=StrategySpec(), config=USExecutionConfig(), *, teaching=False):
    signals=build_us_signals(data,spec)
    symbol=data.instrument.symbol
    index=pd.DatetimeIndex(signals.date)
    weights=pd.DataFrame({symbol:signals.signal.to_numpy(dtype=float)},index=index)
    benchmark=pd.DataFrame({symbol:np.ones(len(index))},index=index)
    strategy=run_us_portfolio({symbol:data},weights,settlement,config,teaching=teaching)
    hold=run_us_portfolio({symbol:data},benchmark,settlement,config,teaching=teaching)
    price=run_us_portfolio({symbol:data},benchmark,settlement,config,teaching=teaching,include_dividends=False)
    return USExperiment(strategy,hold,price,signals,{"strategy":performance_stats(strategy.equity.equity),
        "benchmark_total":performance_stats(hold.equity.equity),"benchmark_price":performance_stats(price.equity.equity)})


def equal_weight_targets(datasets, *, rebalance="monthly"):
    if rebalance not in {"monthly","daily"}:
        raise ValueError("调仓频率仅支持monthly或daily。")
    first=next(iter(datasets.values())).raw
    index=pd.DatetimeIndex(first.date)
    targets=pd.DataFrame(np.nan,index=index,columns=sorted(datasets))
    for i,stamp in enumerate(index):
        if i==0 or rebalance=="daily" or (stamp.year,stamp.month)!=(index[i-1].year,index[i-1].month):
            targets.iloc[i,:]=1/len(datasets)
    return targets


def calculate_us_example(symbol,spec,config,rebalance):
    """Pure worker entry; never import the Streamlit workspace in a CPU child."""
    from quant_lab.us_teaching import teaching_us_inputs
    from quant_lab.us_archive import export_us_run
    datasets,settlement=teaching_us_inputs()
    experiment=run_us_experiment(datasets[symbol],settlement,spec,config,teaching=True)
    targets=equal_weight_targets(datasets,rebalance=rebalance)
    portfolio=run_us_portfolio(datasets,targets,settlement,config,teaching=True)
    report=export_us_run(datasets,targets,settlement,config,portfolio)
    return experiment,portfolio,report
