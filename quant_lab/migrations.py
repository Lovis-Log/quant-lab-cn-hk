"""Transactional SQLite upgrades, including the original unversioned database."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import RLock
from uuid import uuid4


SCHEMA_VERSION = 5
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
    db.execute("""CREATE TABLE IF NOT EXISTS note_categories (
        id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES note_categories(id),
        name TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
        is_system INTEGER NOT NULL DEFAULT 0 CHECK(is_system IN (0,1)),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    now = datetime.now(timezone.utc).isoformat()
    db.execute("""INSERT OR IGNORE INTO note_categories
        (id,parent_id,name,sort_order,is_system,created_at,updated_at)
        VALUES (1,NULL,'未分类',0,1,?,?)""", (now, now))
    for table in ("learning_notes", "experiments"):
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if "category_id" not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN category_id INTEGER REFERENCES note_categories(id)")
        if "deleted_at" not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TEXT")
        if table == "learning_notes" and "updated_at" not in columns:
            db.execute("ALTER TABLE learning_notes ADD COLUMN updated_at TEXT")
            db.execute("UPDATE learning_notes SET updated_at=created_at WHERE updated_at IS NULL")
    db.execute("""CREATE TABLE IF NOT EXISTS note_drafts (
        id TEXT PRIMARY KEY, note_id INTEGER REFERENCES learning_notes(id),
        title TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '',
        category_id INTEGER NOT NULL DEFAULT 1 REFERENCES note_categories(id),
        client_updated_at TEXT, updated_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS note_attachments (
        id TEXT PRIMARY KEY, note_id INTEGER REFERENCES learning_notes(id), draft_id TEXT,
        original_name TEXT NOT NULL, stored_relpath TEXT NOT NULL UNIQUE,
        mime_type TEXT NOT NULL, size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        CHECK((note_id IS NOT NULL AND draft_id IS NULL) OR
              (note_id IS NULL AND draft_id IS NOT NULL)))""")
    db.execute("""CREATE TABLE IF NOT EXISTS ai_conversations (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, scope TEXT NOT NULL,
        context_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, opened_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS ai_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
        turn_id TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','assistant')),
        kind TEXT NOT NULL DEFAULT 'chat', content TEXT NOT NULL,
        model TEXT NOT NULL DEFAULT '', requested_model TEXT NOT NULL DEFAULT '',
        security TEXT NOT NULL DEFAULT '', complete INTEGER NOT NULL DEFAULT 1
            CHECK(complete IN (0,1)), finish_reason TEXT, error TEXT,
        context_json TEXT NOT NULL DEFAULT '{}', saved_note_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(saved_note_id) REFERENCES learning_notes(id) ON DELETE SET NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_notes_category ON learning_notes(category_id,deleted_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_experiments_category ON experiments(category_id,deleted_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_categories_parent ON note_categories(parent_id,sort_order,name)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ai_conversations_scope ON ai_conversations(scope,opened_at DESC)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation ON ai_messages(conversation_id,created_at)")
    db.execute("UPDATE learning_notes SET category_id=1 WHERE category_id IS NULL")
    db.execute("UPDATE experiments SET category_id=1 WHERE category_id IS NULL")


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
            if target.parent.name == "database":
                directory = target.parent.parent / "backups"
                directory.mkdir(parents=True, exist_ok=True)
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
