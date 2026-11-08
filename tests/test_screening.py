"""Hand calculations, independent-symbol failures and cooperative cancellation."""
from dataclasses import replace
from datetime import datetime, timezone
from threading import Event
import json
import time
import numpy as np
import pandas as pd
import pytest
from quant_lab.screening import ScreenRecipe, price_metrics, evaluate_screen, collect_screen
from quant_lab.screen_presets import ScreenPresetStore
from quant_lab.data_quality import calendar_reference
from quant_lab.data import HistoryBundle
from quant_lab.jobs import JobManager, JobState


def fixture(market="A 股", symbol="600519", n=80):
    start, end = pd.Timestamp("2025-01-02").date(), pd.Timestamp("2025-07-01").date()
    dates = [day for day, _ in calendar_reference(market,start,end).sessions][:n]
    close = 10 + np.arange(len(dates)) * .1
    frame = pd.DataFrame({"date":pd.to_datetime(dates),"open":close,"high":close+1,"low":close-1,"close":close,"volume":1000.,"amount":close*1000})
    return HistoryBundle(frame,market,symbol,"隔离教学数据",{"A 股":"CNY","港股":"HKD","美股":"USD"}[market],"",received_at=datetime(2026,11,1,tzinfo=timezone.utc))


def test_metrics_hand_calculation_and_missing_samples():
    frame = fixture().frame
    values = price_metrics(frame)
    assert values["return20"] == pytest.approx(17.9/15.9-1)
    assert values["return60"] == pytest.approx(17.9/11.9-1)
    assert values["drawdown60"] == 0
    assert values["volatility20"] == pytest.approx(frame.close.iloc[-21:].pct_change().dropna().std(ddof=1)*np.sqrt(252))
    assert values["volume_ratio"] == 1 and values["above_ma30"] == 1
    frame.loc[:,"volume"] = 0
    assert price_metrics(frame)["volume_ratio"] is None
    assert price_metrics(frame.iloc[:2])["return20"] is None
    frame.loc[frame.index[-1],"close"] = 10
    assert price_metrics(frame)["drawdown60"] == pytest.approx(1-10/17.8)


def test_bounds_all_enabled_and_missing_metric_not_zero():
    recipe=ScreenRecipe("A 股",("600519",),bounds=(("return20",.1,None),("volume_ratio",1,2)))
    row={"code":"600519","status":"合格",**price_metrics(fixture().frame)}
    assert evaluate_screen([row],recipe).matched.iloc[0]
    row["volume_ratio"]=None
    assert not evaluate_screen([row],recipe).matched.iloc[0]
    assert evaluate_screen([row],replace(recipe,bounds=())).matched.iloc[0]


@pytest.mark.parametrize("market,codes",[("A 股",("600519","000001")),("港股",("00700","00941")),("美股",("AAPL","MSFT"))])
def test_partial_failure_force_and_metadata(market,codes):
    item=fixture(market,codes[0])
    calls=[]
    def fetch(market,code,*args,**kwargs):
        calls.append(kwargs["force"])
        if code==codes[1]: raise ValueError("测试来源失败")
        return item
    result=collect_screen(ScreenRecipe(market,codes),item.frame.date.iloc[0].date(),item.frame.date.iloc[-1].date(),"test",force=True,fetcher=fetch,spacing=0)
    assert calls==[True,True]
    assert result.table.status.tolist()==["合格","失败"]
    assert result.table.matched.tolist()==[True,False]
    assert "来源失败" in result.table.error.iloc[-1]
    assert result.table.source.iloc[0]==item.source


@pytest.mark.parametrize("damage",["identity","stale","missing","jump","receive"])
def test_bad_data_is_visible_and_excluded(damage):
    item=fixture()
    end=item.frame.date.iloc[-1].date()
    if damage=="identity": item=replace(item,currency="USD")
    elif damage=="stale": item=replace(item,update_error="offline")
    elif damage=="missing": item=replace(item,frame=item.frame.drop(index=20))
    elif damage=="receive": item=replace(item,received_at=None)
    else:
        frame=item.frame.copy();frame.loc[30,["open","high","low","close"]]*=2
        item=replace(item,frame=frame)
    result=collect_screen(ScreenRecipe("A 股",("600519",)),item.frame.date.iloc[0].date(),end,"test",fetcher=lambda *a,**k:item,spacing=0)
    assert not result.table.matched.any() and result.table.error.iloc[0]


def test_limit_duplicate_and_unknown_conditions():
    with pytest.raises(ValueError): ScreenRecipe("A 股",tuple(f"600{i:03}" for i in range(21))).validate()
    with pytest.raises(ValueError): ScreenRecipe("美股",("AAPL","AAPL")).validate()
    with pytest.raises(ValueError): ScreenRecipe("美股",("AAPL",),adjustment="qfq").validate()
    with pytest.raises(ValueError): ScreenRecipe("A 股",("600519",),bounds=(("return20",1,0),)).validate()


def test_presets_whitelist_atomic_backup_and_corruption(tmp_path):
    store=ScreenPresetStore(tmp_path/"recipes.json")
    recipe=ScreenRecipe("美股",("AAPL",))
    store.write("测试",recipe)
    store.write("测试",replace(recipe,ascending=True))
    assert store.load()["测试"].ascending
    assert store.path.with_suffix(".json.bak").exists()
    payload=json.loads(store.path.read_text(encoding="utf-8"))
    payload["recipes"]["测试"]["raw_prices"]=[10]
    store.path.write_text(json.dumps(payload),encoding="utf-8")
    before=store.path.read_bytes()
    with pytest.raises(ValueError):store.write("其他",recipe)
    assert store.path.read_bytes()==before


def test_cooperative_batch_cancel_stops_new_symbols():
    item=fixture(); gate=Event(); started=Event(); calls=[]
    def fetch(market,code,*args,**kwargs):
        calls.append(code);started.set();gate.wait(5)
        return replace(item,symbol=code)
    manager=JobManager()
    try:
        recipe=ScreenRecipe("A 股",tuple(f"600{i:03}" for i in range(20)))
        identifier=manager.submit("scope","screening","one",collect_screen,recipe,item.frame.date.iloc[0].date(),item.frame.date.iloc[-1].date(),"test",fetcher=fetch,spacing=0,cooperative_io=True)
        assert started.wait(2)
        assert manager.submit("scope","screening","one",collect_screen)==identifier
        manager.cancel(identifier,"scope");gate.set()
        assert manager.get(identifier,"scope").state==JobState.CANCELLED
        time.sleep(.15)
        assert len(calls)<=2
    finally:gate.set();manager.close()


def test_cooperative_timeout_discards_late_result():
    observed=Event()
    def task(*,cancelled):
        deadline=time.monotonic()+3
        while not cancelled() and time.monotonic()<deadline:time.sleep(.005)
        observed.set()
        return "late"
    manager=JobManager()
    try:
        identifier=manager.submit('scope','test','timeout',task,cooperative_io=True,timeout=.03)
        assert observed.wait(2)
        snapshot=manager.get(identifier,'scope')
        assert snapshot.state==JobState.FAILED and snapshot.result is None
        with pytest.raises(ValueError): manager.submit('scope','test','cpu',task,cpu=True,cooperative_io=True)
    finally:manager.close()


def test_request_spacing_and_maximum_concurrency():
    item=fixture(); starts=[]
    def fetch(market,code,*args,**kwargs):
        starts.append(time.monotonic())
        return replace(item,symbol=code)
    codes=('600519','000001','600036')
    collect_screen(ScreenRecipe('A 股',codes),item.frame.date.iloc[0].date(),item.frame.date.iloc[-1].date(),'test',fetcher=fetch,spacing=.03)
    assert len(starts)==3
    assert all(b-a>=.025 for a,b in zip(starts,starts[1:]))


def test_name_lookup_failure_does_not_invalidate_prices(monkeypatch):
    item=fixture()
    def failed(*args,**kwargs):raise RuntimeError('name service failed')
    monkeypatch.setattr('quant_lab.names.cached_security_name',failed)
    result=collect_screen(ScreenRecipe('A 股',('600519',)),item.frame.date.iloc[0].date(),item.frame.date.iloc[-1].date(),'test',fetcher=lambda *a,**k:item,spacing=0)
    assert result.table.matched.iloc[0]
    assert result.table.name.iloc[0]=='名称暂不可用'
