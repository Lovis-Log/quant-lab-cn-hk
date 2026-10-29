"""Validation causality, continuous folds, diagnostics, versioning and offline replay."""

from dataclasses import replace
from datetime import datetime,timezone
import io,json
from zipfile import ZipFile,ZIP_DEFLATED

import numpy as np
import pandas as pd
import pytest

from quant_lab.backtest import BacktestConfig,run_backtest
from quant_lab.data import HistoryBundle
from quant_lab.source_rights import TEACHING_RETENTION
from quant_lab.strategy import StrategySpec
from quant_lab.research_diagnostics import backtest_diagnostics
from quant_lab.research_validation import ValidationRecipe,run_validation
from quant_lab.research_reports import prepare_lab_inputs,calculate_lab,export_validation_report,replay_report,replay_saved_validation
from quant_lab.research_versions import LEGACY_VERSIONS,VALIDATION_VERSIONS
from quant_lab.storage import save_experiment,get_experiment,export_experiment_zip,replay_experiment,render_report
from quant_lab.experiment_comparison import session_case,compare_cases,load_saved_cases


def history(n=180):
    price=100+np.arange(n)*.1+np.sin(np.arange(n)*.4)*3
    return pd.DataFrame({"date":pd.bdate_range("2025-01-02",periods=n),"open":price,"high":price+1,"low":price-1,
                         "close":price,"volume":10000.,"amount":price*10000})


def config(**kwargs):
    base=BacktestConfig(initial_cash=10000,lot_size=1,commission_bps=0,min_commission=0,
        buy_tax_bps=0,sell_tax_bps=0,slippage_bps=0,limit_pct=None)
    return replace(base,**kwargs)


def recipe():
    return ValidationRecipe(StrategySpec("dual_ma",5,20),config(),(2,4),(8,12),.6,60,30,3)


def prepared(raw=None):
    return prepare_lab_inputs(HistoryBundle(history() if raw is None else raw,"A 股","600519","固定教学样本","CNY","",
        datetime(2026,1,1,tzinfo=timezone.utc),retention=TEACHING_RETENTION))


def test_fee_slippage_turnover_and_exposure_hand_calculation():
    raw=history(4)
    raw[["open","close"]]=10.
    costs=config(initial_cash=1000,commission_bps=10,min_commission=1,buy_tax_bps=2,sell_tax_bps=3,slippage_bps=100)
    result=run_backtest(raw,pd.Series([1,0,0,0]),costs)
    diag=backtest_diagnostics(raw,result,costs)
    assert result.orders.shares.tolist()==[98,98]
    assert diag.summary["commission"]==2
    assert diag.summary["additional_fees"]==pytest.approx(.48902)
    assert diag.summary["charged_fees"]==pytest.approx(2.48902)
    assert diag.summary["slippage_estimate"]==pytest.approx(19.6)
    assert result.equity.equity.iloc[-1]==pytest.approx(977.91098)
    assert diag.summary["notional_turnover"]==pytest.approx(1960/result.equity.equity.mean())
    assert diag.exposure.exposure.between(0,1).all()


def test_grid_and_fold_selection_do_not_read_their_future_tests():
    raw=history(180)
    cfg=recipe()
    original=run_validation(raw,cfg)
    changed=raw.copy()
    split=int(len(raw)*cfg.train_fraction)
    changed.loc[split:,["open","high","low","close"]]*=1.05
    altered=run_validation(changed,cfg)
    pd.testing.assert_frame_equal(original.scan,altered.scan)
    # Recent folds start at index 90; mutate only after the first fold's train.
    first_test=raw.index[raw.date.eq(original.folds.test_start.iloc[0])][0]
    changed=raw.copy()
    changed.loc[first_test:,["open","high","low","close"]]*=1.05
    altered=run_validation(changed,cfg)
    for field in ("short","long","training_score"):
        assert original.folds.iloc[0][field]==pytest.approx(altered.folds.iloc[0][field])
    assert (original.folds.train_end<original.folds.test_start).all()


def test_continuous_rolling_folds_do_not_reset_or_buy_again_for_free():
    raw=history(160)
    price=100+np.arange(160)*.1
    for field in ("open","close"):raw[field]=price
    raw.high=price+1;raw.low=price-1
    cfg=ValidationRecipe(StrategySpec("single_ma",2,3),config(),(2,),(3,),.5,40,20,4)
    result=run_validation(raw,cfg)
    assert len(result.folds)==4
    assert len(result.rolling.orders)==1 and result.rolling.orders.side.iloc[0]=="buy"
    assert result.rolling.equity.shares.iloc[1:].gt(0).all()


def test_limits_no_undefined_score_fallback_and_failed_cost_scenario():
    with pytest.raises(ValueError,match="36"):
        replace(recipe(),shorts=tuple(range(2,12)),longs=tuple(range(20,31))).validate(500)
    with pytest.raises(ValueError,match="8折"):
        replace(recipe(),maximum_folds=9).validate(500)
    raw=history()
    raw[["open","close"]]=100.
    raw.high=101.;raw.low=99.
    with pytest.raises(ValueError,match="均无定义"):
        run_validation(raw,replace(recipe(),score="sharpe"))
    result=run_validation(history(),replace(recipe(),costs=config(slippage_bps=2000),stress_multipliers=(0.,1.,10.)))
    table=result.stress.set_index("multiplier")
    assert table.loc[0.,"charged_fees"]==0 and table.loc[0.,"slippage_estimate"]==0
    assert table.loc[1.,"return"]==pytest.approx(result.base.full_stats.cumulative_return)
    assert table.loc[10.,"status"]=="failed" and pd.isna(table.loc[10.,"return"])


def test_offline_report_roundtrip_complete_inputs_and_tampering_rejected():
    inputs=prepared()
    suite,report=calculate_lab(inputs,recipe())
    replay=replay_report(report)
    assert replay.audit_id==suite.audit_id
    pd.testing.assert_frame_equal(replay.rolling.equity,suite.rolling.equity)
    with ZipFile(io.BytesIO(report)) as archive:
        contents={name:archive.read(name) for name in archive.namelist()}
    assert contents["raw_history.csv"]==contents["signal_history.csv"]
    contents["raw_history.csv"]+=b"corrupt"
    damaged=io.BytesIO()
    with ZipFile(damaged,"w",compression=ZIP_DEFLATED) as archive:
        for name,value in contents.items():archive.writestr(name,value)
    with pytest.raises(ValueError,match="校验失败"):replay_report(damaged.getvalue())
    header=json.loads(contents["manifest.json"])
    header["manifest"]["versions"]["algorithm"]="future-v99"
    contents["manifest.json"]=json.dumps(header).encode()
    with ZipFile(damaged:=io.BytesIO(),"w",compression=ZIP_DEFLATED) as archive:
        for name,value in contents.items():archive.writestr(name,value)
    with pytest.raises(ValueError,match="版本"):replay_report(damaged.getvalue())


def test_unknown_retention_cannot_create_full_report():
    inputs=prepared()
    suite=run_validation(inputs.raw,recipe(),provenance=inputs.provenance)
    with pytest.raises(ValueError,match="留存许可"):
        export_validation_report(replace(inputs,retention=replace(inputs.retention,allowed=False)),suite)


def test_versioned_database_and_legacy_zip_replay_without_rewriting_prices(tmp_path):
    inputs=prepared()
    cfg=recipe()
    suite,report=calculate_lab(inputs,cfg)
    path=tmp_path/"research.sqlite3"
    identifier=save_experiment(title="验证",hypothesis="保持输入",notes="不发送的私人笔记",market="A 股",symbol="600519",
        raw_history=inputs.raw,signal_history=inputs.raw,spec=cfg.base,config=cfg.costs,train_fraction=cfg.train_fraction,result=suite.base,
        source="固定教学样本",adjustment="",received_at=datetime(2026,1,1,tzinfo=timezone.utc),path=path,input_manifest=inputs.input_manifest,
        version_metadata=LEGACY_VERSIONS,validation_metadata={"versions":VALIDATION_VERSIONS,"recipe":suite.manifest["recipe"],
            "provenance":suite.manifest["provenance"],"audit_id":suite.audit_id})
    record=get_experiment(identifier,path)
    raw_bytes=record["raw_csv_bytes"]
    assert record["version_declared"] and replay_experiment(record).audit_id==suite.base.audit_id
    assert replay_saved_validation(record).audit_id==suite.audit_id
    assert replay_report(export_experiment_zip(record)).audit_id==suite.audit_id
    assert get_experiment(identifier,path)["raw_csv_bytes"]==raw_bytes
    record["metrics"]["strategy"]["cumulative_return"]=888
    with pytest.raises(ValueError,match="旧档数值"):replay_experiment(record)
    record=get_experiment(identifier,path)
    record["metrics"]["orders"][0]["date"]="1900-01-01"
    with pytest.raises(ValueError,match="旧档成交记录"):replay_experiment(record)
    record=get_experiment(identifier,path)
    record["input_manifest"]["experiment_versions"]={"algorithm":"future-v99"}
    assert "版本" in render_report(record)
    with pytest.raises(ValueError,match="版本"):replay_experiment(record)
    record["input_manifest"]["experiment_versions"]=None
    with pytest.raises(ValueError,match="版本"):replay_experiment(record)


def test_experiment_comparison_exposes_scope_costs_and_split_differences():
    inputs=prepared()
    cfg=recipe()
    first=run_validation(inputs.raw,cfg,provenance=inputs.provenance)
    other_cfg=replace(cfg,costs=config(commission_bps=10),train_fraction=.7)
    second=run_validation(inputs.raw,other_cfg,provenance=inputs.provenance)
    a,b=session_case(inputs,cfg,first),session_case(inputs,other_cfg,second)
    compared=compare_cases((a,b))
    assert compared.directly_comparable and not compared.test_comparable
    assert "costs" in compared.differences.字段.tolist() and compared.curves is not None
    different=replace(b,identifier="other",metadata={**b.metadata,"currency":"HKD"})
    compared=compare_cases((a,different))
    assert not compared.directly_comparable and compared.curves is None and "currency" in compared.reasons


def test_unversioned_legacy_zip_keeps_original_algorithm_and_audit(tmp_path):
    from test_research_storage import history as legacy_history
    from quant_lab.research import run_experiment
    raw=legacy_history()  # Old four-column archive remains supported.
    spec=StrategySpec("dual_ma",2,3)
    costs=config()
    result=run_experiment(raw,raw,spec,costs)
    target=tmp_path/"old.sqlite3"
    identifier=save_experiment(title="旧档",hypothesis="保持旧算法",notes="私人内容",market="A 股",symbol="600519",
        raw_history=raw,signal_history=raw,spec=spec,config=costs,train_fraction=.7,result=result,
        source="旧来源",adjustment="",received_at=None,path=target)
    record=get_experiment(identifier,target)
    assert not record["version_declared"] and record["received_at"] is None
    assert replay_report(export_experiment_zip(record)).audit_id==result.audit_id


def test_report_cannot_relabel_identical_prices_with_different_provenance():
    inputs=prepared()
    suite=run_validation(inputs.raw,recipe(),provenance=inputs.provenance)
    changed=replace(inputs,provenance={**inputs.provenance,"source":"other source"})
    with pytest.raises(ValueError,match="不匹配"):export_validation_report(changed,suite)


def test_legacy_blocked_order_missing_price_remains_a_valid_archive(tmp_path):
    from quant_lab.research import run_experiment
    raw=history(80)
    raw.loc[3,"volume"]=0
    spec=StrategySpec("single_ma",2,3)
    costs=config()
    result=run_experiment(raw,raw,spec,costs)
    assert result.strategy.orders.status.eq("blocked").any() and result.strategy.orders.status.eq("filled").any()
    path=tmp_path/"blocked.sqlite3"
    identifier=save_experiment(title="旧未成交样本",hypothesis="缺省价格合法",notes="",market="A 股",symbol="600519",raw_history=raw,signal_history=raw,
        spec=spec,config=costs,train_fraction=.7,result=result,source="旧样本",adjustment="",received_at=None,path=path)
    assert replay_experiment(get_experiment(identifier,path)).audit_id==result.audit_id
