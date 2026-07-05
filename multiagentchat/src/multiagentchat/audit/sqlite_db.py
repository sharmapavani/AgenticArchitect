"""SQLite persistence for chat audit logs."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from multiagentchat.audit.models import ChatAuditRecord

# multiagentchat/ (project root), not process cwd — keeps audit DB stable across entrypoints.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_TABLE = "chat_audit_log"

_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    session_id TEXT NOT NULL,
    user_query TEXT NOT NULL,
    api_response TEXT NOT NULL,
    portal TEXT,
    intent TEXT,
    in_scope INTEGER,
    scope_rejection_reason TEXT,
    guardrail_blocked INTEGER,
    guardrail_rule_id TEXT,
    tone_check_passed INTEGER,
    case_number TEXT,
    created_datetime TEXT NOT NULL
);
"""

_CREATE_INDEX_SQL = f"""
CREATE INDEX IF NOT EXISTS idx_{_TABLE}_session_id
ON {_TABLE} (session_id);
"""

_CREATE_RUN_ID_INDEX_SQL = f"""
CREATE UNIQUE INDEX IF NOT EXISTS idx_{_TABLE}_run_id
ON {_TABLE} (run_id)
WHERE run_id IS NOT NULL;
"""

_CREATE_DATETIME_INDEX_SQL = f"""
CREATE INDEX IF NOT EXISTS idx_{_TABLE}_created_datetime
ON {_TABLE} (created_datetime);
"""


def is_audit_enabled() -> bool:
    return os.getenv("CHAT_AUDIT_ENABLED", "1").strip().lower() in {"1", "true", "yes"}


def get_db_path() -> Path:
    raw = os.getenv("CHAT_AUDIT_DB_PATH", "./data/chat_audit.db")
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (_PROJECT_ROOT / path).resolve()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info({_TABLE})").fetchall()
    }
    if "run_id" not in columns:
        conn.execute(f"ALTER TABLE {_TABLE} ADD COLUMN run_id TEXT")
    conn.execute(_CREATE_RUN_ID_INDEX_SQL)


def init_db(db_path: Path | None = None) -> Path:
    """Create audit database file and schema if missing."""
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        conn.executescript(
            _CREATE_TABLE_SQL + _CREATE_INDEX_SQL + _CREATE_DATETIME_INDEX_SQL
        )
        _migrate_schema(conn)
        conn.commit()
    return path


def insert_audit_record(record: ChatAuditRecord, db_path: Path | None = None) -> int:
    """Insert one audit row; returns generated id."""
    path = db_path or get_db_path()
    init_db(path)
    created = record.created_datetime or datetime.now(timezone.utc)
    created_iso = created.replace(microsecond=0).isoformat()

    with _connect(path) as conn:
        cursor = conn.execute(
            f"""
            INSERT INTO {_TABLE} (
                run_id, session_id, user_query, api_response,
                portal, intent, in_scope, scope_rejection_reason,
                guardrail_blocked, guardrail_rule_id, tone_check_passed,
                case_number, created_datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.run_id,
                record.session_id,
                record.user_query,
                record.api_response,
                record.portal,
                record.intent,
                int(record.in_scope) if record.in_scope is not None else None,
                record.scope_rejection_reason,
                int(record.guardrail_blocked)
                if record.guardrail_blocked is not None
                else None,
                record.guardrail_rule_id,
                int(record.tone_check_passed)
                if record.tone_check_passed is not None
                else None,
                record.case_number,
                created_iso,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _row_to_record(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "user_query": row["user_query"],
        "api_response": row["api_response"],
        "portal": row["portal"],
        "intent": row["intent"],
        "in_scope": bool(row["in_scope"]) if row["in_scope"] is not None else None,
        "scope_rejection_reason": row["scope_rejection_reason"],
        "guardrail_blocked": bool(row["guardrail_blocked"])
        if row["guardrail_blocked"] is not None
        else None,
        "guardrail_rule_id": row["guardrail_rule_id"],
        "tone_check_passed": bool(row["tone_check_passed"])
        if row["tone_check_passed"] is not None
        else None,
        "case_number": row["case_number"],
        "created_datetime": row["created_datetime"],
    }


def query_audit_records(
    *,
    session_id: str | None = None,
    run_id: str | None = None,
    limit: int = 50,
    since: datetime | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Return audit rows newest-first."""
    path = db_path or get_db_path()
    if not path.exists():
        return []

    clauses: list[str] = []
    params: list[object] = []

    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if since is not None:
        clauses.append("created_datetime >= ?")
        params.append(since.replace(microsecond=0).isoformat())

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT * FROM {_TABLE}
        {where}
        ORDER BY created_datetime DESC, id DESC
        LIMIT ?
    """
    params.append(limit)

    with _connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_record(row) for row in rows]


def get_audit_record(record_id: int, db_path: Path | None = None) -> dict | None:
    path = db_path or get_db_path()
    if not path.exists():
        return None
    with _connect(path) as conn:
        row = conn.execute(
            f"SELECT * FROM {_TABLE} WHERE id = ?", (record_id,)
        ).fetchone()
    return _row_to_record(row) if row else None


def get_audit_record_by_run_id(run_id: str, db_path: Path | None = None) -> dict | None:
    rows = query_audit_records(run_id=run_id, limit=1, db_path=db_path)
    return rows[0] if rows else None


def get_schema_ddl(db_path: Path | None = None) -> str:
    path = db_path or get_db_path()
    if not path.exists():
        init_db(path)
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?",
            (_TABLE,),
        ).fetchall()
    return "\n".join(row[0] for row in rows if row[0])
