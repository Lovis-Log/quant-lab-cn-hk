"""Isolated V2 install, old-v2 archive, actual DOM and uninstall verification."""

from pathlib import Path
import hashlib
import json
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.verify_installation import compile_installer, install, seed_old_database, command, digest
from quant_lab import storage, learning_store
from quant_lab.migrations import SCHEMA_VERSION


def main():
    version = (ROOT / "VERSION").read_text().strip()
    manifest = json.loads((ROOT / "dist/release" / version / "build-manifest.json").read_text(encoding="utf-8-sig"))
    payload = Path(manifest["payload_dir"])
    root = ROOT / ".tools" / ("learning-delivery-" + uuid4().hex)
    root.mkdir()
    state = {"root":str(root),"app_id":str(uuid4()).upper(),
             "install_dir":str(root/"InstalledApp"),"user_data":str(root/"UserData")}
    print(json.dumps({"record_dir":str(root)}), flush=True)
    (root/"installation-state.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
    seed_old_database(state)
    database = Path(state["user_data"]) / "research.sqlite3"
    storage.save_learning_note("V2 升级前笔记", "原笔记必须保留", path=database)
    initial_note_count = len(storage.list_learning_notes(database))
    # A owned test archive with the actual v2 shape and pre-existing notes.
    with sqlite3.connect(database) as db:
        db.execute("DROP TABLE learning_progress")
        db.execute("DROP TABLE learning_quiz_attempts")
        db.execute("PRAGMA user_version=2")
    installer = compile_installer(state,version,"new")
    install(state,installer,"new")
    exe = Path(state["install_dir"]) / "QuantLab.exe"
    entry = exe.parent / "_internal/app.py"
    original = entry.read_bytes()
    assert digest(exe) == digest(payload / "QuantLab.exe")
    assert original == (payload / "_internal/app.py").read_bytes()
    for phase, flags in (("original",["--learning-center"]),
                         ("mock",["--research-fixes","--mock-ai"]),
                         ("restart",["--resume-learning"])):
        command([ROOT/".venv/Scripts/python.exe",ROOT/"tools/verify_desktop_gui.py",
                 "--exe",exe,"--data-dir",state["user_data"],*flags],root/f"gui-{phase}.log")
        assert entry.read_bytes() == original
        summary = json.loads((Path(state["user_data"])/"gui-result.json").read_text(encoding="utf-8"))
        (root/f"gui-{phase}.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({"phase":phase,"passed":True}),flush=True)
    records = learning_store.load_progress(database)
    assert records[("course","drawdown")]["status"] == "completed"
    assert records[("goal","current")]["details"]["text"] == "桌面验收：掌握回撤后理解样本外"
    assert len(learning_store.quiz_attempts(database)) == 1
    assert ("task","load_history") not in records  # Explicit mock daily data cannot pass the real task.
    assert ("task","run_backtest") not in records
    assert len(storage.list_learning_notes(database)) == initial_note_count + 5
    assert any(note["content"] == "原笔记必须保留" for note in storage.list_learning_notes(database))
    record = storage.get_experiment(1,database)
    assert storage.replay_experiment(record).audit_id == state["audit_id"]
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert hashlib.sha256(db.execute("SELECT raw_csv FROM experiments").fetchone()[0]).hexdigest() == state["raw_blob_sha256"]
    versions = []
    for path in (Path(state["user_data"])/"backups").glob("*.sqlite3"):
        with sqlite3.connect(path) as db:
            versions.append(db.execute("PRAGMA user_version").fetchone()[0])
    assert 2 in versions
    secret = b"sk-isolated-ui-dummy-key"
    assert secret not in database.read_bytes()
    for path in Path(state["user_data"]).rglob("*.log"):
        assert secret not in path.read_bytes()
    command([exe.parent/"unins000.exe","/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART",
             f"/LOG={root/'uninstall.log'}"],root/"uninstall-output.log")
    assert database.exists() and not exe.exists()
    result = {"version":version,"isolated_app_id":state["app_id"],"record_dir":str(root),
        "actual_learning_center_webview":True,"v2_to_v4_backup_and_migration":True,
        "progress_goal_notes_resumed_in_dom":True,"legacy_snapshot_and_replay_preserved":True,
        "professional_mode_control":True,"deepseek_research_mock":True,"entry_restored_after_mock":True,
        "mock_data_not_counted_as_real_task":True,"key_absent_from_database_and_logs":True,
        "isolated_install_uninstall":True,"user_data_retained_after_uninstall":True,
        "real_paid_api_tested":False,"real_market_full_flow_tested":False}
    (root/"validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
