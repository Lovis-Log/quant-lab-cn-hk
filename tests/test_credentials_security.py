"""Unavailable vaults never cause plaintext writes; study exports redact secrets."""

import json
import sqlite3
from io import BytesIO
from zipfile import ZipFile

import pytest

from quant_lab import credentials, storage


def test_vault_unavailable_does_not_write_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUANT_LAB_DATA_DIR", str(tmp_path))
    def unavailable():
        raise credentials.SecureStorageUnavailable("unavailable")
    monkeypatch.setattr(credentials, "_api", unavailable)
    with pytest.raises(credentials.SecureStorageUnavailable):
        credentials.remember_key("sk-no-plaintext-fallback")
    assert list(tmp_path.iterdir()) == []


def test_secret_rejected_in_settings_and_scrubbed_from_reports(tmp_path):
    from test_migrations import legacy_database
    database, _ = legacy_database(tmp_path)
    with pytest.raises(ValueError):
        storage.save_setting("deepseek_model", "sk-secret-should-not-be-a-model", database)
    record = storage.get_experiment(1, database)
    record["notes"] = "误粘贴 sk-secret-should-not-be-exported"
    assert "sk-secret" not in storage.render_report(record)
    with ZipFile(BytesIO(storage.export_experiment_zip(record))) as archive:
        assert b"sk-secret" not in archive.read("report.md")
