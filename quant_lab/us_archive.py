"""Portable US input snapshots/replay, versioned independently of legacy SQLite."""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import io
import json

import pandas as pd

from quant_lab.source_rights import RetentionPolicy, require_retention
from quant_lab.us_market import USInstrument, SettlementCalendar, US_RULES_VERSION
from quant_lab.us_data import USDataset, USAction, USActionBook, validate_us_prices
from quant_lab.us_backtest import US_ALGORITHM_VERSION, USExecutionConfig, run_us_portfolio


def export_us_run(datasets, targets, settlement, config, result):
    """Export only a result matching its full verified inputs, never raw credentials."""
    for data in datasets.values():
        require_retention(data.retention)
    replay=run_us_portfolio(datasets,targets,settlement,config,
        teaching=result.manifest["teaching"],include_dividends=result.manifest["include_dividends"])
    if replay.audit_id!=result.audit_id:
        raise ValueError("当前输入与导出的美股实验不匹配，请重新计算。")
    body={"format":"quantlab-us-run-v1","algorithm":US_ALGORITHM_VERSION,"rules":US_RULES_VERSION,
        "audit_id":result.audit_id,"manifest":result.manifest,
        "raw_csv":{s:validate_us_prices(data.raw).to_csv(index=False) for s,data in datasets.items()},
        "targets_csv":targets.to_csv(),"equity_csv":result.equity.to_csv(index=False),
        "orders_csv":result.orders.to_csv(index=False),"cash_ledger_csv":result.cash_ledger.to_csv(index=False),
        "positions_csv":result.positions.to_csv(index=False)}
    encoded=json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return json.dumps({"sha256":hashlib.sha256(encoded.encode()).hexdigest(),"body":body},ensure_ascii=False).encode("utf-8")


def replay_us_run(payload: bytes):
    if len(payload)>50_000_000:
        raise ValueError("美股实验快照超出50MB上限。")
    envelope=json.loads(payload)
    body=envelope["body"]
    encoded=json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    if hashlib.sha256(encoded.encode()).hexdigest()!=envelope["sha256"]:
        raise ValueError("美股实验快照内容校验失败。")
    if body.get("format")!="quantlab-us-run-v1" or body.get("algorithm")!=US_ALGORITHM_VERSION or body.get("rules")!=US_RULES_VERSION:
        raise ValueError("此美股实验算法/规则版本尚无复算实现；不能用新版本重新解释。")
    manifest=body["manifest"]
    datasets={}
    for symbol,info in manifest["inputs"].items():
        identity=dict(info["identity"])
        identity["source_codes"]=tuple(tuple(pair) for pair in identity["source_codes"])
        events=[]
        for values in info["actions"]["events"]:
            values=dict(values)
            values["effective_date"]=date.fromisoformat(values["effective_date"])
            values["known_at"]=datetime.fromisoformat(values["known_at"])
            values["pay_at"]=datetime.fromisoformat(values["pay_at"]) if values["pay_at"] else None
            values["payment_date"]=date.fromisoformat(values["payment_date"]) if values.get("payment_date") else None
            values["amount_per_share"]=Decimal(values["amount_per_share"])
            events.append(USAction(**values))
        book=info["actions"]
        raw=pd.read_csv(io.StringIO(body["raw_csv"][symbol]),parse_dates=["date"],float_precision="round_trip")
        datasets[symbol]=USDataset(USInstrument(**identity),raw,info["source"],datetime.fromisoformat(info["received_at"]),
            USActionBook(symbol,date.fromisoformat(book["start"]),date.fromisoformat(book["end"]),book["known"],book["evidence"],tuple(events)),
            info["raw_price_evidence"],info["price_basis"],RetentionPolicy(**info["retention"]),manifest["teaching"],info["input_version"])
    cal=manifest["settlement_calendar"]
    settlement=SettlementCalendar(date.fromisoformat(cal["start"]),date.fromisoformat(cal["end"]),
        tuple(date.fromisoformat(day) for day in cal["dates"]),cal["version"],cal["evidence"],True)
    targets=pd.read_csv(io.StringIO(body["targets_csv"]),index_col=0,parse_dates=[0],float_precision="round_trip")
    config=USExecutionConfig(**manifest["config"])
    result=run_us_portfolio(datasets,targets,settlement,config,teaching=manifest["teaching"],
                            include_dividends=manifest["include_dividends"])
    if result.audit_id!=body["audit_id"] or json.dumps(result.manifest,sort_keys=True)!=json.dumps(manifest,sort_keys=True):
        raise ValueError("美股输入或版本指纹与原实验不一致。")
    for field in ("equity","orders","cash_ledger","positions"):
        if getattr(result,field).to_csv(index=False)!=body[field+"_csv"]:
            raise ValueError("美股复算结果与原记录不一致。")
    return result
