"""Parse JSON payloads from crew task raw outputs."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
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


def _coerce_optional_str(value: Any) -> str | None:
    """Coerce crew JSON values to optional strings (LLM may return lists)."""
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if item is not None and str(item).strip()]
        return "\n".join(parts) if parts else None
    if isinstance(value, dict):
        return json.dumps(value)
    text = str(value).strip()
    return text or None


def normalize_workflow_map(
    raw: dict[str, Any] | None,
    *,
    portal_fallback: str | None = None,
) -> dict[str, str | None] | None:
    """Return WorkflowMap-compatible fields; None when workflow is absent."""
    if not raw or not isinstance(raw, dict):
        return None
    workflow = _coerce_optional_str(raw.get("workflow")) or ""
    if not workflow:
        return None
    return {
        "workflow": workflow,
        "impacted_ocf": _coerce_optional_str(raw.get("impacted_ocf")),
        "portal": _coerce_optional_str(raw.get("portal")) or portal_fallback,
        "role": _coerce_optional_str(raw.get("role")),
        "suggested_next_action": _coerce_optional_str(raw.get("suggested_next_action")),
    }


def parse_crew_outputs(raw: str, task_outputs: list[Any] | None = None) -> dict[str, Any]:
    """Merge task outputs when available; fall back to parsing final raw string."""
    result: dict[str, Any] = {}
    if task_outputs:
        keys = [
            "triage",
            "retrieve",
            "insurer_validate",
            "training",
            "respond",
            "sentiment",
            "ticket",
            "handoff",
            "copilot",
        ]
        for key, output in zip(keys, task_outputs):
            if output is None:
                continue
            raw_out = getattr(output, "raw", str(output))
            result[key] = extract_json(raw_out)
    if not result and raw:
        result["final"] = extract_json(raw)
    return result
