"""Request-scoped correlation context (run_id, session_id)."""

from __future__ import annotations

import contextvars
from typing import Iterator
from contextlib import contextmanager

_run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "run_id", default=None
)
_session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)


def run_id_to_trace_id(run_id: str) -> str:
    """Map UUID run_id to 32-char hex OTel / Portkey trace id."""
    return run_id.replace("-", "").lower()


def get_run_id() -> str | None:
    return _run_id_var.get()


def get_session_id() -> str | None:
    return _session_id_var.get()


@contextmanager
def bind_run_context(
    *,
    run_id: str,
    session_id: str,
) -> Iterator[None]:
    """Bind correlation ids for the current async/thread context."""
    run_token = _run_id_var.set(run_id)
    session_token = _session_id_var.set(session_id)
    try:
        yield
    finally:
        _run_id_var.reset(run_token)
        _session_id_var.reset(session_token)
