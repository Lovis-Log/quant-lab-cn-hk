"""Writable per-user application paths for web and packaged desktop runs."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4


LIBRARY_MARKER = "quantlab-library.json"


def default_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "QuantLabCNHK"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "quant-lab-cnhk"


def bootstrap_path() -> Path:
    return default_data_dir() / "bootstrap.json"


def _configured_root() -> Path | None:
    try:
        payload = json.loads(bootstrap_path().read_text(encoding="utf-8"))
        root = Path(payload["data_root"]).expanduser().resolve()
        if (root / LIBRARY_MARKER).is_file():
            return root
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return None


def user_data_dir() -> Path:
    override = os.environ.get("QUANT_LAB_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return _configured_root() or default_data_dir()


def library_configured() -> bool:
    return bool(os.environ.get("QUANT_LAB_DATA_DIR")) or _configured_root() is not None


def database_path() -> Path:
    root = user_data_dir()
    if os.environ.get("QUANT_LAB_DATA_DIR"):
        return root / "research.sqlite3"
    return root / "database" / "research.sqlite3"


def attachments_dir() -> Path:
    return user_data_dir() / "notes" / "attachments"


def drafts_dir() -> Path:
    return user_data_dir() / "notes" / "drafts"


def securities_dir() -> Path:
    root = user_data_dir()
    return root / "securities" if os.environ.get("QUANT_LAB_DATA_DIR") else root / "cache" / "securities"


def stage_library(parent: Path) -> Path:
    """Create and verify a managed library, then atomically activate it for next launch."""
    parent = parent.expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / "QuantLabCNHK"
    target.mkdir(parents=True, exist_ok=True)
    marker = target / LIBRARY_MARKER
    if any(target.iterdir()) and not marker.exists():
        raise ValueError("目标 QuantLabCNHK 文件夹不是空文件夹，也不是可识别的资料库。")
    for relative in ("database", "notes/attachments", "notes/drafts", "backups",
                     "exports", "logs", "cache/securities", "webview"):
        (target / relative).mkdir(parents=True, exist_ok=True)

    source = user_data_dir()
    source_db = source / "research.sqlite3"
    if not source_db.exists():
        source_db = source / "database" / "research.sqlite3"
    target_db = target / "database" / "research.sqlite3"
    if source_db.exists() and source_db.resolve() != target_db.resolve() and not target_db.exists():
        with sqlite3.connect(source_db) as old, sqlite3.connect(target_db) as new:
            old.backup(new)
            result = new.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise OSError("复制后的研究数据库完整性检查失败。")
    for source_name, target_name in (("backups", "backups"), ("securities", "cache/securities"),
                                     ("notes", "notes")):
        src = source / source_name
        if src.exists() and src.resolve() != (target / target_name).resolve():
            shutil.copytree(src, target / target_name, dirs_exist_ok=True)

    marker_payload = {"format": 1, "created_at": datetime.now(timezone.utc).isoformat()}
    marker.write_text(json.dumps(marker_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pointer = bootstrap_path()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    temporary = pointer.with_name(f"bootstrap.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps({"data_root": str(target)}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, pointer)
    return target
