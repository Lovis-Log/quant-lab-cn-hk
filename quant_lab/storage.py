"""SQLite research archive and watchlists in the user's writable profile."""

from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import zlib
from copy import deepcopy
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Iterator

import pandas as pd

from quant_lab.backtest import BacktestConfig
from quant_lab.market_data import normalize_symbol
from quant_lab.paths import database_path as active_database_path
from quant_lab.research import ExperimentResult
from quant_lab.strategy import StrategySpec
from quant_lab.migrations import migrate
from quant_lab.security import redact
from quant_lab.market_data import display_security


def database_path() -> Path:
    return active_database_path()


@contextmanager
def _connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=15)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        migrate(connection, target)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_watchlist(path: Path | None = None) -> list[tuple[str, str]]:
    if not (path or database_path()).exists():
        return []
    with _connect(path) as db:
        return [(row["market"], row["symbol"]) for row in db.execute(
            "SELECT market, symbol FROM watchlist ORDER BY market, symbol"
        )]


def add_watchlist(market: str, symbol: str, path: Path | None = None, *, company_name: str = "") -> str:
    from quant_lab.security_identity import normalize_security
    symbol = normalize_security(market, symbol)
    with _connect(path) as db:
        count = db.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        present = db.execute("SELECT 1 FROM watchlist WHERE market=? AND symbol=?",
                             (market, symbol)).fetchone()
        if count >= 10 and not present:
            raise ValueError("自选股最多保存 10 只，以控制免费数据接口请求量。")
        db.execute("INSERT OR IGNORE INTO watchlist (market,symbol,added_at,company_name) VALUES (?, ?, ?, ?)",
                   (market, symbol, datetime.now(timezone.utc).isoformat(), redact(company_name)))
    return symbol


def remove_watchlist(market: str, symbol: str, path: Path | None = None) -> None:
    with _connect(path) as db:
        db.execute("DELETE FROM watchlist WHERE market=? AND symbol=?", (market, symbol))


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def save_experiment(
    *, title: str, hypothesis: str, notes: str, market: str, symbol: str,
    raw_history: pd.DataFrame, signal_history: pd.DataFrame,
    spec: StrategySpec, config: BacktestConfig, train_fraction: float,
    result: ExperimentResult, source: str, adjustment: str,
    received_at: datetime | None, path: Path | None = None,
    company_name: str = "",
    input_manifest: dict | None = None,
    version_metadata: dict | None = None,
    validation_metadata: dict | None = None,
) -> int:
    if not title.strip() or not hypothesis.strip():
        raise ValueError("研究标题和假设不能为空。")
    symbol = normalize_symbol(market, symbol)
    if config.market != market:
        raise ValueError("回测市场与研究市场不一致。")
    if raw_history.empty or signal_history.empty:
        raise ValueError("实验不能保存空行情。")
    raw_bytes, signal_bytes = _csv_bytes(raw_history), _csv_bytes(signal_history)
    stored_manifest=deepcopy(input_manifest or {})
    if version_metadata is not None:
        from quant_lab.research_versions import legacy_versions
        legacy_versions({"experiment_versions":version_metadata})
        stored_manifest["experiment_versions"]=dict(version_metadata)
    if validation_metadata is not None:
        from quant_lab.research_versions import VALIDATION_VERSIONS
        if validation_metadata.get("versions")!=VALIDATION_VERSIONS:
            raise ValueError("研究验证版本无法保存为当前配方。")
        stored_manifest["validation"]=deepcopy(validation_metadata)
    if input_manifest is not None:
        if (input_manifest.get("format"), input_manifest.get("market"), input_manifest.get("symbol")) != (1, market, symbol):
            raise ValueError("研究输入清单版本或证券身份与存档不匹配。")
        for field, payload in (("raw", raw_bytes), ("signal", signal_bytes)):
            info = input_manifest.get(field, {})
            if info.get("sha256") != hashlib.sha256(payload).hexdigest():
                raise ValueError("研究输入清单与保存行情不一致。")
            rights = info.get("retention", {})
            if not rights.get("allowed") or not rights.get("evidence"):
                raise ValueError("来源本地留存许可未核实，不能新增行情快照。")
            if info.get("adjustment") != ("" if field == "raw" else adjustment):
                raise ValueError("研究输入清单的价格口径与存档不匹配。")
    stats = {
        "strategy": asdict(result.full_stats),
        "benchmark": asdict(result.benchmark_stats),
        "train": asdict(result.train_stats),
        "test": asdict(result.test_stats),
        "split_date": result.split_date.isoformat(),
        "orders": result.strategy.orders.to_dict(orient="records"),
    }
    with _connect(path) as db:
        cursor = db.execute("""
            INSERT INTO experiments (
                title, hypothesis, notes, market, symbol, start_date, end_date,
                strategy_json, config_json, train_fraction, metrics_json,
                source, adjustment, received_at, created_at, audit_id,
                raw_sha256, signal_sha256, raw_csv, signal_csv, company_name, input_manifest_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            redact(title.strip()), redact(hypothesis.strip()), redact(notes.strip()), market, symbol,
            str(raw_history["date"].iloc[0].date()), str(raw_history["date"].iloc[-1].date()),
            json.dumps(asdict(spec), ensure_ascii=False),
            json.dumps(asdict(config), ensure_ascii=False), train_fraction,
            json.dumps(stats, ensure_ascii=False, default=str), redact(source), adjustment,
            received_at.isoformat() if received_at else None,
            datetime.now(timezone.utc).isoformat(), result.audit_id,
            hashlib.sha256(raw_bytes).hexdigest(), hashlib.sha256(signal_bytes).hexdigest(),
            zlib.compress(raw_bytes), zlib.compress(signal_bytes),
            redact(company_name),
            json.dumps(stored_manifest, ensure_ascii=False),
        ))
        return int(cursor.lastrowid)


def list_experiments(path: Path | None = None, *, include_deleted: bool = True) -> list[dict]:
    if not (path or database_path()).exists():
        return []
    with _connect(path) as db:
        rows = db.execute("""
            SELECT id, title, market, symbol, start_date, end_date, created_at,
                   audit_id, source, company_name FROM experiments
        """ + ("" if include_deleted else " WHERE deleted_at IS NULL") + " ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def get_experiment(experiment_id: int, path: Path | None = None) -> dict:
    with _connect(path) as db:
        row = db.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
    if row is None:
        raise KeyError(f"找不到实验 {experiment_id}")
    record = dict(row)
    record["input_manifest"] = json.loads(record.pop("input_manifest_json", "{}"))
    from quant_lab.research_versions import LEGACY_VERSIONS
    record["versions"]=record["input_manifest"].get("experiment_versions",dict(LEGACY_VERSIONS))
    record["version_declared"]="experiment_versions" in record["input_manifest"]
    for field in ("raw", "signal"):
        csv_bytes = zlib.decompress(record.pop(f"{field}_csv"))
        if hashlib.sha256(csv_bytes).hexdigest() != record[f"{field}_sha256"]:
            raise ValueError("已保存的行情快照校验失败。")
        record[f"{field}_csv_bytes"] = csv_bytes
        record[f"{field}_history"] = pd.read_csv(
            io.BytesIO(csv_bytes), parse_dates=["date"], float_precision="round_trip"
        )
    for field in ("strategy", "config", "metrics"):
        record[field] = json.loads(record.pop(f"{field}_json"))
    return record


def replay_experiment(record: dict) -> ExperimentResult:
    """Recompute from archived prices; reject any mismatch in the audit fingerprint."""
    from quant_lab.research import run_experiment
    from quant_lab.research_versions import legacy_versions
    legacy_versions(record.get("input_manifest",{}))

    result = run_experiment(
        record["raw_history"], record["signal_history"],
        StrategySpec(**record["strategy"]), BacktestConfig(**record["config"]),
        record["train_fraction"],
    )
    if result.audit_id != record["audit_id"]:
        raise ValueError("复算指纹与保存记录不一致。")
    expected=record.get("metrics")
    if expected is not None:
        for field,stats in (("strategy",result.full_stats),("benchmark",result.benchmark_stats),("train",result.train_stats),("test",result.test_stats)):
            original=expected.get(field,{})
            for key,value in asdict(stats).items():
                saved=original.get(key)
                same=saved is None and value is None
                if saved is not None and value is not None:
                    same=math.isfinite(float(saved)) and math.isfinite(float(value)) and math.isclose(float(saved),float(value),rel_tol=1e-10,abs_tol=1e-10)
                if not same:raise ValueError("旧档数值与兼容算法不一致；保留原记录，不用当前算法重新解释。")
        previous_orders=expected.get("orders")
        if previous_orders is not None:
            replayed=result.strategy.orders.to_dict(orient="records")
            if len(previous_orders)!=len(replayed):raise ValueError("旧档成交记录与兼容算法不一致。")
            for old,new in zip(previous_orders,replayed):
                if set(old)!=set(new):raise ValueError("旧档成交记录结构不受当前兼容算法支持。")
                for field,value in new.items():
                    saved=old[field]
                    if field in {"date","decision_date"}:same=pd.Timestamp(saved)==pd.Timestamp(value)
                    elif field in {"price","fees","cash_after"}:
                        missing_price=field=="price" and new.get("status")=="blocked"
                        same=bool(pd.isna(saved) and pd.isna(value)) if missing_price else saved is None and value is None
                        if not same and saved is not None and value is not None:same=math.isfinite(float(saved)) and math.isfinite(float(value)) and math.isclose(float(saved),float(value),rel_tol=1e-10,abs_tol=1e-10)
                    else:same=saved==value
                    if not same:raise ValueError("旧档成交记录与兼容算法不一致；原记录保持可读，不按新结果改写。")
    return result


def export_experiment_zip(record: dict) -> bytes:
    """Portable report with exact CSV inputs and machine-readable assumptions."""
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("report.md", render_report(record))
        archive.writestr("raw_history.csv", record["raw_csv_bytes"])
        archive.writestr("signal_history.csv", record["signal_csv_bytes"])
        archive.writestr("assumptions.json", json.dumps({
            "strategy": record["strategy"], "config": record["config"],
            "train_fraction": record["train_fraction"],
            "source": record["source"], "adjustment": record["adjustment"],
            "market": record["market"], "symbol": record["symbol"],
            "company_name": record.get("company_name", ""),
            "audit_id": record["audit_id"],
            "raw_sha256": record["raw_sha256"],
            "signal_sha256": record["signal_sha256"],
            "input_manifest": record.get("input_manifest", {}),
            "versions": record.get("versions", {}),
            "version_declared": record.get("version_declared",False),
            "metrics": record.get("metrics"),
        }, ensure_ascii=False, indent=2))
    return output.getvalue()


def render_report(record: dict) -> str:
    metrics = record["metrics"]
    return redact("\n".join([
        f"# {record['title']}", "", f"- 实验编号：{record['id']}",
        f"- 假设：{record['hypothesis']}",
        f"- 标的：{display_security(record['market'], record['symbol'], record.get('company_name'))}",
        f"- 区间：{record['start_date']} 至 {record['end_date']}",
        f"- 数据来源：{record['source']}；复权：{record['adjustment'] or '不复权'}",
        f"- 上次成功获取时间（北京时间 UTC+08:00）：{_beijing(record['received_at'])}",
        f"- 实验时间（UTC）：{record['created_at']}",
        f"- 实验指纹：{record['audit_id']}",
        f"- 版本：{json.dumps(record.get('versions',{}),ensure_ascii=False)}；{'显式记录' if record.get('version_declared') else '旧档未声明，按兼容算法核对'}",
        f"- 原始/信号数据 SHA-256：{record['raw_sha256']} / {record['signal_sha256']}",
        "", "## 策略与成交假设", "",
        "```json", json.dumps({"strategy": record["strategy"], "config": record["config"],
                            "train_fraction": record["train_fraction"]}, ensure_ascii=False, indent=2),
        "```", "", "## 结果", "",
        f"- 策略累计收益：{metrics['strategy']['cumulative_return']:.4%}",
        f"- 最大回撤：{metrics['strategy']['max_drawdown']:.4%}",
        f"- 夏普比率：{metrics['strategy']['sharpe']}",
        f"- 同成本买入持有累计收益：{metrics['benchmark']['cumulative_return']:.4%}",
        f"- 样本外起点：{metrics['split_date']}",
        "", "## 学习笔记", "", record["notes"], "",
        "## 复现", "",
        "本地 SQLite 记录内含本次使用的原始成交价格和信号价格完整快照，"
        "可用相同策略、费用和训练比例重新运行。日线回测仍不证明可实际成交。", "",
    ]))


def _beijing(value: str | None) -> str:
    from zoneinfo import ZoneInfo
    if not value:
        return "未记录（旧实验）"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(sep=" ")


SETTING_KEYS = {"refresh_enabled", "refresh_interval_seconds", "learning_mode", "deepseek_model", "deepseek_answer_mode"}


def load_settings(path: Path | None = None) -> dict:
    if not (path or database_path()).exists():
        return {}
    with _connect(path) as db:
        return {r["key"]: json.loads(r["value_json"]) for r in db.execute("SELECT * FROM settings")
                if r["key"] in SETTING_KEYS}


def save_setting(key: str, value, path: Path | None = None) -> None:
    if key not in SETTING_KEYS:
        raise ValueError("该设置不允许写入研究数据库。")
    if isinstance(value, str) and redact(value) != value:
        raise ValueError("不能把密钥写入普通设置。")
    with _connect(path) as db:
        db.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                   (key, json.dumps(value, ensure_ascii=False)))


def cached_security_name(market: str, symbol: str, path: Path | None = None) -> dict | None:
    if not (path or database_path()).exists():
        return None
    with _connect(path) as db:
        row = db.execute("SELECT * FROM security_names WHERE market=? AND symbol=?", (market, symbol)).fetchone()
        return dict(row) if row else None


def save_security_name(market: str, symbol: str, name: str, source: str,
                       fetched_at: datetime, path: Path | None = None) -> None:
    with _connect(path) as db:
        db.execute("""INSERT INTO security_names VALUES (?,?,?,?,?) ON CONFLICT(market,symbol)
                   DO UPDATE SET name=excluded.name,source=excluded.source,fetched_at=excluded.fetched_at""",
                   (market, symbol, redact(name), source, fetched_at.isoformat()))


def save_learning_note(title: str, content: str, *, model: str = "", origin: str = "手写",
                       market: str | None = None, symbol: str | None = None,
                       experiment_id: int | None = None, path: Path | None = None,
                       secrets=()) -> int:
    if not title.strip() or not content.strip():
        raise ValueError("笔记标题与内容不能为空。")
    now = datetime.now(timezone.utc).isoformat()
    with _connect(path) as db:
        cur = db.execute("""INSERT INTO learning_notes
            (title,content,origin,model,market,symbol,experiment_id,created_at,category_id,updated_at)
            VALUES (?,?,?,?,?,?,?,?,1,?)""",
            (redact(title, secrets), redact(content, secrets), redact(origin, secrets), redact(model, secrets), market, symbol,
             experiment_id, now, now))
        return int(cur.lastrowid)


def list_learning_notes(path: Path | None = None) -> list[dict]:
    if not (path or database_path()).exists():
        return []
    with _connect(path) as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM learning_notes WHERE deleted_at IS NULL ORDER BY id DESC"
        )]
