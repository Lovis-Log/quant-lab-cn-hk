"""Bounded training scans, continuous rolling OOS and fixed-rule cost stress."""

from dataclasses import asdict,dataclass,replace
import hashlib
import json
import math

import numpy as np
import pandas as pd

from quant_lab.backtest import BacktestConfig,run_backtest
from quant_lab.metrics import performance_stats
from quant_lab.processing import clean_stock_history
from quant_lab.research import run_experiment
from quant_lab.strategy import StrategySpec,build_signals
from quant_lab.research_diagnostics import backtest_diagnostics
from quant_lab.research_versions import VALIDATION_VERSIONS


@dataclass(frozen=True)
class ValidationRecipe:
    base: StrategySpec
    costs: BacktestConfig
    shorts: tuple[int,...] = (5,10)
    longs: tuple[int,...] = (20,30)
    train_fraction: float = .7
    rolling_train: int = 126
    rolling_test: int = 42
    maximum_folds: int = 4
    score: str = "return"
    stress_multipliers: tuple[float,...] = (0.,1.,2.,3.)

    def candidates(self):
        for values in (self.shorts,self.longs):
            if not values or len(set(values))!=len(values) or any(type(v) is not int or not 2<=v<=250 for v in values):
                raise ValueError("候选周期须为2至250的唯一整数。")
        candidates=tuple(StrategySpec(self.base.kind,s,l) for s in sorted(self.shorts) for l in sorted(self.longs) if s<l)
        if not 1<=len(candidates)<=36:
            raise ValueError("有效候选必须为1至36组，且短周期小于长周期。")
        return candidates

    def validate(self,n):
        candidates=self.candidates()
        if self.score not in {"return","sharpe"} or not .5<=self.train_fraction<=.85:
            raise ValueError("训练目标或样本内比例无效。")
        if any(type(v) is not int for v in (self.rolling_train,self.rolling_test,self.maximum_folds)):
            raise ValueError("滚动窗口和折数须为整数。")
        minimum=max(30,max(spec.long_window for spec in candidates)+5,self.base.long_window+5)
        if self.rolling_train<minimum or self.rolling_test<5 or not 1<=self.maximum_folds<=8:
            raise ValueError("滚动训练须覆盖均线与预热，测试至少5条，最多8折。")
        if n>10000 or int(n*self.train_fraction)<minimum or n<self.rolling_train+5:
            raise ValueError("历史不足以支持当前训练/均线，或超过10000行计算上限。")
        if not 1<=len(self.stress_multipliers)<=6 or 1. not in self.stress_multipliers or len(set(self.stress_multipliers))!=len(self.stress_multipliers):
            raise ValueError("成本压力须含1倍基准，最多6个唯一情景。")
        if any(isinstance(v,bool) or not math.isfinite(v) or not 0<=v<=10 for v in self.stress_multipliers):
            raise ValueError("成本倍数须为0至10的有限值。")
        budget=n*len(candidates)+self.maximum_folds*self.rolling_train*len(candidates)+n*(len(self.stress_multipliers)+3)
        if budget>2_000_000:
            raise ValueError("本次预计计算量超过200万行次，请缩小网格或窗口。")
        return candidates,budget


@dataclass(frozen=True)
class ValidationSuite:
    base: object
    diagnostics: object
    scan: pd.DataFrame
    folds: pd.DataFrame
    rolling: object
    rolling_diagnostics: object
    stress: pd.DataFrame
    manifest: dict
    audit_id: str


def _rank_grid(raw,candidates,config,score):
    rows=[]
    for spec in candidates:
        signals=build_signals(raw,spec).signal
        result=run_backtest(raw,signals,config)
        stats=performance_stats(result.equity.equity)
        metric=stats.cumulative_return if score=="return" else stats.sharpe
        rows.append({"short":spec.short_window,"long":spec.long_window,"training_return":stats.cumulative_return,
            "training_sharpe":stats.sharpe,"training_drawdown":stats.max_drawdown,
            "score":metric,"filled_orders":int(result.orders.status.eq("filled").sum()) if not result.orders.empty else 0})
    table=pd.DataFrame(rows).sort_values(["score","short","long"],ascending=[False,True,True],na_position="last").reset_index(drop=True)
    if table.score.notna().sum()==0:
        raise ValueError("所有候选训练目标均无定义；没有静默更换选参目标。")
    return table


def run_validation(raw,recipe: ValidationRecipe,*,provenance=None):
    if not isinstance(raw,pd.DataFrame) or raw.empty:raise ValueError("研究验证需要非空原始行情。")
    data=clean_stock_history(raw,raw.date.iloc[0].date(),raw.date.iloc[-1].date())
    candidates,budget=recipe.validate(len(data))
    if recipe.costs.initial_cash/(float(data.open.min())*recipe.costs.lot_size)>1_000_000:
        raise ValueError("初始最大交易单位超过100万，请调整研究资金或单位以控制计算量。")
    if (data.close.pct_change(fill_method=None).abs()>=.4).any():
        raise ValueError("存在需核对的大幅价格跳变；本AH价格研究不重建公司行动，请核验或缩短区间。")
    split=int(len(data)*recipe.train_fraction)
    scan=_rank_grid(data.iloc[:split].reset_index(drop=True),candidates,recipe.costs,recipe.score)
    starts=[i for i in range(recipe.rolling_train,len(data),recipe.rolling_test) if len(data)-i>=5][-recipe.maximum_folds:]
    first=starts[0]
    last=min(starts[-1]+recipe.rolling_test,len(data))
    selected=pd.Series(0,index=range(last-first+1),dtype=int)
    fold_rows=[]
    # One execution run across folds: no free liquidation/reset at boundaries.
    for fold,start in enumerate(starts):
        end=min(start+recipe.rolling_test,len(data))
        train_start=start-recipe.rolling_train
        training=data.iloc[train_start:start].reset_index(drop=True)
        rank=_rank_grid(training,candidates,recipe.costs,recipe.score)
        best=rank.iloc[0]
        spec=StrategySpec(recipe.base.kind,int(best.short),int(best.long))
        prefix=build_signals(data.iloc[train_start:end].reset_index(drop=True),spec)
        for trade_day in range(start,end):
            selected.iloc[trade_day-first]=int(prefix.signal.iloc[trade_day-1-train_start])
        fold_rows.append({"fold":fold+1,"train_start":data.date.iloc[train_start],"train_end":data.date.iloc[start-1],
            "test_start":data.date.iloc[start],"test_end":data.date.iloc[end-1],"short":spec.short_window,"long":spec.long_window,"training_score":float(best.score)})
    test=data.iloc[first-1:last].reset_index(drop=True)
    rolling=run_backtest(test,selected,recipe.costs)
    for row,start in zip(fold_rows,starts):
        end=min(start+recipe.rolling_test,len(data))
        stats=performance_stats(rolling.equity.equity.iloc[start-first:end-first+1])
        row["test_return"]=stats.cumulative_return
    stress_rows=[]
    for multiplier in recipe.stress_multipliers:
        try:
            costs=replace(recipe.costs,**{field:getattr(recipe.costs,field)*multiplier for field in
                ("commission_bps","min_commission","buy_tax_bps","sell_tax_bps","slippage_bps")})
            run=run_backtest(data,build_signals(data,recipe.base).signal,costs)
            stats=performance_stats(run.equity.equity)
            diagnostic=backtest_diagnostics(data,run,costs)
            stress_rows.append({"multiplier":multiplier,"status":"success","return":stats.cumulative_return,
                "max_drawdown":stats.max_drawdown,"charged_fees":diagnostic.summary["charged_fees"],
                "slippage_estimate":diagnostic.summary["slippage_estimate"],"error":""})
        except ValueError as error:
            stress_rows.append({"multiplier":multiplier,"status":"failed","return":None,"max_drawdown":None,
                "charged_fees":None,"slippage_estimate":None,"error":str(error)})
    base=run_experiment(data,data,recipe.base,recipe.costs,recipe.train_fraction)
    manifest={"versions":dict(VALIDATION_VERSIONS),"recipe":asdict(recipe),"signal_basis":"unadjusted",
        "raw_sha256":hashlib.sha256(data.to_csv(index=False).encode()).hexdigest(),"provenance":provenance or {},
        "planned_row_evaluations":budget,"candidates":len(candidates),"rejected_pairs":len(recipe.shorts)*len(recipe.longs)-len(candidates),
        "rolling_coverage":{"first_test":str(data.date.iloc[first].date()),"last_test":str(data.date.iloc[last-1].date()),
            "test_rows":last-first,"tail_rows_not_tested":len(data)-last,"fold_count":len(starts)},
        "company_actions":{"status":"unverified-not-modelled","scope":"AH original-price/cost research; not total return"}}
    digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()
    return ValidationSuite(base,backtest_diagnostics(data,base.strategy,recipe.costs),scan,pd.DataFrame(fold_rows),rolling,
        backtest_diagnostics(test,rolling,recipe.costs),pd.DataFrame(stress_rows),manifest,"validation-v1:"+digest[:24])
