"""Small learning records in the existing archive; no financial inputs rewritten."""

from datetime import datetime, timezone
import json
import math

from quant_lab.storage import _connect, database_path
from quant_lab.security import redact


KINDS = {"task", "guide", "course", "experiment", "goal", "onboarding"}


def load_progress(path=None) -> dict:
    if not (path or database_path()).exists():
        return {}
    with _connect(path) as db:
        return {(row["kind"], row["item_id"]): {"status": row["status"],
                "details": json.loads(row["details_json"]), "updated_at": row["updated_at"]}
                for row in db.execute("SELECT * FROM learning_progress")}


def save_progress(kind, item_id, details=None, *, status="completed", path=None, secrets=()):
    if kind not in KINDS or not item_id or len(item_id) > 100 or status not in {"completed", "in_progress", "skipped"}:
        raise ValueError("学习记录类型或状态无效。")
    # Callers pass only evidence identifiers or explicit user-authored goals.
    encoded = redact(json.dumps(details or {}, ensure_ascii=False, allow_nan=False), secrets)
    if len(encoded) > 4000:
        raise ValueError("学习记录过长。")
    with _connect(path) as db:
        db.execute("""INSERT INTO learning_progress VALUES (?,?,?,?,?)
            ON CONFLICT(kind,item_id) DO UPDATE SET status=excluded.status,
            details_json=excluded.details_json,updated_at=excluded.updated_at""",
            (kind, redact(item_id, secrets), status, encoded, datetime.now(timezone.utc).isoformat()))


def save_quiz_attempt(course_id, answer, correct, *, path=None):
    if not course_id or not math.isfinite(float(answer)) or type(correct) is not bool:
        raise ValueError("测验记录无效。")
    with _connect(path) as db:
        cursor = db.execute("INSERT INTO learning_quiz_attempts(course_id,answer,correct,created_at) VALUES (?,?,?,?)",
            (course_id, float(answer), int(correct), datetime.now(timezone.utc).isoformat()))
        return cursor.lastrowid


def quiz_attempts(path=None):
    if not (path or database_path()).exists():
        return []
    with _connect(path) as db:
        return [dict(row) for row in db.execute("SELECT * FROM learning_quiz_attempts ORDER BY id DESC LIMIT 200")]


def reset_progress(path=None):
    """Reset only progress/quizzes, keeping research inputs, notes and settings."""
    with _connect(path) as db:
        db.execute("DELETE FROM learning_progress WHERE NOT(kind='onboarding' AND item_id='welcome')")
        db.execute("DELETE FROM learning_quiz_attempts")
