"""Persistent categorized notes, drafts, attachments, and recycle-bin operations."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

from quant_lab.paths import attachments_dir, drafts_dir, user_data_dir
from quant_lab.security import redact
from quant_lab.storage import _connect


UNCATEGORIZED_ID = 1
MAX_CATEGORY_DEPTH = 8
MAX_ATTACHMENT_BYTES = 200 * 1024 * 1024
MAX_NOTE_ATTACHMENT_BYTES = 1024 * 1024 * 1024
MAX_NOTE_ATTACHMENTS = 20
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".csv", ".txt", ".md",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _category(db, category_id: int) -> dict:
    row = db.execute("SELECT * FROM note_categories WHERE id=?", (category_id,)).fetchone()
    if row is None:
        raise ValueError("笔记分类不存在。")
    return dict(row)


def list_categories(path: Path | None = None) -> list[dict]:
    with _connect(path) as db:
        rows = [dict(row) for row in db.execute(
            "SELECT * FROM note_categories ORDER BY parent_id IS NOT NULL,parent_id,sort_order,name"
        )]
    by_parent: dict[int | None, list[dict]] = {}
    for row in rows:
        by_parent.setdefault(row["parent_id"], []).append(row)
    output: list[dict] = []
    def visit(parent, depth):
        for row in by_parent.get(parent, []):
            output.append({**row, "depth": depth})
            visit(row["id"], depth + 1)
    visit(None, 0)
    return output


def _validate_category_name(name: str) -> str:
    value = " ".join(name.split()).strip()
    if not value or len(value) > 80 or any(ord(char) < 32 for char in value):
        raise ValueError("分类名称必须为 1–80 个可见字符。")
    return value


def _category_depth(db, category_id: int | None) -> int:
    depth, seen = 0, set()
    while category_id is not None:
        if category_id in seen:
            raise ValueError("分类树存在循环。")
        seen.add(category_id)
        row = db.execute("SELECT parent_id FROM note_categories WHERE id=?", (category_id,)).fetchone()
        if row is None:
            raise ValueError("父分类不存在。")
        depth += 1
        category_id = row[0]
    return depth


def create_category(name: str, parent_id: int | None = None, path: Path | None = None) -> int:
    name = _validate_category_name(name)
    with _connect(path) as db:
        if parent_id is not None:
            _category(db, parent_id)
            if _category_depth(db, parent_id) >= MAX_CATEGORY_DEPTH:
                raise ValueError(f"分类最多 {MAX_CATEGORY_DEPTH} 层。")
        duplicate = db.execute(
            "SELECT 1 FROM note_categories WHERE parent_id IS ? AND lower(name)=lower(?)",
            (parent_id, name),
        ).fetchone()
        if duplicate:
            raise ValueError("同一父分类下已有同名分类。")
        order = db.execute("SELECT COALESCE(MAX(sort_order),-1)+1 FROM note_categories WHERE parent_id IS ?",
                           (parent_id,)).fetchone()[0]
        now = _now()
        cur = db.execute("""INSERT INTO note_categories
            (parent_id,name,sort_order,is_system,created_at,updated_at) VALUES (?,?,?,?,?,?)""",
            (parent_id, name, order, 0, now, now))
        return int(cur.lastrowid)


def rename_category(category_id: int, name: str, path: Path | None = None) -> None:
    name = _validate_category_name(name)
    with _connect(path) as db:
        row = _category(db, category_id)
        if row["is_system"]:
            raise ValueError("系统分类不能重命名。")
        if db.execute("SELECT 1 FROM note_categories WHERE id<>? AND parent_id IS ? AND lower(name)=lower(?)",
                      (category_id, row["parent_id"], name)).fetchone():
            raise ValueError("同一父分类下已有同名分类。")
        db.execute("UPDATE note_categories SET name=?,updated_at=? WHERE id=?", (name, _now(), category_id))


def move_category(category_id: int, parent_id: int | None, path: Path | None = None) -> None:
    with _connect(path) as db:
        row = _category(db, category_id)
        if row["is_system"]:
            raise ValueError("系统分类不能移动。")
        if parent_id == category_id:
            raise ValueError("分类不能成为自己的父分类。")
        cursor = parent_id
        while cursor is not None:
            if cursor == category_id:
                raise ValueError("不能把分类移动到自己的子分类。")
            cursor = _category(db, cursor)["parent_id"]
        if parent_id is not None and _category_depth(db, parent_id) >= MAX_CATEGORY_DEPTH:
            raise ValueError(f"分类最多 {MAX_CATEGORY_DEPTH} 层。")
        db.execute("UPDATE note_categories SET parent_id=?,updated_at=? WHERE id=?",
                   (parent_id, _now(), category_id))


def delete_category(category_id: int, path: Path | None = None) -> None:
    with _connect(path) as db:
        row = _category(db, category_id)
        if row["is_system"]:
            raise ValueError("系统分类不能删除。")
        destination = row["parent_id"] or UNCATEGORIZED_ID
        db.execute("UPDATE note_categories SET parent_id=?,updated_at=? WHERE parent_id=?",
                   (row["parent_id"], _now(), category_id))
        db.execute("UPDATE learning_notes SET category_id=? WHERE category_id=?", (destination, category_id))
        db.execute("UPDATE experiments SET category_id=? WHERE category_id=?", (destination, category_id))
        db.execute("UPDATE note_drafts SET category_id=? WHERE category_id=?", (destination, category_id))
        db.execute("DELETE FROM note_categories WHERE id=?", (category_id,))


def save_draft(draft_id: str, *, title: str, content: str, category_id: int = UNCATEGORIZED_ID,
               note_id: int | None = None, client_updated_at: str | None = None,
               path: Path | None = None, secrets=()) -> None:
    with _connect(path) as db:
        _category(db, category_id)
        db.execute("""INSERT INTO note_drafts
            (id,note_id,title,content,category_id,client_updated_at,updated_at)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            note_id=excluded.note_id,title=excluded.title,content=excluded.content,
            category_id=excluded.category_id,client_updated_at=excluded.client_updated_at,
            updated_at=excluded.updated_at""",
            (draft_id, note_id, redact(title, secrets), redact(content, secrets), category_id,
             client_updated_at, _now()))


def load_draft(draft_id: str, path: Path | None = None) -> dict | None:
    with _connect(path) as db:
        row = db.execute("SELECT * FROM note_drafts WHERE id=?", (draft_id,)).fetchone()
        return dict(row) if row else None


def latest_draft(path: Path | None = None) -> dict | None:
    with _connect(path) as db:
        row = db.execute("SELECT * FROM note_drafts ORDER BY updated_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def discard_draft(draft_id: str, path: Path | None = None) -> None:
    with _connect(path) as db:
        rows = db.execute("SELECT stored_relpath FROM note_attachments WHERE draft_id=?", (draft_id,)).fetchall()
        db.execute("DELETE FROM note_attachments WHERE draft_id=?", (draft_id,))
        db.execute("DELETE FROM note_drafts WHERE id=?", (draft_id,))
    for row in rows:
        try:
            (user_data_dir() / row[0]).unlink(missing_ok=True)
        except OSError:
            pass


def save_note(*, title: str, content: str, category_id: int = UNCATEGORIZED_ID,
              note_id: int | None = None, draft_id: str | None = None,
              origin: str = "手写", model: str = "", experiment_id: int | None = None,
              path: Path | None = None, secrets=()) -> int:
    title, content = title.strip(), content.strip()
    if not title or not content:
        raise ValueError("笔记标题与内容不能为空。")
    now = _now()
    moved: list[tuple[Path, Path]] = []
    try:
        with _connect(path) as db:
            _category(db, category_id)
            if note_id is None:
                cur = db.execute("""INSERT INTO learning_notes
                    (title,content,origin,model,market,symbol,experiment_id,created_at,
                     category_id,updated_at,deleted_at) VALUES (?,?,?,?,?,?,?,?,?,?,NULL)""",
                    (redact(title, secrets), redact(content, secrets), redact(origin, secrets),
                     redact(model, secrets), None, None, experiment_id, now, category_id, now))
                note_id = int(cur.lastrowid)
            else:
                if not db.execute("SELECT 1 FROM learning_notes WHERE id=?", (note_id,)).fetchone():
                    raise KeyError("笔记不存在。")
                db.execute("""UPDATE learning_notes SET title=?,content=?,category_id=?,updated_at=?,
                           deleted_at=NULL WHERE id=?""",
                           (redact(title, secrets), redact(content, secrets), category_id, now, note_id))
            if draft_id:
                rows = db.execute("SELECT id,stored_relpath FROM note_attachments WHERE draft_id=?",
                                  (draft_id,)).fetchall()
                final_dir = attachments_dir() / str(note_id)
                final_dir.mkdir(parents=True, exist_ok=True)
                for row in rows:
                    source = user_data_dir() / row["stored_relpath"]
                    target = final_dir / source.name
                    if source.exists() and source.resolve() != target.resolve():
                        shutil.move(str(source), str(target))
                        moved.append((target, source))
                    relative = target.relative_to(user_data_dir()).as_posix()
                    db.execute("UPDATE note_attachments SET note_id=?,draft_id=NULL,stored_relpath=? WHERE id=?",
                               (note_id, relative, row["id"]))
                db.execute("DELETE FROM note_drafts WHERE id=?", (draft_id,))
    except Exception:
        for target, source in reversed(moved):
            source.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.move(str(target), str(source))
        raise
    return note_id


def get_note(note_id: int, path: Path | None = None) -> dict:
    with _connect(path) as db:
        row = db.execute("SELECT * FROM learning_notes WHERE id=?", (note_id,)).fetchone()
        if row is None:
            raise KeyError("笔记不存在。")
        return dict(row)


def list_library_items(*, query: str = "", category_id: int | None = None,
                       kind: str = "全部", trashed: bool = False,
                       path: Path | None = None) -> list[dict]:
    like = f"%{query.strip()}%"
    deleted = "IS NOT NULL" if trashed else "IS NULL"
    with _connect(path) as db:
        category_ids = None
        if category_id is not None:
            category_ids, frontier = {category_id}, [category_id]
            while frontier:
                children = [r[0] for r in db.execute(
                    f"SELECT id FROM note_categories WHERE parent_id IN ({','.join('?'*len(frontier))})", frontier)]
                category_ids.update(children)
                frontier = children
        params: list = []
        category_sql = ""
        if category_ids:
            category_sql = f" AND category_id IN ({','.join('?'*len(category_ids))})"
            params.extend(sorted(category_ids))
        items: list[dict] = []
        if kind in {"全部", "笔记"}:
            rows = db.execute(f"""SELECT id,title,content,origin,created_at,updated_at,
                category_id,deleted_at,'笔记' AS kind FROM learning_notes
                WHERE deleted_at {deleted} AND (title LIKE ? OR content LIKE ?){category_sql}
                ORDER BY updated_at DESC""", [like, like, *params]).fetchall()
            items.extend(dict(row) for row in rows)
        if kind in {"全部", "实验"}:
            rows = db.execute(f"""SELECT id,title,hypothesis AS content,'研究实验' AS origin,
                created_at,created_at AS updated_at,category_id,deleted_at,'实验' AS kind
                FROM experiments WHERE deleted_at {deleted} AND
                (title LIKE ? OR hypothesis LIKE ? OR notes LIKE ?){category_sql}
                ORDER BY created_at DESC""", [like, like, like, *params]).fetchall()
            items.extend(dict(row) for row in rows)
    return sorted(items, key=lambda item: item["updated_at"] or item["created_at"], reverse=True)


def trash_item(kind: str, item_id: int, path: Path | None = None) -> None:
    table = "learning_notes" if kind == "笔记" else "experiments"
    with _connect(path) as db:
        db.execute(f"UPDATE {table} SET deleted_at=? WHERE id=?", (_now(), item_id))


def set_item_category(kind: str, item_id: int, category_id: int,
                      path: Path | None = None) -> None:
    table = "learning_notes" if kind == "笔记" else "experiments"
    with _connect(path) as db:
        _category(db, category_id)
        db.execute(f"UPDATE {table} SET category_id=? WHERE id=?", (category_id, item_id))


def restore_item(kind: str, item_id: int, path: Path | None = None) -> None:
    table = "learning_notes" if kind == "笔记" else "experiments"
    with _connect(path) as db:
        db.execute(f"UPDATE {table} SET deleted_at=NULL WHERE id=?", (item_id,))


def permanent_delete_item(kind: str, item_id: int, path: Path | None = None) -> None:
    paths: list[str] = []
    with _connect(path) as db:
        if kind == "笔记":
            paths = [row[0] for row in db.execute(
                "SELECT stored_relpath FROM note_attachments WHERE note_id=?", (item_id,))]
            db.execute("DELETE FROM note_attachments WHERE note_id=?", (item_id,))
            db.execute("DELETE FROM note_drafts WHERE note_id=?", (item_id,))
            db.execute("DELETE FROM learning_notes WHERE id=? AND deleted_at IS NOT NULL", (item_id,))
        else:
            db.execute("UPDATE learning_notes SET experiment_id=NULL WHERE experiment_id=?", (item_id,))
            db.execute("DELETE FROM experiments WHERE id=? AND deleted_at IS NOT NULL", (item_id,))
    for relative in paths:
        try:
            (user_data_dir() / relative).unlink(missing_ok=True)
        except OSError:
            pass


def _validate_attachment(name: str, data: bytes) -> tuple[str, str]:
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("附件类型不在安全白名单中。")
    if not data or len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError("附件必须非空且不超过 200MB。")
    signatures = {
        ".png": b"\x89PNG", ".jpg": b"\xff\xd8", ".jpeg": b"\xff\xd8",
        ".gif": b"GIF8", ".webp": b"RIFF", ".bmp": b"BM", ".pdf": b"%PDF",
        ".doc": b"\xd0\xcf\x11\xe0", ".xls": b"\xd0\xcf\x11\xe0", ".ppt": b"\xd0\xcf\x11\xe0",
        ".docx": b"PK", ".xlsx": b"PK", ".pptx": b"PK",
    }
    signature = signatures.get(suffix)
    if signature and not data.startswith(signature):
        raise ValueError("附件内容与扩展名不匹配。")
    if suffix in {".txt", ".md", ".csv"}:
        try:
            data[:65536].decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("文本附件必须使用 UTF-8 编码。") from None
    return suffix, mimetypes.guess_type(name)[0] or "application/octet-stream"


def save_attachment(data: bytes, original_name: str, *, draft_id: str | None = None,
                    note_id: int | None = None, path: Path | None = None) -> dict:
    if (draft_id is None) == (note_id is None):
        raise ValueError("附件必须且只能关联草稿或正式笔记。")
    suffix, mime_type = _validate_attachment(original_name, data)
    with _connect(path) as db:
        where, owner = ("draft_id", draft_id) if draft_id else ("note_id", note_id)
        count, total = db.execute(
            f"SELECT COUNT(*),COALESCE(SUM(size_bytes),0) FROM note_attachments WHERE {where}=?",
            (owner,)).fetchone()
        if count >= MAX_NOTE_ATTACHMENTS or total + len(data) > MAX_NOTE_ATTACHMENT_BYTES:
            raise ValueError("每篇笔记最多 20 个附件且总大小不超过 1GB。")
    attachment_id = uuid4().hex
    owner_dir = (drafts_dir() / str(draft_id)) if draft_id else (attachments_dir() / str(note_id))
    owner_dir.mkdir(parents=True, exist_ok=True)
    target = owner_dir / f"{attachment_id}{suffix}"
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, target)
    relative = target.relative_to(user_data_dir()).as_posix()
    record = {
        "id": attachment_id, "note_id": note_id, "draft_id": draft_id,
        "original_name": Path(original_name).name, "stored_relpath": relative,
        "mime_type": mime_type, "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "created_at": _now(),
    }
    try:
        with _connect(path) as db:
            db.execute("""INSERT INTO note_attachments
                (id,note_id,draft_id,original_name,stored_relpath,mime_type,size_bytes,sha256,created_at)
                VALUES (:id,:note_id,:draft_id,:original_name,:stored_relpath,:mime_type,:size_bytes,:sha256,:created_at)""",
                record)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return record


def list_attachments(*, note_id: int | None = None, draft_id: str | None = None,
                     path: Path | None = None) -> list[dict]:
    where, owner = ("draft_id", draft_id) if draft_id else ("note_id", note_id)
    if owner is None:
        return []
    with _connect(path) as db:
        return [dict(row) for row in db.execute(
            f"SELECT * FROM note_attachments WHERE {where}=? ORDER BY created_at", (owner,))]


def attachment_bytes(attachment: dict) -> bytes:
    data = (user_data_dir() / attachment["stored_relpath"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != attachment["sha256"]:
        raise ValueError("附件校验失败。")
    return data


def export_note_zip(note_id: int, path: Path | None = None) -> bytes:
    note = get_note(note_id, path)
    attachments = list_attachments(note_id=note_id, path=path)
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("note.md", f"# {note['title']}\n\n{note['content']}\n")
        manifest = [{key: item[key] for key in ("id", "original_name", "mime_type", "size_bytes", "sha256")}
                    for item in attachments]
        archive.writestr("attachments.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for item in attachments:
            archive.writestr(f"attachments/{item['original_name']}", attachment_bytes(item))
    return output.getvalue()


def attachment_tokens(content: str) -> list[str]:
    return re.findall(r"attachment://([a-f0-9]{32})", content)
