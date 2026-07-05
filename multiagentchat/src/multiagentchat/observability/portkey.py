"""Optional Portkey gateway helpers."""

from __future__ import annotations

import os

from multiagentchat.observability.context import get_run_id, run_id_to_trace_id


def is_portkey_enabled() -> bool:
    return bool(os.getenv("PORTKEY_API_KEY") and os.getenv("PORTKEY_BASE_URL"))


def portkey_base_url() -> str | None:
    raw = os.getenv("PORTKEY_BASE_URL")
    return raw.rstrip("/") if raw else None


def portkey_headers() -> dict[str, str]:
    """Headers for Portkey hierarchical tracing tied to run_id."""
    headers: dict[str, str] = {}
    api_key = os.getenv("PORTKEY_API_KEY")
    if api_key:
        headers["x-portkey-api-key"] = api_key
    run_id = get_run_id()
    if run_id:
        headers["x-portkey-trace-id"] = run_id_to_trace_id(run_id)
    return headers
