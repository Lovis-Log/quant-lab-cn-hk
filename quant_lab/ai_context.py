"""Only current program facts, never private notes or full price tables."""

from dataclasses import asdict
import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from quant_lab.metrics import summarize_prices, performance_stats
from quant_lab.market_data import display_security
from quant_lab.deepseek import safe_context


def _beijing(value):
    if not value:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(sep=" ")


def bundle_context(page, bundle) -> dict:
    result = {"page": page}
    if bundle is None or bundle.frame.empty:
        result["data_status"] = "没有当前股票的有效历史行情；无法分析缺失指标。"
        return result
    frame = bundle.frame
    result.update({"market": bundle.market, "symbol": bundle.symbol, "company_name": bundle.company_name,
                   "security": display_security(bundle.market, bundle.symbol, bundle.company_name),
                   "data_period": [str(frame.date.iloc[0].date()), str(frame.date.iloc[-1].date())],
                   "source": bundle.source, "adjustment": bundle.adjustment_label,
                   "data_fingerprint": hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()[:16],
                   "received_at": _beijing(bundle.received_at),
                   "data_status": "历史日线／最近收盘参考；确切延迟未知" +
                                    ("；最近更新失败，数据可能过期" if bundle.update_error else ""),
                   "price_metrics": asdict(summarize_prices(frame))})
    if len(frame) >= 3:
        daily = frame.close.pct_change().dropna()
        risk = performance_stats(frame.close)
        result["price_metrics"].update({"sample_variance": float(daily.var(ddof=1)),
            "sample_std": float(daily.std(ddof=1)), "annualized_volatility": risk.annualized_volatility,
            "max_drawdown": risk.max_drawdown, "periods_per_year": 252})
    return result


def experiment_context(record: dict) -> dict:
    return safe_context({
        "market": record["market"], "symbol": record["symbol"],
        "company_name": record.get("company_name", ""),
        "security": display_security(record["market"], record["symbol"], record.get("company_name")),
        "data_period": [record["start_date"], record["end_date"]],
        "source": record["source"], "adjustment": record["adjustment"],
        "received_at": _beijing(record["received_at"]), "data_status": "存档历史快照；确切延迟未知",
        "experiment_id": record["id"], "audit_id": record["audit_id"],
        "strategy": record["strategy"], "costs": record["config"],
        "performance": {k: record["metrics"][k] for k in ("strategy", "benchmark", "train", "test")},
    })


def context_scope(context: dict) -> str:
    fields = {k: context.get(k) for k in ("page", "market", "symbol", "data_period", "data_fingerprint", "experiment_id", "audit_id", "lesson", "answer_mode", "learning_context", "statistics", "knowledge")}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, default=str).encode()).hexdigest()[:16]
