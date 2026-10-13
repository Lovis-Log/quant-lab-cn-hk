"""Two-phase old->new installation test with unique AppId and owned directories.

Prepare the old installer before rebuilding dist/QuantLab; then upgrade using
the newly built payload. Never touches the normal installation or real data.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def command(args, log):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    log.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"Isolated validation command failed ({result.returncode}); see {log}")


def compile_installer(state, version, phase):
    root = Path(state["root"]).resolve()
    root.relative_to((ROOT/".tools").resolve())
    script = (ROOT/"installer/QuantLab.iss").read_text(encoding="utf-8")
    script = script.replace('#define MyAppName "Quant Lab CN/HK"', '#define MyAppName "Quant Lab Isolated Validation"')
    lines = []
    for line in script.splitlines():
        replacements = {
            "AppId=": "AppId={{" + state["app_id"] + "}",
            "DefaultDirName=": "DefaultDirName=" + state["install_dir"],
            "DefaultGroupName=": "DefaultGroupName=QuantLabValidation-" + state["app_id"],
            "OutputDir=": "OutputDir=" + str(root/phase),
            "OutputBaseFilename=": "OutputBaseFilename=IsolatedValidationSetup",
            "SetupIconFile=": "SetupIconFile=" + str(ROOT/"assets/quantlab.ico"),
            "PrivilegesRequired=": "PrivilegesRequired=lowest",
            'Source: "..\\dist\\QuantLab\\*"': f'Source: "{ROOT / "dist/QuantLab"}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs',
        }
        replaced = next((value for prefix,value in replacements.items() if line.startswith(prefix)), line)
        if replaced.startswith("Name:") and "Quant Lab CN-HK" in replaced:
            replaced = replaced.replace("Quant Lab CN-HK", "QuantLabValidation-" + state["app_id"])
        lines.append(replaced)
    spec = root/f"{phase}.iss"
    spec.write_text("\n".join(lines), encoding="utf-8")
    numeric = version.split("-")[0] + ".0"
    command([ROOT/".tools/InnoSetup7/ISCC.exe", f"/DMyAppVersion={version}", f"/DMyAppFileVersion={numeric}", spec], root/f"{phase}-compile.log")
    return root/phase/"IsolatedValidationSetup.exe"


def install(state, installer, phase):
    root = Path(state["root"])
    command([installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS",
             f"/DIR={state['install_dir']}", f"/LOG={root / (phase+'-install.log')}"], root/f"{phase}-install-output.log")
    assert (Path(state["install_dir"])/"QuantLab.exe").is_file()


def seed_old_database(state):
    from quant_lab import storage, migrations
    from quant_lab.backtest import BacktestConfig
    from quant_lab.strategy import StrategySpec
    from quant_lab.research import run_experiment
    import pandas as pd
    root = Path(state["root"])
    seed = root/"seed.sqlite3"
    frame = pd.DataFrame({"date":pd.date_range("2026-01-05",periods=40,freq="B"),
                          "open":[10+i*.1 for i in range(40)], "high":[11+i*.1 for i in range(40)],
                          "low":[9+i*.1 for i in range(40)], "close":[10.2+i*.1 for i in range(40)],
                          "volume":[10000]*40,"amount":[100000]*40})
    spec, config = StrategySpec("dual_ma",2,3), BacktestConfig(limit_pct=None)
    result = run_experiment(frame,frame,spec,config)
    storage.save_experiment(title="旧库隔离验收实验", hypothesis="仅验证迁移和复算", notes="旧学习笔记必须保留",
        market="A 股",symbol="000001",raw_history=frame,signal_history=frame,spec=spec,config=config,
        train_fraction=.7,result=result,source="隔离验收模拟样本，非行情",adjustment="",
        received_at=datetime.now(timezone.utc),path=seed)
    directory = Path(state["user_data"])
    directory.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(directory/"research.sqlite3") as db, sqlite3.connect(seed) as source:
        for sql in migrations.BASE_SCHEMA:
            db.execute(sql)
        columns = [r[1] for r in db.execute("PRAGMA table_info(experiments)")]
        row = source.execute("SELECT "+",".join(columns)+" FROM experiments").fetchone()
        db.execute("INSERT INTO experiments VALUES ("+",".join("?"*len(columns))+")",row)
        db.execute("INSERT INTO watchlist VALUES ('A 股','600519','2026-10-01T00:00:00+00:00')")
        state["raw_blob_sha256"] = hashlib.sha256(db.execute("SELECT raw_csv FROM experiments").fetchone()[0]).hexdigest()
    state["audit_id"] = result.audit_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-old",action="store_true")
    parser.add_argument("--upgrade",type=Path)
    parser.add_argument("--resume",action="store_true",help="Resume GUI checks after a verified installation")
    args = parser.parse_args()
    if args.prepare_old:
        old_version = (ROOT/"dist/QuantLab/_internal/VERSION").read_text(encoding="utf-8").strip()
        old_manifest = json.loads((ROOT/"docs/releases/v1.1.0-rc.1-build.json").read_text(encoding="utf-8-sig"))
        assert old_version == "1.1.0-rc.1"
        assert digest(ROOT/"dist/QuantLab/QuantLab.exe") == next(a["sha256"] for a in old_manifest["assets"] if a["name"]=="QuantLab.exe")
        root = ROOT/".tools"/("installer-validation-"+uuid4().hex)
        root.mkdir(parents=True)
        state = {"root":str(root),"app_id":str(uuid4()).upper(),"install_dir":str(root/"InstalledApp"),
                 "user_data":str(root/"UserData"),"old_version":old_version}
        old_installer = compile_installer(state,old_version,"old")
        install(state,old_installer,"old")
        seed_old_database(state)
        state_path = root/"installation-state.json"
        state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({"old_install_passed":True,"state_file":str(state_path)},ensure_ascii=False))
        return
    if not args.upgrade:
        parser.error("Choose --prepare-old or --upgrade <state-file>")
    state_path = args.upgrade.resolve()
    state_path.relative_to((ROOT/".tools").resolve())
    state = json.loads(state_path.read_text(encoding="utf-8"))
    root = Path(state["root"])
    version = (ROOT/"VERSION").read_text().strip()
    if args.resume:
        assert (root/"new-install.log").is_file()
        assert digest(Path(state["install_dir"])/"QuantLab.exe") == digest(ROOT/"dist/QuantLab/QuantLab.exe")
    else:
        new_installer = compile_installer(state,version,"new")
        install(state,new_installer,"new")
    assert (Path(state["install_dir"])/"_internal/VERSION").read_text().strip() == version
    python = ROOT/".venv/Scripts/python.exe"
    exe = Path(state["install_dir"])/"QuantLab.exe"
    database = Path(state["user_data"])/"research.sqlite3"
    with sqlite3.connect(database) as db:
        has_notes = db.execute("SELECT 1 FROM sqlite_master WHERE name='learning_notes'").fetchone()
        previous_notes = list(db.execute("SELECT id,title,content,model FROM learning_notes")) if has_notes else []
    # First test untouched installed entry, then the same component with a
    # temporary mocked API transport, then untouched entry after restart.
    for phase,mock in (("gui-original",False),("gui-mock",True),("gui-restart",False)):
        cmd = [python,ROOT/"tools/verify_desktop_gui.py","--exe",exe,"--data-dir",state["user_data"]]
        if mock:
            cmd.append("--mock-ai")
        command(cmd,root/f"{phase}.log")
    from quant_lab import storage
    record = storage.get_experiment(1,database)
    assert record["notes"] == "旧学习笔记必须保留"
    assert storage.replay_experiment(record).audit_id == state["audit_id"]
    assert len(storage.list_watchlist(database)) == 1
    assert len(storage.list_learning_notes(database)) == len(previous_notes)+1
    assert storage.load_settings(database)["refresh_enabled"] is False
    assert storage.load_settings(database)["deepseek_model"] == "manual-model-validation"
    with sqlite3.connect(database) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        current_notes = list(db.execute("SELECT id,title,content,model FROM learning_notes"))
        assert all(row in current_notes for row in previous_notes)
        assert hashlib.sha256(db.execute("SELECT raw_csv FROM experiments").fetchone()[0]).hexdigest() == state["raw_blob_sha256"]
    assert list((Path(state["user_data"])/"backups").glob("*.sqlite3"))
    secret = b"sk-isolated-ui-dummy-key"
    assert secret not in database.read_bytes()
    for log in Path(state["user_data"]).rglob("*.log"):
        assert secret not in log.read_bytes()
    uninstaller = Path(state["install_dir"])/"unins000.exe"
    command([uninstaller,"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART",f"/LOG={root/'uninstall.log'}"],root/"uninstall-output.log")
    assert database.exists() and not exe.exists()
    result = {"old_version":state["old_version"],"new_version":version,"isolated_app_id":state["app_id"],
              "install_upgrade_uninstall":True,"legacy_snapshot_unchanged":True,"replay_passed":True,
              "settings_and_notes_survived_restart":True,"key_not_restored_to_session":True,
              "gui_original_and_mock_stream_passed":True,"user_data_preserved_after_uninstall":True}
    (root/"installation-result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({**result,"record_dir":str(root)},ensure_ascii=False))


if __name__ == "__main__":
    main()
