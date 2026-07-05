"""MCP server exposing SQLite chat audit tools for agents and compliance review."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from multiagentchat.audit.models import ChatAuditRecord
from multiagentchat.audit.sqlite_db import (
    get_audit_record,
    get_schema_ddl,
    init_db,
    insert_audit_record,
    query_audit_records,
)
from multiagentchat.observability.run_metrics_db import (
    get_run_metrics as fetch_run_metrics,
    init_metrics_db,
    is_metrics_enabled,
    query_run_metrics as fetch_run_metrics_query,
    run_metrics_summary as compute_run_metrics_summary,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env")

mcp = FastMCP("Chat Audit")


@mcp.resource("audit://schema")
def audit_schema() -> str:
    """SQLite DDL for the chat_audit_log table."""
    init_db()
    return get_schema_ddl()


@mcp.tool()
def log_chat_audit(
    session_id: str,
    user_query: str,
    api_response: str,
    run_id: str | None = None,
    portal: str | None = None,
    intent: str | None = None,
    in_scope: bool | None = None,
    scope_rejection_reason: str | None = None,
    guardrail_blocked: bool | None = None,
    guardrail_rule_id: str | None = None,
    tone_check_passed: bool | None = None,
    case_number: str | None = None,
) -> dict:
    """Log a user query and API response to the SQLite audit store."""
    record = ChatAuditRecord(
        run_id=run_id,
        session_id=session_id,
        user_query=user_query,
        api_response=api_response,
        portal=portal,
        intent=intent,
        in_scope=in_scope,
        scope_rejection_reason=scope_rejection_reason,
        guardrail_blocked=guardrail_blocked,
        guardrail_rule_id=guardrail_rule_id,
        tone_check_passed=tone_check_passed,
        case_number=case_number,
    )
    record_id = insert_audit_record(record)
    return {"id": record_id, "status": "logged", "run_id": run_id, "session_id": session_id}


@mcp.tool()
def query_chat_audit(
    session_id: str | None = None,
    run_id: str | None = None,
    limit: int = 50,
    since: str | None = None,
) -> list[dict]:
    """Query chat audit logs (newest first). Filter by session_id, run_id, or ISO since timestamp."""
    since_dt = datetime.fromisoformat(since) if since else None
    return query_audit_records(session_id=session_id, run_id=run_id, limit=limit, since=since_dt)


@mcp.tool()
def get_chat_audit_by_run_id(run_id: str) -> dict | None:
    """Fetch a single audit record by run_id."""
    from multiagentchat.audit.sqlite_db import get_audit_record_by_run_id

    return get_audit_record_by_run_id(run_id)


@mcp.tool()
def get_chat_audit_by_id(record_id: int) -> dict | None:
    """Fetch a single audit record by id."""
    return get_audit_record(record_id)


@mcp.tool()
def audit_summary(session_id: str | None = None, limit: int = 20) -> str:
    """Human-readable summary of recent audit entries for compliance review."""
    rows = query_audit_records(session_id=session_id, limit=limit)
    if not rows:
        return "No audit records found."
    lines = [f"Showing {len(rows)} audit record(s):"]
    for row in rows:
        lines.append(
            f"- [{row['created_datetime']}] id={row['id']} run_id={row.get('run_id')} "
            f"session={row['session_id']} "
            f"in_scope={row['in_scope']} intent={row['intent']!r} "
            f"query={row['user_query'][:120]!r}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_run_metrics(run_id: str) -> dict | None:
    """Fetch per-run operational metrics rollup and step breakdown by run_id."""
    return fetch_run_metrics(run_id)


@mcp.tool()
def query_run_metrics(
    status: str | None = None,
    since: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Query run_metrics rows (newest first). Filter by status and/or ISO since timestamp."""
    since_dt = datetime.fromisoformat(since) if since else None
    return fetch_run_metrics_query(status=status, since=since_dt, limit=limit)


@mcp.tool()
def run_metrics_summary(since: str | None = None, limit: int = 1000) -> dict:
    """Aggregate success rate, avg latency, avg cost, and token totals over recent runs."""
    since_dt = datetime.fromisoformat(since) if since else None
    return compute_run_metrics_summary(since=since_dt, limit=limit)


def main() -> None:
    if os.getenv("CHAT_AUDIT_AUTO_INIT", "1").strip().lower() in {"1", "true", "yes"}:
        init_db()
    if is_metrics_enabled():
        init_metrics_db()
    mcp.run()


if __name__ == "__main__":
    main()
