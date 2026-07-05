"""Pydantic models for chat audit records."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatAuditRecord(BaseModel):
    """One persisted chat interaction for compliance / auditing."""

    id: int | None = None
    run_id: str | None = None
    session_id: str
    user_query: str
    api_response: str
    portal: str | None = None
    intent: str | None = None
    in_scope: bool | None = None
    scope_rejection_reason: str | None = None
    guardrail_blocked: bool | None = None
    guardrail_rule_id: str | None = None
    tone_check_passed: bool | None = None
    case_number: str | None = None
    created_datetime: datetime | None = None


class ChatAuditQuery(BaseModel):
    """Filters for querying audit logs."""

    session_id: str | None = None
    run_id: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    since: datetime | None = None
