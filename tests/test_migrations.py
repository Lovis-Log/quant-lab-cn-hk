"""Upgrade populated unversioned files with rollback and byte-preserved inputs."""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pytest

from quant_lab import migrations, storage
from quant_lab.backtest import BacktestConfig
from quant_lab.research import run_experiment
from quant_lab.strategy import StrategySpec
from test_research_storage import history


def legacy_database(tmp_path):
    fresh, old = tmp_path / "fresh.sqlite3", tmp_path / "legacy.sqlite3"
    frame = history()
    spec, config = StrategySpec("dual_ma", 2, 3), BacktestConfig(limit_pct=None)
    result = run_experiment(frame, frame, spec, config)
    storage.save_experiment(title="旧研究", hypothesis="旧假设", notes="旧私人笔记", market="A 股", symbol="600519",
        raw_history=frame, signal_history=frame, spec=spec, config=config, train_fraction=.7,
        result=result, source="old source", adjustment="", received_at=datetime.now(timezone.utc), path=fresh)
    with sqlite3.connect(old) as db, sqlite3.connect(fresh) as source:
        for sql in migrations.BASE_SCHEMA:
            db.execute(sql)
        columns = [r[1] for r in db.execute("PRAGMA table_info(experiments)")]
        row = source.execute("SELECT " + ",".join(columns) + " FROM experiments").fetchone()
        db.execute("INSERT INTO experiments VALUES (" + ",".join("?" * len(columns)) + ")", row)
        db.execute("INSERT INTO watchlist VALUES ('港股','00700','2026-10-01T00:00:00+00:00')")
    return old, result.audit_id


def test_populated_legacy_migration_and_replay(tmp_path):
    old, audit = legacy_database(tmp_path)
    with sqlite3.connect(old) as db:
        prior = db.execute("SELECT raw_csv,signal_csv,notes FROM experiments").fetchone()
    assert storage.list_watchlist(old) == [("港股", "00700")]
    record = storage.get_experiment(1, old)
    assert record["company_name"] == "" and record["notes"] == "旧私人笔记"
    assert storage.replay_experiment(record).audit_id == audit
    assert "名称暂不可用" in storage.render_report(record)
    with ZipFile(BytesIO(storage.export_experiment_zip(record))) as archive:
        assert archive.read("raw_history.csv") == record["raw_csv_bytes"]
    with sqlite3.connect(old) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("SELECT raw_csv,signal_csv,notes FROM experiments").fetchone() == prior
    backups = list((tmp_path / "backups").glob("research.pre-v2.*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 0
        assert backup.execute("SELECT raw_csv,signal_csv,notes FROM experiments").fetchone() == prior
    storage.list_experiments(old)
    assert len(list((tmp_path / "backups").glob("research.pre-v2.*.sqlite3"))) == 1


def test_migration_failure_rolls_back_schema_and_rows(tmp_path, monkeypatch):
    old, _ = legacy_database(tmp_path)
    def fail(db):
        db.execute("ALTER TABLE experiments ADD COLUMN company_name TEXT")
        raise sqlite3.OperationalError("injected migration failure")
    monkeypatch.setattr(migrations, "_upgrade", fail)
    with pytest.raises(sqlite3.OperationalError):
        storage.list_experiments(old)
    with sqlite3.connect(old) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert "company_name" not in {r[1] for r in db.execute("PRAGMA table_info(experiments)")}
        assert db.execute("SELECT notes FROM experiments").fetchone()[0] == "旧私人笔记"


def test_new_settings_notes_and_snapshot_are_isolated(tmp_path):
    old, audit = legacy_database(tmp_path)
    before = storage.get_experiment(1, old)
    storage.save_setting("refresh_interval_seconds", 600, old)
    with pytest.raises(ValueError):
        storage.save_setting("api_key", "sk-do-not-store-this-key", old)
    storage.save_learning_note("回答", "请核对 sk-do-not-store-this-key", model="model-x", path=old)
    assert "sk-do-not-store-this-key" not in storage.list_learning_notes(old)[0]["content"]
    after = storage.get_experiment(1, old)
    assert after["raw_csv_bytes"] == before["raw_csv_bytes"]
    assert storage.replay_experiment(after).audit_id == audit
    assert storage.load_settings(old)["refresh_interval_seconds"] == 600
