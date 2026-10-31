"""Full-data comparison, strict execution inputs and hand-calculated AH cash."""

from dataclasses import replace
from datetime import date,datetime,timezone
import json

import numpy as np
import pandas as pd
import pytest

from quant_lab.backtest import BacktestConfig
from quant_lab.comparison import collect_comparison,compare_inputs,normalize_comparison_codes
from quant_lab.data import HistoryBundle
from quant_lab.portfolio_cash import CashPortfolioConfig,prepare_portfolio_execution,run_cash_portfolio,run_portfolio_research
from quant_lab.workspaces import WorkspaceStore,restore_values


def frame(values=(10,10,10,10,10),start="2026-01-05"):
    prices=np.asarray(values,dtype=float)
    return pd.DataFrame({"date":pd.bdate_range(start,periods=len(prices)),"open":prices,"high":prices+1,"low":prices-1,
                         "close":prices,"volume":1000.,"amount":prices*1000})


def fetcher(histories,calls=None,*,failure=None):
    def fetch(market,symbol,start,end,adjustment="",force=False):
        if calls is not None:calls.append((symbol,force))
        item=HistoryBundle(histories[symbol].copy(),market,symbol,"固定教学样本","CNY" if market=="A 股" else "HKD",adjustment,
                           datetime(2026,10,28,tzinfo=timezone.utc))
        return failure(item) if failure else item
    return fetch


def config(method="daily",cash=100,**costs):
    execution=BacktestConfig(market="A 股",initial_cash=cash,lot_size=1,commission_bps=0,min_commission=0,
        buy_tax_bps=0,sell_tax_bps=0,slippage_bps=0,limit_pct=None,**costs)
    return CashPortfolioConfig(execution,(("600519",1),("000001",1)),method)


def test_normalized_duplicates_and_mixed_currency_are_rejected_before_computing():
    with pytest.raises(ValueError):normalize_comparison_codes("A 股",("sh.600519","600519"))
    histories={"600519":frame(),"000001":frame()}
    with pytest.raises(ValueError,match="币种"):
        collect_comparison("A 股",tuple(histories),date(2026,1,1),date(2026,2,1),fetcher=fetcher(histories,failure=lambda item:replace(item,currency="HKD")))


def test_common_coverage_price_return_drawdown_and_zero_correlation():
    histories={"600519":frame((100,110,99)),"000001":frame((100,100,100))}
    inputs=collect_comparison("A 股",tuple(histories),date(2026,1,1),date(2026,2,1),fetcher=fetcher(histories))
    result=compare_inputs(inputs,"000001",2)
    assert result.normalized["600519"].tolist()==pytest.approx([100,110,99])
    assert result.drawdowns["600519"].iloc[-1]==pytest.approx(-.1)
    assert result.risk_return.loc["600519","annualized_volatility"]==pytest.approx(np.sqrt(.02*252))
    assert result.risk_return.loc["600519","relative_to_benchmark"]==pytest.approx(-.01)
    assert pd.isna(result.correlation.loc["600519","000001"])


def test_force_forwarded_coverage_and_full_resolution_ten_stocks():
    calls=[]
    codes=tuple(f"6005{i:02}" for i in range(10))
    data={code:frame(np.linspace(10+i,20+i,2609),"2016-10-27") for i,code in enumerate(codes)}
    inputs=collect_comparison("A 股",codes,date(2016,10,27),date(2026,10,27),force=True,fetcher=fetcher(data,calls))
    result=compare_inputs(inputs,codes[0],20)
    assert len(result.closes)==2609 and result.closes.shape[1]==10
    assert len(calls)==10 and all(force for _,force in calls)
    assert result.coverage.excluded_rows.eq(0).all()
    assert result.rolling_volatility.iloc[:19].isna().all().all()


def test_display_common_intersection_but_missing_internal_day_blocks_execution():
    one=frame(np.arange(12)+10)
    two=frame(np.arange(12)+20).drop(index=5).reset_index(drop=True)
    data={"600519":one,"000001":two}
    inputs=collect_comparison("A 股",tuple(data),date(2026,1,1),date(2026,2,1),fetcher=fetcher(data))
    result=compare_inputs(inputs,"600519")
    assert len(result.closes)==11
    assert result.coverage.set_index("code").loc["600519","excluded_rows"]==1
    with pytest.raises(ValueError,match="缺失成交日"):
        prepare_portfolio_execution(inputs)


def test_new_failed_fetch_never_enters_a_comparison_batch():
    data={"600519":frame(),"000001":frame()}
    with pytest.raises(ValueError,match="更新失败"):
        collect_comparison("A 股",tuple(data),date(2026,1,1),date(2026,2,1),fetcher=fetcher(data,failure=lambda item:replace(item,update_error="failed")))


def test_cash_fees_whole_units_and_next_open_hand_calculation():
    raw={"600519":frame(),"000001":frame()}
    weights=pd.Series({"600519":.5,"000001":.5})
    cfg=replace(config(),execution=replace(config().execution,min_commission=1))
    result=run_cash_portfolio(raw,weights,cfg)
    assert result.equity.iloc[0].cash==100 and result.equity.iloc[0].holdings_value==0
    assert result.positions.loc[result.positions.date==raw["600519"].date.iloc[1],"shares"].tolist()==[4,4]
    assert result.equity.iloc[1].cash==18 and result.equity.iloc[1].equity==98
    assert result.equity.iloc[1].cumulative_fees==2
    assert (result.orders.decision_date<result.orders.date).all()
    np.testing.assert_allclose(result.equity.equity,result.equity.cash+result.equity.holdings_value)


def test_rebalance_costs_zero_volume_and_concentration_do_not_borrow():
    raw={"600519":frame((10,10,20,20,20)),"000001":frame()}
    weights=pd.Series({"600519":.5,"000001":.5})
    monthly=run_cash_portfolio(raw,weights,config("monthly"))
    daily=run_cash_portfolio(raw,weights,config("daily"))
    assert len(daily.orders)>len(monthly.orders)
    assert daily.equity.cash.ge(0).all()
    raw["000001"].loc[1,"volume"]=0
    blocked=run_cash_portfolio(raw,weights,config())
    assert any("零成交量" in reason for reason in blocked.orders.reason)
    assert blocked.equity.cash.ge(0).all()


def test_oos_allocations_do_not_use_future_prices_and_constant_inverse_is_visible():
    data={"600519":frame(10+np.arange(40)*.1+np.sin(np.arange(40))*.2),
          "000001":frame(20+np.arange(40)*.08+np.cos(np.arange(40))*.1)}
    def run(values):
        observed=collect_comparison("A 股",tuple(values),date(2026,1,1),date(2026,3,20),fetcher=fetcher(values))
        return run_portfolio_research(prepare_portfolio_execution(observed),config(cash=10000),.7)
    original=run(data)
    changed={code:table.copy() for code,table in data.items()}
    for table in changed.values():
        table.loc[30:,["open","high","low","close"]]*=1.1
    altered=run(changed)
    pd.testing.assert_frame_equal(original.weights,altered.weights)
    assert original.train_last_date<original.test_first_date
    for result in original.runs.values():
        assert result.equity.iloc[0].cash==10000
        assert result.manifest["provenance"]["input_manifests"]
    data={"600519":frame([10]*40),"000001":frame([20]*40)}
    constant=run(data)
    assert constant.inverse_error and tuple(constant.runs)==("等权",)


def test_workspace_whitelist_round_trip_and_corrupt_file_preserved(tmp_path):
    target=tmp_path/"workspace-presets.json"
    store=WorkspaceStore(target)
    store.save("多股票比较",{"nav_page":"多股票比较","compare_market":"港股","compare_codes":"700,941",
        "compare_start":date(2020,1,2),"manual_panel_open":False,"private_notes":"secret note","deepseek_api_key":"secret key"})
    text=target.read_text(encoding="utf-8")
    assert "secret" not in text and "private_notes" not in text
    values=restore_values(store.activate("多股票比较"))
    assert values["compare_codes"]=="00700,00941" and values["compare_start"]==date(2020,1,2)
    assert values["manual_panel_open"] is False
    target.write_text('{"format":99}',encoding="utf-8")
    with pytest.raises(ValueError):store.save("学习",{})
    assert target.read_text(encoding="utf-8")=='{"format":99}'


def test_sina_fallback_initialization_is_serialized_across_parallel_histories(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    import time
    from quant_lab.data import AKShareProvider
    active=0
    peak=0
    guard=Lock()
    def primary(**kwargs):raise ConnectionError("offline primary")
    def fallback(**kwargs):
        nonlocal active,peak
        with guard:
            active+=1
            peak=max(peak,active)
        time.sleep(.03)
        with guard:active-=1
        return frame()
    monkeypatch.setattr("quant_lab.data.ak.stock_hk_hist",primary)
    monkeypatch.setattr("quant_lab.data.ak.stock_hk_daily",fallback)
    provider=AKShareProvider()
    with ThreadPoolExecutor(max_workers=2) as pool:
        values=list(pool.map(lambda code:provider.history("港股",code,date(2026,1,1),date(2026,2,1)),("00700","00941")))
    assert peak==1 and len(values)==2


def test_adjusted_comparison_levels_cannot_change_raw_price_training_weights():
    data={"600519":frame(10+np.arange(40)*.1+np.sin(np.arange(40))*.2),
          "000001":frame(20+np.arange(40)*.08+np.cos(np.arange(40))*.1)}
    original=fetcher(data)
    def adjusted(market,code,start,end,adjustment="",**kwargs):
        item=original(market,code,start,end,adjustment,**kwargs)
        if adjustment:
            table=item.frame.copy()
            table[["open","high","low","close"]]+=3
            return replace(item,frame=table)
        return item
    def run(adjustment):
        inputs=collect_comparison("A 股",tuple(data),date(2026,1,1),date(2026,3,20),adjustment,fetcher=adjusted)
        return run_portfolio_research(prepare_portfolio_execution(inputs,fetcher=adjusted),config(cash=10000)).weights
    pd.testing.assert_frame_equal(run(""),run("qfq"))
