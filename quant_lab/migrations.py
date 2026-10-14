"""Transactional SQLite upgrades, including the original unversioned database."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import RLock
from uuid import uuid4


SCHEMA_VERSION = 3
_LOCK = RLock()
BASE_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS watchlist (
        market TEXT NOT NULL, symbol TEXT NOT NULL, added_at TEXT NOT NULL,
        PRIMARY KEY (market, symbol))""",
    """CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, hypothesis TEXT NOT NULL,
        notes TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL,
        start_date TEXT NOT NULL, end_date TEXT NOT NULL,
        strategy_json TEXT NOT NULL, config_json TEXT NOT NULL,
        train_fraction REAL NOT NULL, metrics_json TEXT NOT NULL,
        source TEXT NOT NULL, adjustment TEXT NOT NULL, received_at TEXT,
        created_at TEXT NOT NULL, audit_id TEXT NOT NULL,
        raw_sha256 TEXT NOT NULL, signal_sha256 TEXT NOT NULL,
        raw_csv BLOB NOT NULL, signal_csv BLOB NOT NULL)""",
)


def _upgrade(db: sqlite3.Connection) -> None:
    for statement in BASE_SCHEMA:
        db.execute(statement)
    for table in ("watchlist", "experiments"):
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if "company_name" not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN company_name TEXT NOT NULL DEFAULT ''")
    db.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value_json TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS security_names (
        market TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL,
        source TEXT NOT NULL, fetched_at TEXT NOT NULL, PRIMARY KEY(market,symbol))""")
    db.execute("""CREATE TABLE IF NOT EXISTS learning_notes (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
        origin TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', market TEXT,
        symbol TEXT, experiment_id INTEGER, created_at TEXT NOT NULL,
        FOREIGN KEY(experiment_id) REFERENCES experiments(id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS learning_progress (
        kind TEXT NOT NULL, item_id TEXT NOT NULL, status TEXT NOT NULL,
        details_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL,
        PRIMARY KEY(kind,item_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS learning_quiz_attempts (
        id INTEGER PRIMARY KEY, course_id TEXT NOT NULL, answer REAL NOT NULL,
        correct INTEGER NOT NULL CHECK(correct IN (0,1)), created_at TEXT NOT NULL)""")


def migrate(db: sqlite3.Connection, target: Path) -> None:
    with _LOCK:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise ValueError("数据库版本比当前软件新，请使用新版软件打开。")
        if version == SCHEMA_VERSION:
            return
        existing = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()
        if existing:
            directory = target.parent / "backups"
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = directory / f"research.pre-v{SCHEMA_VERSION}.{stamp}.{uuid4().hex[:8]}.sqlite3"
            backup = sqlite3.connect(backup_path)
            try:
                db.backup(backup)
            finally:
                backup.close()
        db.execute("BEGIN IMMEDIATE")
        try:
            _upgrade(db)
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            db.commit()
        except Exception:
            db.rollback()
            raise
