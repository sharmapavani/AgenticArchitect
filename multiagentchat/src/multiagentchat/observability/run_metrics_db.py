"""SQLite tables for run-level operational metrics."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from multiagentchat.audit.sqlite_db import _connect, get_db_path, init_db
from multiagentchat.observability.run_collector import StepMetricRecord

RunStatus = Literal["success", "error", "scope_refusal"]


@dataclass
class RunMetricsRecord:
    run_id: str
    session_id: str
    status: RunStatus
    duration_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    model: str
    error_message: str | None = None
    created_datetime: datetime | None = None

_RUN_METRICS_TABLE = "run_metrics"
_RUN_STEP_METRICS_TABLE = "run_step_metrics"

_CREATE_RUN_METRICS_SQL = f"""
CREATE TABLE IF NOT EXISTS {_RUN_METRICS_TABLE} (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    model TEXT,
    error_message TEXT,
    created_datetime TEXT NOT NULL
);
"""

_CREATE_RUN_STEP_METRICS_SQL = f"""
CREATE TABLE IF NOT EXISTS {_RUN_STEP_METRICS_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_type TEXT NOT NULL,
    step_name TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    FOREIGN KEY (run_id) REFERENCES {_RUN_METRICS_TABLE}(run_id)
);
"""

_CREATE_RUN_METRICS_STATUS_INDEX = f"""
CREATE INDEX IF NOT EXISTS idx_{_RUN_METRICS_TABLE}_status
ON {_RUN_METRICS_TABLE} (status);
"""

_CREATE_RUN_METRICS_DATETIME_INDEX = f"""
CREATE INDEX IF NOT EXISTS idx_{_RUN_METRICS_TABLE}_created_datetime
ON {_RUN_METRICS_TABLE} (created_datetime);
"""


def is_metrics_enabled() -> bool:
    return os.getenv("RUN_METRICS_ENABLED", "1").strip().lower() in {"1", "true", "yes"}


def init_metrics_db(db_path: Path | None = None) -> Path:
    path = init_db(db_path)
    with _connect(path) as conn:
        conn.executescript(
            _CREATE_RUN_METRICS_SQL
            + _CREATE_RUN_STEP_METRICS_SQL
            + _CREATE_RUN_METRICS_STATUS_INDEX
            + _CREATE_RUN_METRICS_DATETIME_INDEX
        )
        conn.commit()
    return path


def insert_run_metrics(record: RunMetricsRecord, db_path: Path | None = None) -> None:
    path = db_path or get_db_path()
    init_metrics_db(path)
    created = record.created_datetime or datetime.now()
    created_iso = created.replace(microsecond=0).isoformat()
    with _connect(path) as conn:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {_RUN_METRICS_TABLE} (
                run_id, session_id, status, duration_ms,
                input_tokens, output_tokens, total_tokens, cost_usd,
                model, error_message, created_datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.run_id,
                record.session_id,
                record.status,
                record.duration_ms,
                record.input_tokens,
                record.output_tokens,
                record.total_tokens,
                record.cost_usd,
                record.model,
                record.error_message,
                created_iso,
            ),
        )
        conn.commit()


def insert_run_step_metrics(
    run_id: str,
    steps: list[StepMetricRecord],
    db_path: Path | None = None,
) -> None:
    if not steps:
        return
    path = db_path or get_db_path()
    init_metrics_db(path)
    with _connect(path) as conn:
        conn.executemany(
            f"""
            INSERT INTO {_RUN_STEP_METRICS_TABLE} (
                run_id, step_type, step_name, duration_ms,
                input_tokens, output_tokens, cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    s.step_type,
                    s.step_name,
                    s.duration_ms,
                    s.input_tokens,
                    s.output_tokens,
                    s.cost_usd,
                )
                for s in steps
            ],
        )
        conn.commit()


def _row_to_run_metrics(row: sqlite3.Row) -> dict:
    return {
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "status": row["status"],
        "duration_ms": row["duration_ms"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "total_tokens": row["total_tokens"],
        "cost_usd": row["cost_usd"],
        "model": row["model"],
        "error_message": row["error_message"],
        "created_datetime": row["created_datetime"],
    }


def get_run_metrics(run_id: str, db_path: Path | None = None) -> dict | None:
    path = db_path or get_db_path()
    if not path.exists():
        return None
    init_metrics_db(path)
    with _connect(path) as conn:
        row = conn.execute(
            f"SELECT * FROM {_RUN_METRICS_TABLE} WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        result = _row_to_run_metrics(row)
        steps = conn.execute(
            f"SELECT * FROM {_RUN_STEP_METRICS_TABLE} WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        result["steps"] = [
            {
                "step_type": s["step_type"],
                "step_name": s["step_name"],
                "duration_ms": s["duration_ms"],
                "input_tokens": s["input_tokens"],
                "output_tokens": s["output_tokens"],
                "cost_usd": s["cost_usd"],
            }
            for s in steps
        ]
    return result


def query_run_metrics(
    *,
    status: str | None = None,
    since: datetime | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict]:
    path = db_path or get_db_path()
    if not path.exists():
        return []
    init_metrics_db(path)
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if since is not None:
        clauses.append("created_datetime >= ?")
        params.append(since.replace(microsecond=0).isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT * FROM {_RUN_METRICS_TABLE}
        {where}
        ORDER BY created_datetime DESC
        LIMIT ?
    """
    params.append(limit)
    with _connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_run_metrics(row) for row in rows]


def run_metrics_summary(
    *,
    since: datetime | None = None,
    limit: int = 1000,
    db_path: Path | None = None,
) -> dict:
    rows = query_run_metrics(since=since, limit=limit, db_path=db_path)
    if not rows:
        return {
            "total_runs": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0.0,
            "avg_cost_usd": 0.0,
            "total_tokens": 0,
            "by_status": {},
        }
    by_status: dict[str, int] = {}
    total_duration = 0.0
    total_cost = 0.0
    total_tokens = 0
    for row in rows:
        st = row["status"]
        by_status[st] = by_status.get(st, 0) + 1
        total_duration += float(row["duration_ms"])
        total_cost += float(row["cost_usd"])
        total_tokens += int(row["total_tokens"])
    n = len(rows)
    success = by_status.get("success", 0)
    return {
        "total_runs": n,
        "success_rate": round(success / n, 4) if n else 0.0,
        "avg_duration_ms": round(total_duration / n, 2) if n else 0.0,
        "avg_cost_usd": round(total_cost / n, 6) if n else 0.0,
        "total_tokens": total_tokens,
        "by_status": by_status,
    }
