"""Learning migration and reset preserve existing research and private notes."""

import sqlite3

import pytest

from quant_lab import learning_store, storage, migrations
from test_migrations import legacy_database


def test_progress_quiz_goal_survive_reopen_and_reset_preserves_research(tmp_path):
    database, audit = legacy_database(tmp_path)
    old = storage.get_experiment(1, database)
    storage.save_learning_note("私人笔记", "不发送给模型", path=database)
    storage.save_setting("deepseek_model", "chosen-model", database)
    learning_store.save_progress("goal", "current", {"text":"掌握回撤"}, status="in_progress", path=database)
    learning_store.save_progress("course", "drawdown", {"method":"实验与测验"}, path=database)
    learning_store.save_progress("experiment", "drawdown", {"parameter":80}, path=database)
    learning_store.save_quiz_attempt("drawdown", -20, True, path=database)
    assert learning_store.load_progress(database)[("goal","current")]["details"]["text"] == "掌握回撤"
    assert learning_store.quiz_attempts(database)[0]["correct"] == 1
    learning_store.reset_progress(database)
    assert learning_store.load_progress(database) == {} and learning_store.quiz_attempts(database) == []
    assert storage.get_experiment(1,database)["raw_csv_bytes"] == old["raw_csv_bytes"]
    assert storage.replay_experiment(storage.get_experiment(1,database)).audit_id == audit
    assert storage.list_learning_notes(database)[0]["content"] == "不发送给模型"
    assert storage.load_settings(database)["deepseek_model"] == "chosen-model"


def test_v2_upgrade_backup_preserves_notes_and_rolls_back_on_failure(tmp_path, monkeypatch):
    database = tmp_path / "v2.sqlite3"
    storage.save_learning_note("旧笔记", "正文", path=database)
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE learning_progress")
        db.execute("DROP TABLE learning_quiz_attempts")
        db.execute("PRAGMA user_version=2")
    original = migrations._upgrade
    def fail(db):
        original(db)
        raise sqlite3.OperationalError("injected v3 failure")
    monkeypatch.setattr(migrations, "_upgrade", fail)
    with pytest.raises(sqlite3.OperationalError):
        learning_store.load_progress(database)
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='learning_progress'").fetchone()
        assert db.execute("SELECT content FROM learning_notes").fetchone()[0] == "正文"
    backup = next((tmp_path / "backups").glob("research.pre-v3.*"))
    with sqlite3.connect(backup) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    monkeypatch.setattr(migrations, "_upgrade", original)
    assert learning_store.load_progress(database) == {}
    assert storage.list_learning_notes(database)[0]["content"] == "正文"


def test_goal_secrets_are_redacted_and_invalid_records_rejected(tmp_path):
    database = tmp_path / "learning.sqlite3"
    secret = "custom-private-api-credential"
    learning_store.save_progress("goal", "current", {"text":"误粘贴 " + secret}, path=database, secrets=(secret,))
    assert secret not in database.read_bytes().decode("utf-8", errors="ignore")
    with pytest.raises(ValueError):
        learning_store.save_progress("api_key", "secret", path=database)
    with pytest.raises(ValueError):
        learning_store.save_quiz_attempt("drawdown", float("nan"), True, path=database)
