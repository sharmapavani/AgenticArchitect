"""Pydantic schemas for MultiAgentChat API and Flow state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    url: str
    title: str


class WorkflowMap(BaseModel):
    workflow: str
    impacted_ocf: str | None = None
    portal: str | None = None
    role: str | None = None
    suggested_next_action: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: Literal["en", "fr", "auto"] = "auto"
    portal_hint: Literal["facilities", "insurers", "pms_vendors"] | None = None
    channel: Literal["chat"] = "chat"
    skip_rag: bool = False
    is_session_start: bool = False
    conversation_history: list[dict[str, str]] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    workflow_map: WorkflowMap | None = None
    confidence: float = 0.0
    translated_from_en: bool = False
    escalate: bool = False
    case_number: str | None = None
    session_id: str
    run_id: str = ""
    in_scope: bool = True
    scope_refusal_reason: str | None = None
    guardrail_blocked: bool = False
    guardrail_rule_id: str | None = None
    tone_check_passed: bool = True
    greeting_included: bool = False
    intent: str | None = None
    portal: str | None = None


class TriageOutput(BaseModel):
    portal: Literal["facilities", "insurers", "pms_vendors"] = "facilities"
    language: Literal["en", "fr"] = "en"
    intent: Literal[
        "user_management",
        "ocf_submission",
        "ocf_adjudication",
        "general",
    ] = "general"
    channel: str = "chat"
    urgency: Literal["low", "medium", "high"] = "medium"
    in_scope: bool = True
    scope_rejection_reason: str | None = None


class CAIFlowState(BaseModel):
    session_id: str = ""
    run_id: str = ""
    message: str = ""
    language: Literal["en", "fr", "auto"] = "auto"
    portal_hint: Literal["facilities", "insurers", "pms_vendors"] | None = None
    skip_rag: bool = False
    is_session_start: bool = False
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    greeting_text: str | None = None
    in_scope: bool = True
    scope_rejection_reason: str | None = None
    crew_raw: str = ""
    chat_response: ChatResponse | None = None
