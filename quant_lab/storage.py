"""SQLite research archive and watchlists in the user's writable profile."""

from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zlib
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Iterator

import pandas as pd

from quant_lab.backtest import BacktestConfig
from quant_lab.market_data import normalize_symbol
from quant_lab.paths import user_data_dir
from quant_lab.research import ExperimentResult
from quant_lab.strategy import StrategySpec


def database_path() -> Path:
    return user_data_dir() / "research.sqlite3"


@contextmanager
def _connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=15)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            market TEXT NOT NULL, symbol TEXT NOT NULL,
            added_at TEXT NOT NULL, PRIMARY KEY (market, symbol)
        );
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, hypothesis TEXT NOT NULL,
            notes TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL,
            start_date TEXT NOT NULL, end_date TEXT NOT NULL,
            strategy_json TEXT NOT NULL, config_json TEXT NOT NULL,
            train_fraction REAL NOT NULL, metrics_json TEXT NOT NULL,
            source TEXT NOT NULL, adjustment TEXT NOT NULL,
            received_at TEXT, created_at TEXT NOT NULL, audit_id TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL, signal_sha256 TEXT NOT NULL,
            raw_csv BLOB NOT NULL, signal_csv BLOB NOT NULL
        );
        """)
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


def add_watchlist(market: str, symbol: str, path: Path | None = None) -> str:
    symbol = normalize_symbol(market, symbol)
    with _connect(path) as db:
        count = db.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        present = db.execute("SELECT 1 FROM watchlist WHERE market=? AND symbol=?",
                             (market, symbol)).fetchone()
        if count >= 10 and not present:
            raise ValueError("自选股最多保存 10 只，以控制免费数据接口请求量。")
        db.execute("INSERT OR IGNORE INTO watchlist VALUES (?, ?, ?)",
                   (market, symbol, datetime.now(timezone.utc).isoformat()))
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
) -> int:
    if not title.strip() or not hypothesis.strip():
        raise ValueError("研究标题和假设不能为空。")
    symbol = normalize_symbol(market, symbol)
    if config.market != market:
        raise ValueError("回测市场与研究市场不一致。")
    if raw_history.empty or signal_history.empty:
        raise ValueError("实验不能保存空行情。")
    raw_bytes, signal_bytes = _csv_bytes(raw_history), _csv_bytes(signal_history)
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
                raw_sha256, signal_sha256, raw_csv, signal_csv
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            title.strip(), hypothesis.strip(), notes.strip(), market, symbol,
            str(raw_history["date"].iloc[0].date()), str(raw_history["date"].iloc[-1].date()),
            json.dumps(asdict(spec), ensure_ascii=False),
            json.dumps(asdict(config), ensure_ascii=False), train_fraction,
            json.dumps(stats, ensure_ascii=False, default=str), source, adjustment,
            received_at.isoformat() if received_at else None,
            datetime.now(timezone.utc).isoformat(), result.audit_id,
            hashlib.sha256(raw_bytes).hexdigest(), hashlib.sha256(signal_bytes).hexdigest(),
            zlib.compress(raw_bytes), zlib.compress(signal_bytes),
        ))
        return int(cursor.lastrowid)


def list_experiments(path: Path | None = None) -> list[dict]:
    if not (path or database_path()).exists():
        return []
    with _connect(path) as db:
        rows = db.execute("""
            SELECT id, title, market, symbol, start_date, end_date, created_at,
                   audit_id, source FROM experiments ORDER BY id DESC
        """).fetchall()
        return [dict(row) for row in rows]


def get_experiment(experiment_id: int, path: Path | None = None) -> dict:
    with _connect(path) as db:
        row = db.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
    if row is None:
        raise KeyError(f"找不到实验 {experiment_id}")
    record = dict(row)
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

    result = run_experiment(
        record["raw_history"], record["signal_history"],
        StrategySpec(**record["strategy"]), BacktestConfig(**record["config"]),
        record["train_fraction"],
    )
    if result.audit_id != record["audit_id"]:
        raise ValueError("复算指纹与保存记录不一致。")
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
            "audit_id": record["audit_id"],
            "raw_sha256": record["raw_sha256"],
            "signal_sha256": record["signal_sha256"],
        }, ensure_ascii=False, indent=2))
    return output.getvalue()


def render_report(record: dict) -> str:
    metrics = record["metrics"]
    return "\n".join([
        f"# {record['title']}", "", f"- 实验编号：{record['id']}",
        f"- 假设：{record['hypothesis']}",
        f"- 标的：{record['market']} {record['symbol']}",
        f"- 区间：{record['start_date']} 至 {record['end_date']}",
        f"- 数据来源：{record['source']}；复权：{record['adjustment'] or '不复权'}",
        f"- 行情接收时间（UTC）：{record['received_at'] or '未记录'}",
        f"- 实验时间（UTC）：{record['created_at']}",
        f"- 实验指纹：{record['audit_id']}",
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
    ])
