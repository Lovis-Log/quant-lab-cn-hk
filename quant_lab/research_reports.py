"""Versioned validation ZIPs and bounded offline replay, without executable code."""

from copy import deepcopy
from dataclasses import asdict,dataclass
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

import pandas as pd

from quant_lab.backtest import BacktestConfig
from quant_lab.data import HistoryBundle
from quant_lab.research_inputs import prepare_inputs
from quant_lab.research_validation import ValidationRecipe,run_validation
from quant_lab.research_versions import VALIDATION_VERSIONS
from quant_lab.source_rights import RetentionPolicy,require_retention
from quant_lab.strategy import StrategySpec
from quant_lab.data_quality import calendar_reference


@dataclass(frozen=True)
class PreparedLabInputs:
    raw: pd.DataFrame
    input_manifest: dict
    provenance: dict
    retention: RetentionPolicy


def prepare_lab_inputs(bundle: HistoryBundle):
    if bundle.market not in {"A 股","港股"}:raise ValueError("本验证引擎仅处理A/H价格模型，不能绕过美股来源关卡。")
    if bundle.update_error:raise ValueError("当前行情更新失败；已有实验保留，请重新取得有效输入。")
    paired=prepare_inputs(bundle)
    teaching=any(token in bundle.source.lower() for token in ("教学","模拟","demo","teaching","simulation"))
    if not teaching:
        if bundle.received_at is None or bundle.received_at.tzinfo is None:
            raise ValueError("真实研究输入的成功接收时点尚未记录。")
        first,last=paired.raw.date.iloc[0].date(),paired.raw.date.iloc[-1].date()
        reference=calendar_reference(bundle.market,first,last)
        if not reference.available or tuple(paired.raw.date.dt.date)!=tuple(day for day,_ in reference.sessions):
            raise ValueError("实际区间内交易日存在缺失或日历无法核验，不能跳过成交日进行新验证。")
    manifest=deepcopy(paired.manifest)
    manifest["displayed_signal"]=manifest["signal"]
    manifest["signal"]=deepcopy(manifest["raw"])
    provenance={"market":bundle.market,"symbol":bundle.symbol,"currency":bundle.currency,
        "source":bundle.source,"received_at":bundle.received_at.isoformat() if bundle.received_at else None,
        "company_name":bundle.company_name,"input_manifest":manifest,
        "quality":bundle.quality.to_dict() if bundle.quality else {"status":"not-recorded"}}
    return PreparedLabInputs(paired.raw,manifest,provenance,RetentionPolicy(**manifest["raw"]["retention"]))


def recipe_from_dict(value):
    value=dict(value)
    value["base"]=StrategySpec(**value["base"])
    value["costs"]=BacktestConfig(**value["costs"])
    for field in ("shorts","longs","stress_multipliers"):value[field]=tuple(value[field])
    return ValidationRecipe(**value)


def suite_tables(suite):
    return {"base_equity.csv":suite.base.strategy.equity,"base_orders.csv":suite.base.strategy.orders,
        "benchmark_equity.csv":suite.base.benchmark.equity,"scan.csv":suite.scan,"folds.csv":suite.folds,
        "rolling_equity.csv":suite.rolling.equity,"rolling_orders.csv":suite.rolling.orders,
        "stress.csv":suite.stress,"costs.csv":suite.diagnostics.costs,"blocked.csv":suite.diagnostics.blocked,
        "exposure.csv":suite.diagnostics.exposure}


def _table_files(raw,suite):
    files={name:frame.to_csv(index=False).encode("utf-8") for name,frame in suite_tables(suite).items()}
    files["raw_history.csv"]=raw.to_csv(index=False).encode("utf-8")
    files["signal_history.csv"]=files["raw_history.csv"]
    return files


def render_validation_report(suite):
    info=suite.manifest
    provenance=info["provenance"]
    stats=suite.base.full_stats
    diagnostic=suite.diagnostics.summary
    return "\n".join(["# Quant Lab 研究验证报告","",
        f"- 实验：{suite.audit_id}",f"- 标的：{provenance.get('market','未记录')} {provenance.get('symbol','未记录')}",
        f"- 来源：{provenance.get('source','未记录')}；接收：{provenance.get('received_at') or '未记录'}",
        f"- 算法与规则：{json.dumps(info['versions'],ensure_ascii=False)}",
        "- 信号价格：不复权；AH价格/成本模型，不含股息及公司行动重建，不是总回报。",
        "- 公司行动状态：未核验且未建模；不是已确认没有事件。","",
        "## 全样本固定策略结果","",f"- 累计价格策略收益：{stats.cumulative_return:.6%}",
        f"- 最大回撤：{stats.max_drawdown:.6%}",f"- 实收费用：{diagnostic['charged_fees']:.6f}",
        f"- 成交价差滑点估计（另列，不重复扣费）：{diagnostic['slippage_estimate']:.6f}",
        f"- 累计双边成交金额/平均日权益：{diagnostic['notional_turnover']}",
        f"- 平均仓位暴露：{diagnostic['average_exposure']:.6%}","",
        "## 验证定义","",
        "参数扫描只用固定训练前缀；平局按短、长周期升序。滚动每折只用之前的训练窗口选参，已结束观测可进入后折训练。",
        "滚动样本外持仓与现金跨折连续，不免费平仓或重置。样本外数据不用于该折参数选择。",
        "成本压力使用固定基础策略，非重新优化；失败情景明确记录，不填收益0。",
        f"覆盖：{json.dumps(info['rolling_coverage'],ensure_ascii=False)}","",
        "## 假设和参数","","```json",json.dumps(info['recipe'],ensure_ascii=False,indent=2),"```","",
        "## 文件与离线复算","",
        "本ZIP含完整原始价、相同不复权信号价、事件未知状态、来源/质量/接收信息、规则/算法版本、参数及输出校验。",
        "在对应源码环境运行：python -m quant_lab.research_reports report.zip。复算只用本地数据，不联网，不执行文件中的代码。",
        "私有笔记、AI会话和凭据不在此自动报告中。报告是研究记录，不能消除原始数据修订、幸存者偏差或多次查看测试集带来的过拟合。",""])


def export_validation_report(inputs:PreparedLabInputs,suite):
    require_retention(inputs.retention)
    for field in ("raw","signal"):
        require_retention(RetentionPolicy(**inputs.input_manifest[field]["retention"]))
    raw=inputs.raw
    if hashlib.sha256(raw.to_csv(index=False).encode()).hexdigest()!=suite.manifest["raw_sha256"] or inputs.provenance!=suite.manifest["provenance"]:
        raise ValueError("报告输入与已计算实验不匹配。")
    files=_table_files(raw,suite)
    files["report.md"]=render_validation_report(suite).encode("utf-8")
    header={"format":"quantlab-validation-report-v1","audit_id":suite.audit_id,"manifest":suite.manifest,
        "diagnostics":suite.diagnostics.summary,"rolling_diagnostics":suite.rolling_diagnostics.summary,
        "sha256":{name:hashlib.sha256(value).hexdigest() for name,value in files.items()}}
    output=io.BytesIO()
    with ZipFile(output,"w",compression=ZIP_DEFLATED) as archive:
        for name,value in files.items():archive.writestr(name,value)
        archive.writestr("manifest.json",json.dumps(header,ensure_ascii=False,sort_keys=True,indent=2,default=str))
    return output.getvalue()


def replay_validation_report(payload:bytes):
    if len(payload)>50_000_000:raise ValueError("验证报告超过50MB上限。")
    with ZipFile(io.BytesIO(payload)) as archive:
        entries=archive.infolist()
        if len(entries)>20 or len({entry.filename for entry in entries})!=len(entries) or sum(e.file_size for e in entries)>50_000_000:
            raise ValueError("报告文件数、重复成员或解压大小超限。")
        header=json.loads(archive.read("manifest.json"))
        expected=set(header["sha256"])|{"manifest.json"}
        fixed={"manifest.json","report.md","raw_history.csv","signal_history.csv","base_equity.csv","base_orders.csv","benchmark_equity.csv",
               "scan.csv","folds.csv","rolling_equity.csv","rolling_orders.csv","stress.csv","costs.csv","blocked.csv","exposure.csv"}
        if expected!=fixed or set(archive.namelist())!=fixed:raise ValueError("报告成员与固定格式不匹配。")
        if header.get("format")!="quantlab-validation-report-v1" or header["manifest"]["versions"]!=VALIDATION_VERSIONS:
            raise ValueError("验证算法/规则版本无复算实现，不能用当前代码重新解释。")
        files={name:archive.read(name) for name in header["sha256"]}
        if any(hashlib.sha256(value).hexdigest()!=header["sha256"][name] for name,value in files.items()):
            raise ValueError("验证报告文件校验失败。")
    if files["raw_history.csv"]!=files["signal_history.csv"]:raise ValueError("验证报告信号口径不一致。")
    raw=pd.read_csv(io.BytesIO(files["raw_history.csv"]),parse_dates=["date"],float_precision="round_trip")
    recipe=recipe_from_dict(header["manifest"]["recipe"])
    result=run_validation(raw,recipe,provenance=header["manifest"]["provenance"])
    regenerated=_table_files(raw,result)
    if result.audit_id!=header["audit_id"] or any(value!=files[name] for name,value in regenerated.items()):
        raise ValueError("验证报告输入/输出与离线复算不一致。")
    if result.diagnostics.summary!=header["diagnostics"] or result.rolling_diagnostics.summary!=header["rolling_diagnostics"]:
        raise ValueError("诊断与本地复算不一致。")
    if render_validation_report(result).encode("utf-8")!=files["report.md"]:
        raise ValueError("报告文字与本地复算结果不一致。")
    return result


def calculate_lab(inputs,recipe):
    result=run_validation(inputs.raw,recipe,provenance=inputs.provenance)
    report=export_validation_report(inputs,result) if inputs.retention.allowed else None
    return result,report


def replay_saved_validation(record):
    metadata=record.get("input_manifest",{}).get("validation")
    if not metadata or metadata.get("versions")!=VALIDATION_VERSIONS:
        raise ValueError("此存档没有受支持的研究验证配方；旧基础实验仍可按旧算法复算。")
    result=run_validation(record["raw_history"],recipe_from_dict(metadata["recipe"]),provenance=metadata["provenance"])
    if result.audit_id!=metadata["audit_id"]:raise ValueError("存档验证配方与本地复算不一致。")
    return result


def replay_validation_archive(identifier):
    """Pure offline worker entry; read one selected archive and never rewrite it."""
    from quant_lab.storage import get_experiment,replay_experiment
    record=get_experiment(int(identifier))
    replay_experiment(record)
    return replay_saved_validation(record)


def replay_legacy_zip(payload):
    from quant_lab.storage import replay_experiment
    with ZipFile(io.BytesIO(payload)) as archive:
        members=archive.infolist()
        if len(members)!=4 or set(archive.namelist())!={"report.md","raw_history.csv","signal_history.csv","assumptions.json"} or sum(m.file_size for m in members)>50_000_000:
            raise ValueError("旧实验ZIP成员或大小无效。")
        assumptions=json.loads(archive.read("assumptions.json"))
        if assumptions.get("versions"):
            from quant_lab.research_versions import legacy_versions
            legacy_versions({"experiment_versions":assumptions["versions"]})
        record=dict(assumptions)
        for field in ("raw","signal"):
            raw=archive.read(field+"_history.csv")
            if hashlib.sha256(raw).hexdigest()!=assumptions[field+"_sha256"]:
                raise ValueError("旧实验行情校验失败。")
            record[field+"_history"]=pd.read_csv(io.BytesIO(raw),parse_dates=["date"],float_precision="round_trip")
    result=replay_experiment(record)
    return replay_saved_validation(record) if record.get("input_manifest",{}).get("validation") else result


def replay_report(payload):
    if len(payload)>50_000_000:raise ValueError("报告超过50MB上限。")
    with ZipFile(io.BytesIO(payload)) as archive:
        validation="manifest.json" in archive.namelist()
    return replay_validation_report(payload) if validation else replay_legacy_zip(payload)


if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:raise SystemExit("Usage: python -m quant_lab.research_reports report.zip")
    result=replay_report(Path(sys.argv[1]).read_bytes())
    print("Offline replay matched: "+result.audit_id)
