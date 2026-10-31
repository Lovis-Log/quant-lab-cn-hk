"""Hand-calculated US cash, event, calendar, provenance and replay examples."""

from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from quant_lab.us_market import USInstrument,SettlementCalendar,NY,normalize_us_symbol,session_information,settlement_lag,us_schedule
from quant_lab.us_data import USDataset,USAction,USActionBook,eligibility_issues,validate_us_prices
from quant_lab.us_backtest import USExecutionConfig,run_us_portfolio
from quant_lab.us_research import build_us_signals,run_us_experiment,equal_weight_targets
from quant_lab.us_archive import export_us_run,replay_us_run
from quant_lab.us_teaching import TEACHING_US_RIGHTS,teaching_us_inputs
from quant_lab.strategy import StrategySpec


def inputs(prices=(10,10,10,10,10),symbol="TEST",events=()):
    start=date(2024,6,3)
    days=pd.DatetimeIndex(us_schedule(start,start+timedelta(days=15)).index)[:len(prices)]
    values=np.array(prices,dtype=float)
    raw=pd.DataFrame({"date":days,"open":values,"high":values+1,"low":values-1,"close":values,"volume":1000.})
    instrument=USInstrument(symbol,"生成的测试身份","XNYS",identity_evidence="test-generated")
    end=days[-1].date()
    data=USDataset(instrument,raw,"固定教学样本",datetime(2025,1,1,tzinfo=timezone.utc),
        USActionBook(symbol,start,end,True,"generated-complete",tuple(events)),"generated-execution","unadjusted-execution",TEACHING_US_RIGHTS,True)
    cal=SettlementCalendar(start,end+timedelta(days=20),tuple(us_schedule(start,end+timedelta(days=20)).index.date),
        "test-settlement-v1","explicit test calendar, not production",True)
    return data,cal


def targets(data,values):
    return pd.DataFrame({data.instrument.symbol:values},index=pd.DatetimeIndex(data.raw.date))


def config(cash=100,**kwargs):
    return USExecutionConfig(initial_cash=cash,slippage_bps=0,**kwargs)


def action(kind,day,**kwargs):
    return USAction("event-"+kind,"TEST",kind,day,"test-event",datetime(2024,1,1,tzinfo=timezone.utc),**kwargs)


def test_identity_class_codes_source_mapping_and_currency():
    instrument=USInstrument("BRK.B","类别股测试","XNYS","class_share",source_codes=(("source-one","BRK-B"),("source-two","BRK.B")),identity_evidence="test")
    assert normalize_us_symbol(" brk.b ")=="BRK.B"
    assert instrument.source_symbol("source-one")=="BRK-B"
    with pytest.raises(ValueError):normalize_us_symbol("BRK-B")
    with pytest.raises(ValueError):instrument.source_symbol("unknown")
    with pytest.raises(ValueError):replace(instrument,currency="HKD")


def test_us_sessions_dst_holiday_and_early_close():
    assert session_information(date(2024,3,8))["open_utc"].startswith("2024-03-08T14:30")
    assert session_information(date(2024,3,11))["open_utc"].startswith("2024-03-11T13:30")
    assert not session_information(date(2024,11,28))["is_session"]
    after=session_information(date(2024,11,29))
    assert after["early_close"] and "T13:00" in after["close_new_york"]


def test_historical_settlement_rule_and_separate_bank_holiday_calendar():
    assert settlement_lag(date(2017,9,1))[0]==3
    assert settlement_lag(date(2017,9,5))[0]==2
    assert settlement_lag(date(2024,5,24))[0]==2
    assert settlement_lag(date(2024,5,28))[0]==1
    # NYSE opens on Oct 14, but this explicitly provided settlement calendar
    # omits that banking holiday. A price calendar must not erase the difference.
    assert session_information(date(2024,10,14))["is_session"]
    cal=SettlementCalendar(date(2024,10,11),date(2024,10,18),
        (date(2024,10,11),date(2024,10,15),date(2024,10,16),date(2024,10,17),date(2024,10,18)),"test-bank","test",True)
    assert cal.due(date(2024,10,11))[0]==date(2024,10,15)
    with pytest.raises(ValueError):cal.due(date(2024,10,18))


def test_next_open_execution_whole_shares_and_costs_are_hand_calculable():
    data,cal=inputs((10,10,10,10,10))
    result=run_us_portfolio({"TEST":data},targets(data,[1,1,1,1,1]),cal,config(100,minimum_commission=1),teaching=True)
    assert result.positions.iloc[0].shares==0
    assert result.orders.iloc[0]["date"]==data.raw.date.iloc[1]
    assert result.orders.iloc[0].shares==9
    assert result.equity.iloc[1].settled_cash==9
    assert result.equity.iloc[1].equity==99
    assert result.orders.iloc[0].fees==1
    assert (result.positions.shares%1==0).all()


def test_sold_proceeds_cannot_fund_another_stock_before_settlement():
    first,cal=inputs()
    second,_=inputs(symbol="OTHER")
    weights=pd.DataFrame({"TEST":[1,0,0,0,0],"OTHER":[0,1,1,1,1]},index=pd.DatetimeIndex(first.raw.date))
    result=run_us_portfolio({"TEST":first,"OTHER":second},weights,cal,config(),teaching=True)
    switch=result.equity.iloc[2]
    assert switch.unsettled_sale_cash==100 and switch.settled_cash==0
    blocked=result.orders.loc[(result.orders.symbol=="OTHER")&(result.orders.date==first.raw.date.iloc[2])].iloc[0]
    assert blocked.shares==0 and "已结算现金" in blocked.reason
    bought=result.orders.loc[(result.orders.symbol=="OTHER")&(result.orders.date==first.raw.date.iloc[3])].iloc[0]
    assert bought.shares==10


@pytest.mark.parametrize("numerator,denominator,prices,expected",[
    (2,1,(10,10,5,5,5),20), (1,2,(10,10,20,20,20),5)])
def test_split_and_reverse_split_preserve_wealth(numerator,denominator,prices,expected):
    data,cal=inputs(prices,events=(action("split",date(2024,6,5),numerator=numerator,denominator=denominator),))
    result=run_us_portfolio({"TEST":data},targets(data,[1]*5),cal,config(),teaching=True)
    assert result.positions.iloc[2].shares==expected
    assert result.equity.equity.eq(100).all()
    split=result.cash_ledger.loc[result.cash_ledger.kind=="split_shares"].iloc[0]
    assert split.amount_usd==0 and split.share_delta==expected-10


def test_reverse_split_fractional_position_is_blocked_without_cash_in_lieu():
    data,cal=inputs((10,10,20,20,20),events=(action("split",date(2024,6,5),numerator=1,denominator=2),))
    with pytest.raises(ValueError,match="碎股"):
        run_us_portfolio({"TEST":data},targets(data,[1]*5),cal,config(90),teaching=True)


def test_dividend_receivable_not_spendable_before_verified_payment():
    event=action("dividend",date(2024,6,5),amount_per_share=Decimal(1),pay_at=datetime(2024,6,7,17,tzinfo=NY))
    data,cal=inputs((10,10,9,9,9,9,9),events=(event,))
    result=run_us_portfolio({"TEST":data},targets(data,[1]*7),cal,config(),teaching=True)
    ex=result.equity.iloc[2]
    assert ex.dividend_receivable==10 and ex.settled_cash==0 and ex.equity==100
    assert result.positions.iloc[4].shares==10  # Pay-day close precedes 17:00.
    assert result.positions.iloc[5].shares==11  # Next session open can spend it.
    assert result.equity.iloc[5].dividend_receivable==0 and result.equity.iloc[5].equity==100


def test_dividend_entitlement_survives_sale_before_payday():
    event=action("dividend",date(2024,6,5),amount_per_share=Decimal(1),pay_at=datetime(2024,6,7,15,tzinfo=NY))
    data,cal=inputs((10,10,9,9,9),events=(event,))
    result=run_us_portfolio({"TEST":data},targets(data,[1,0,0,0,0]),cal,config(),teaching=True)
    assert result.positions.iloc[2].shares==0
    assert result.equity.iloc[2].dividend_receivable==10
    assert result.equity.iloc[-1].settled_cash==100


def test_date_only_verified_dividend_is_conservatively_available_after_payment_day():
    event=action("dividend",date(2024,6,5),amount_per_share=Decimal(1),payment_date=date(2024,6,7))
    assert event.availability_assumption=="after-payment-date"
    assert event.pay_at==datetime(2024,6,8,0,tzinfo=NY)
    data,cal=inputs((10,10,9,9,9,9),events=(event,))
    result=run_us_portfolio({"TEST":data},targets(data,[1]*6),cal,config(),teaching=True)
    assert result.equity.iloc[4].dividend_receivable==10
    assert result.equity.iloc[5].dividend_receivable==0
    with pytest.raises(ValueError,match="不一致"):
        replace(event,pay_at=datetime(2024,6,7,9,tzinfo=NY))


@pytest.mark.parametrize("which",["unknown_actions","unknown_identity","unknown_price","unknown_rights","unverified_settlement","late_event","unsupported"])
def test_live_or_unknown_inputs_fail_closed(which):
    data,cal=inputs()
    if which=="unknown_actions": data=replace(data,actions=replace(data.actions,known=False))
    if which=="unknown_identity":data=replace(data,instrument=replace(data.instrument,identity_evidence=""))
    if which=="unknown_price":data=replace(data,price_basis="unverified")
    if which=="unknown_rights":data=replace(data,retention=replace(data.retention,allowed=False))
    if which=="unverified_settlement":cal=replace(cal,verified=False)
    if which=="late_event":
        event=replace(action("split",date(2024,6,5)),known_at=datetime(2024,6,5,20,tzinfo=timezone.utc))
        data=replace(data,actions=replace(data.actions,events=(event,)))
    if which=="unsupported":data=replace(data,actions=replace(data.actions,events=(action("spinoff",date(2024,6,5)),)))
    with pytest.raises(ValueError,match="禁止回测"):
        run_us_portfolio({"TEST":data},targets(data,[1]*5),cal,config(),teaching=True)


def test_missing_trading_day_and_same_day_events_are_not_silently_filled():
    data,cal=inputs()
    broken=replace(data,raw=data.raw.drop(index=2).reset_index(drop=True))
    assert any("交易日缺失" in text for text in eligibility_issues(broken,cal,teaching=True))
    split=action("split",date(2024,6,5),numerator=2)
    dividend=action("dividend",date(2024,6,5),amount_per_share=Decimal(1),pay_at=datetime(2024,6,7,15,tzinfo=NY))
    both=replace(data,actions=replace(data.actions,events=(split,dividend)))
    assert any("同日拆股" in text for text in eligibility_issues(both,cal,teaching=True))


def test_future_splits_do_not_change_earlier_signals_and_split_prefix_is_rescaled():
    datasets,_=teaching_us_inputs()
    data=datasets["TEACHA"]
    prefix=replace(data,raw=data.raw.iloc[:10].copy())
    spec=StrategySpec("dual_ma",2,3)
    pd.testing.assert_frame_equal(build_us_signals(data,spec).iloc[:10].reset_index(drop=True),build_us_signals(prefix,spec))
    data,_=inputs((10,12,14,7,8),events=(action("split",date(2024,6,6),numerator=2),))
    signal=build_us_signals(data,spec)
    assert signal.ma_long.iloc[3]==pytest.approx((6+7+7)/3)


def test_portfolio_cash_positions_weights_and_fair_benchmark():
    datasets,cal=teaching_us_inputs()
    data=datasets["TEACHA"]
    cfg=config(10000)
    experiment=run_us_experiment(data,cal,StrategySpec("dual_ma",2,3),cfg,teaching=True)
    assert experiment.benchmark.manifest["config"]==experiment.strategy.manifest["config"]
    assert experiment.stats["benchmark_total"].ending_equity>experiment.stats["benchmark_price"].ending_equity
    portfolio=run_us_portfolio(datasets,equal_weight_targets(datasets),cal,cfg,teaching=True)
    np.testing.assert_allclose(portfolio.equity.equity,
        portfolio.equity.settled_cash+portfolio.equity.unsettled_sale_cash+portfolio.equity.dividend_receivable+portfolio.equity.holdings_value)
    assert portfolio.equity.settled_cash.ge(0).all() and portfolio.positions.shares.ge(0).all()


def test_versioned_export_replays_offline_and_rejects_tampering_or_new_algorithm():
    data,cal=teaching_us_inputs()
    cfg=config(10000)
    weights=equal_weight_targets(data)
    result=run_us_portfolio(data,weights,cal,cfg,teaching=True)
    payload=export_us_run(data,weights,cal,cfg,result)
    replay=replay_us_run(payload)
    assert replay.audit_id==result.audit_id
    pd.testing.assert_frame_equal(replay.equity,result.equity)
    changed=json.loads(payload)
    changed["body"]["equity_csv"]+="corrupted"
    with pytest.raises(ValueError,match="校验失败"):replay_us_run(json.dumps(changed).encode())
    changed=json.loads(payload)
    changed["body"]["algorithm"]="future-v2"
    encoded=json.dumps(changed["body"],sort_keys=True,ensure_ascii=False,separators=(",",":"))
    changed["sha256"]=hashlib.sha256(encoded.encode()).hexdigest()
    with pytest.raises(ValueError,match="算法/规则版本"):replay_us_run(json.dumps(changed).encode())


def test_invalid_price_calendar_weights_and_teaching_cannot_open_live_path():
    data,cal=inputs()
    frame=data.raw.copy()
    frame["volume"]=True
    with pytest.raises(ValueError):validate_us_prices(frame)
    with pytest.raises(ValueError,match="禁止回测"):
        run_us_portfolio({"TEST":data},targets(data,[1]*5),cal,config())
    with pytest.raises(ValueError,match="权重"):
        run_us_portfolio({"TEST":data},targets(data,[1.1]*5),cal,config(),teaching=True)
    with pytest.raises(ValueError):config(True)
