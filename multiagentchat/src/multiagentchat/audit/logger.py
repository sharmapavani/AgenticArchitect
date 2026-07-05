"""High-level audit logger used by the FastAPI gateway."""

from __future__ import annotations

import json
import logging

from multiagentchat.audit.models import ChatAuditRecord
from multiagentchat.audit.sqlite_db import insert_audit_record, is_audit_enabled
from multiagentchat.schemas.chat import ChatRequest, ChatResponse

_log = logging.getLogger(__name__)


def log_chat_exchange(request: ChatRequest, response: ChatResponse) -> int | None:
    """Persist user query and API response when audit is enabled."""
    if not is_audit_enabled():
        return None

    try:
        record = ChatAuditRecord(
            run_id=response.run_id or None,
            session_id=response.session_id,
            user_query=request.message.strip(),
            api_response=json.dumps(response.model_dump(mode="json"), ensure_ascii=False),
            portal=response.portal,
            intent=response.intent,
            in_scope=response.in_scope,
            scope_rejection_reason=response.scope_refusal_reason,
            guardrail_blocked=response.guardrail_blocked,
            guardrail_rule_id=response.guardrail_rule_id,
            tone_check_passed=response.tone_check_passed,
            case_number=response.case_number,
        )
        record_id = insert_audit_record(record)
        _log.debug(
            "audit logged id=%s run_id=%s session=%s",
            record_id,
            response.run_id,
            response.session_id,
        )
        return record_id
    except Exception:
        _log.exception("failed to write chat audit log")
        return None
