"""Recompute numeric facts and expose 2-6 experiment comparability differences."""

from dataclasses import asdict,dataclass
import json

import pandas as pd

from quant_lab.research_versions import LEGACY_VERSIONS
from quant_lab.storage import get_experiment,replay_experiment


@dataclass(frozen=True)
class ExperimentCase:
    identifier: str
    label: str
    metadata: dict
    stats: dict
    test_return: float
    equity: pd.DataFrame


@dataclass(frozen=True)
class ExperimentComparison:
    summary: pd.DataFrame
    differences: pd.DataFrame
    directly_comparable: bool
    test_comparable: bool
    reasons: tuple[str,...]
    curves: pd.DataFrame | None


def session_case(inputs,recipe,suite):
    p=inputs.provenance
    return ExperimentCase("session:"+suite.audit_id,
        f"{p['symbol']} {recipe.base.short_window}/{recipe.base.long_window} · {suite.audit_id[-6:]}",
        {"market":p["market"],"symbol":p["symbol"],"currency":p["currency"],"source":p["source"],"received_at":p["received_at"],
         "start":str(inputs.raw.date.iloc[0].date()),"end":str(inputs.raw.date.iloc[-1].date()),
         "raw_sha256":suite.manifest["raw_sha256"],"signal_sha256":suite.manifest["raw_sha256"],
         "strategy":asdict(recipe.base),"costs":asdict(recipe.costs),"train_fraction":recipe.train_fraction,
         "test_start":str(suite.base.split_date),"versions":dict(LEGACY_VERSIONS),"version_declared":True,
         "validation_versions":suite.manifest["versions"]},asdict(suite.base.full_stats),suite.base.test_stats.cumulative_return,
        suite.base.strategy.equity[["date","equity"]].copy())


def load_saved_cases(identifiers):
    if not 2<=len(identifiers)<=6 or len(set(identifiers))!=len(identifiers):
        raise ValueError("请选择2至6个不重复的存档实验。")
    cases=[]
    for identifier in identifiers:
        record=get_experiment(int(identifier))
        result=replay_experiment(record)
        currency={"A 股":"CNY","港股":"HKD"}.get(record["market"],"未知")
        metadata={"market":record["market"],"symbol":record["symbol"],"currency":currency,"source":record["source"],
            "received_at":record["received_at"],"start":record["start_date"],"end":record["end_date"],
            "raw_sha256":record["raw_sha256"],"signal_sha256":record["signal_sha256"],"strategy":record["strategy"],
            "costs":record["config"],"train_fraction":record["train_fraction"],"test_start":str(result.split_date),
            "versions":record["versions"],"version_declared":record["version_declared"],
            "validation_versions":record["input_manifest"].get("validation",{}).get("versions")}
        cases.append(ExperimentCase("archive:"+str(identifier),f"#{identifier} {record['title']}",metadata,
            asdict(result.full_stats),result.test_stats.cumulative_return,result.strategy.equity[["date","equity"]].copy()))
    return tuple(cases)


def compare_cases(cases):
    if not 2<=len(cases)<=6 or len({c.identifier for c in cases})!=len(cases):
        raise ValueError("对比需要2至6个唯一实验。")
    first=cases[0].metadata
    scope=("market","symbol","currency","start","end","raw_sha256","signal_sha256","versions")
    reasons=tuple(field for field in scope if any(case.metadata.get(field)!=first.get(field) for case in cases[1:]))
    if any(case.metadata["costs"]["initial_cash"]!=first["costs"]["initial_cash"] for case in cases[1:]):
        reasons+=("initial_cash",)
    test_comparable=not reasons and all(case.metadata.get("test_start")==first.get("test_start") for case in cases)
    rows=[]
    for case in cases:
        teaching=any(token in str(case.metadata.get("source","")).lower() for token in ("教学","模拟","demo","teaching","simulation"))
        rows.append({"实验":case.label,"输入标记":"教学/模拟" if teaching else "历史来源（非实时）","市场":case.metadata["market"],"代码":case.metadata["symbol"],"币种":case.metadata["currency"],
            "全样本收益":case.stats["cumulative_return"],"最大回撤":case.stats["max_drawdown"],"夏普":case.stats["sharpe"],
            "样本外收益":case.test_return,"比较状态":"同数据模型；参数/费用差异见下表" if not reasons else "数据/区间/版本不同，不可直接比"})
    differences=[]
    for field in sorted(set().union(*(case.metadata.keys() for case in cases))):
        values=[json.dumps(case.metadata.get(field),ensure_ascii=False,sort_keys=True,default=str) for case in cases]
        if len(set(values))>1:
            differences.append({"字段":field,**{case.label:value for case,value in zip(cases,values)}})
    curves=None
    if not reasons:
        curves=pd.concat([case.equity.set_index("date").equity.div(case.equity.equity.iloc[0]).rename(case.label) for case in cases],axis=1)
    return ExperimentComparison(pd.DataFrame(rows),pd.DataFrame(differences),not reasons,test_comparable,reasons,curves)


def compare_saved(identifiers):
    """Worker entry lives in a pure service, never in a Streamlit module."""
    return compare_cases(load_saved_cases(identifiers))
