"""Task guardrails for triage and respond tasks."""

from __future__ import annotations

import json
import re
from typing import Any

from crewai.tasks.task_output import TaskOutput


def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"raw": text}


def triage_guardrail(output: TaskOutput):
    """Validate triage output contains required scope fields."""
    try:
        payload = _extract_json(output.raw)
        if "in_scope" not in payload:
            return False, "Missing in_scope field in triage output"
        if not payload.get("in_scope") and not payload.get("scope_rejection_reason"):
            return False, "Out-of-scope triage must include scope_rejection_reason"
        return True, output
    except Exception as exc:
        return False, f"Triage output must be valid JSON: {exc}"


def respond_guardrail(output: TaskOutput):
    """Validate response output has answer and audit fields."""
    try:
        payload = _extract_json(output.raw)
        if not payload.get("answer"):
            return False, "Response must include answer field"
        confidence = payload.get("confidence", 0)
        citations = payload.get("citations", [])
        answer_lower = payload.get("answer", "").lower()
        ocf_terms = ("ocf", "form 1", "adjudic", "submission")
        mentions_ocf = any(term in answer_lower for term in ocf_terms)
        if mentions_ocf and not citations:
            return False, "OCF guidance requires at least one citation"
        if confidence < 0.3 and mentions_ocf:
            return False, "Low confidence OCF guidance blocked"
        return True, output
    except Exception as exc:
        return False, f"Response output must be valid JSON: {exc}"
