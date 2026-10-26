"""Persistent, scope-isolated DeepSeek conversations and final-answer messages."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4

from quant_lab.deepseek import safe_context
from quant_lab.security import redact
from quant_lab.storage import _connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def conversation_title(question: str) -> str:
    first = next((line.strip() for line in question.splitlines() if line.strip()), "新对话")
    return re.sub(r"\s+", " ", first)[:80]


def create_conversation(scope: str, context: dict | None = None, *, title: str = "新对话",
                        path: Path | None = None, conversation_id: str | None = None) -> dict:
    conversation_id = conversation_id or uuid4().hex
    now = _now()
    safe = safe_context(context)
    with _connect(path) as db:
        db.execute(
            """INSERT INTO ai_conversations
               (id,title,scope,context_json,created_at,updated_at,opened_at)
               VALUES (?,?,?,?,?,?,?)""",
            (conversation_id, conversation_title(title), scope,
             json.dumps(safe, ensure_ascii=False), now, now, now),
        )
    return get_conversation(conversation_id, path)


def get_conversation(conversation_id: str, path: Path | None = None) -> dict:
    with _connect(path) as db:
        row = db.execute("SELECT * FROM ai_conversations WHERE id=?", (conversation_id,)).fetchone()
    if row is None:
        raise KeyError("对话不存在。")
    result = dict(row)
    result["context"] = safe_context(json.loads(result.pop("context_json") or "{}"))
    return result


def latest_conversation(scope: str, path: Path | None = None) -> dict | None:
    with _connect(path) as db:
        row = db.execute(
            "SELECT id FROM ai_conversations WHERE scope=? ORDER BY opened_at DESC,updated_at DESC LIMIT 1",
            (scope,),
        ).fetchone()
    return get_conversation(row["id"], path) if row else None


def list_conversations(query: str = "", path: Path | None = None) -> list[dict]:
    like = f"%{query.strip()}%"
    with _connect(path) as db:
        rows = db.execute(
            """SELECT c.*,COUNT(m.id) AS message_count
               FROM ai_conversations c LEFT JOIN ai_messages m ON m.conversation_id=c.id
               WHERE c.title LIKE ? OR EXISTS (
                   SELECT 1 FROM ai_messages searched
                   WHERE searched.conversation_id=c.id AND searched.content LIKE ?
               )
               GROUP BY c.id ORDER BY c.updated_at DESC""",
            (like, like),
        ).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        item["context"] = safe_context(json.loads(item.pop("context_json") or "{}"))
        output.append(item)
    return output


def touch_conversation(conversation_id: str, path: Path | None = None) -> None:
    with _connect(path) as db:
        if not db.execute("SELECT 1 FROM ai_conversations WHERE id=?", (conversation_id,)).fetchone():
            raise KeyError("对话不存在。")
        db.execute("UPDATE ai_conversations SET opened_at=? WHERE id=?", (_now(), conversation_id))


def rename_conversation(conversation_id: str, title: str, path: Path | None = None) -> None:
    value = conversation_title(title)
    if value == "新对话" and not title.strip():
        raise ValueError("对话标题不能为空。")
    with _connect(path) as db:
        cursor = db.execute(
            "UPDATE ai_conversations SET title=?,updated_at=? WHERE id=?",
            (redact(value), _now(), conversation_id),
        )
        if cursor.rowcount != 1:
            raise KeyError("对话不存在。")


def delete_conversation(conversation_id: str, path: Path | None = None) -> None:
    with _connect(path) as db:
        cursor = db.execute("DELETE FROM ai_conversations WHERE id=?", (conversation_id,))
        if cursor.rowcount != 1:
            raise KeyError("对话不存在。")


def add_message(conversation_id: str, *, turn_id: str, role: str, content: str,
                kind: str = "chat", model: str = "", requested_model: str = "",
                security: str = "", complete: bool = True, finish_reason: str | None = None,
                error: str | None = None, context: dict | None = None,
                saved_note_id: int | None = None, secrets=(), path: Path | None = None,
                message_id: str | None = None) -> dict:
    if role not in {"user", "assistant"}:
        raise ValueError("对话消息角色无效。")
    value = redact(content, secrets).strip()
    if not value:
        raise ValueError("对话消息不能为空。")
    message_id = message_id or uuid4().hex
    now = _now()
    safe = safe_context(context)
    with _connect(path) as db:
        conversation = db.execute(
            "SELECT title FROM ai_conversations WHERE id=?", (conversation_id,)
        ).fetchone()
        if conversation is None:
            raise KeyError("对话不存在。")
        db.execute(
            """INSERT INTO ai_messages
               (id,conversation_id,turn_id,role,kind,content,model,requested_model,
                security,complete,finish_reason,error,context_json,saved_note_id,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (message_id, conversation_id, turn_id, role, kind, value,
             redact(model, secrets), redact(requested_model, secrets), redact(security, secrets),
             int(complete), finish_reason, redact(error or "", secrets) or None,
             json.dumps(safe, ensure_ascii=False), saved_note_id, now),
        )
        title = conversation["title"]
        if role == "user" and title == "新对话":
            title = conversation_title(value)
        db.execute(
            "UPDATE ai_conversations SET title=?,updated_at=?,opened_at=? WHERE id=?",
            (title, now, now, conversation_id),
        )
    return get_message(message_id, path)


def get_message(message_id: str, path: Path | None = None) -> dict:
    with _connect(path) as db:
        row = db.execute(
            """SELECT m.*,c.scope FROM ai_messages m
               JOIN ai_conversations c ON c.id=m.conversation_id WHERE m.id=?""",
            (message_id,),
        ).fetchone()
    if row is None:
        raise KeyError("对话消息不存在。")
    return _decode_message(row)


def list_messages(conversation_id: str, path: Path | None = None) -> list[dict]:
    with _connect(path) as db:
        rows = db.execute(
            """SELECT m.*,c.scope FROM ai_messages m
               JOIN ai_conversations c ON c.id=m.conversation_id
               WHERE m.conversation_id=? ORDER BY m.rowid""",
            (conversation_id,),
        ).fetchall()
    return [_decode_message(row) for row in rows]


def update_message(message_id: str, *, content: str | None = None,
                   complete: bool | None = None, finish_reason: str | None = None,
                   error: str | None = None, saved_note_id: int | None = None,
                   secrets=(), path: Path | None = None) -> None:
    assignments, values = [], []
    if content is not None:
        assignments.append("content=?")
        values.append(redact(content, secrets))
    if complete is not None:
        assignments.append("complete=?")
        values.append(int(complete))
    if finish_reason is not None:
        assignments.append("finish_reason=?")
        values.append(finish_reason)
    if error is not None:
        assignments.append("error=?")
        values.append(redact(error, secrets) or None)
    if saved_note_id is not None:
        assignments.append("saved_note_id=?")
        values.append(saved_note_id)
    if not assignments:
        return
    values.append(message_id)
    with _connect(path) as db:
        row = db.execute("SELECT conversation_id FROM ai_messages WHERE id=?", (message_id,)).fetchone()
        if row is None:
            raise KeyError("对话消息不存在。")
        db.execute(f"UPDATE ai_messages SET {','.join(assignments)} WHERE id=?", values)
        db.execute("UPDATE ai_conversations SET updated_at=? WHERE id=?", (_now(), row["conversation_id"]))


def _decode_message(row) -> dict:
    item = dict(row)
    item["complete"] = bool(item["complete"])
    item["context"] = safe_context(json.loads(item.pop("context_json") or "{}"))
    item["question"] = ""
    return item
