"""Span helpers with run_id / session_id attributes."""

from __future__ import annotations

import secrets
from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, Status, StatusCode, TraceFlags

from multiagentchat.observability.context import (
    get_run_id,
    get_session_id,
    run_id_to_trace_id,
)
from multiagentchat.observability.otel import get_tracer


def _base_attrs(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    run_id = get_run_id()
    session_id = get_session_id()
    if run_id:
        attrs["run_id"] = run_id
    if session_id:
        attrs["session_id"] = session_id
    if extra:
        attrs.update(extra)
    return attrs


def _trace_context_from_run_id(run_id: str) -> SpanContext:
    trace_id = int(run_id_to_trace_id(run_id), 16)
    span_id = int(secrets.token_hex(8), 16)
    return SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


@contextmanager
def start_root_span(
    name: str,
    *,
    run_id: str,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Start a root span whose trace_id is derived from run_id."""
    tracer = get_tracer()
    parent_ctx = trace.set_span_in_context(NonRecordingSpan(_trace_context_from_run_id(run_id)))
    with tracer.start_as_current_span(
        name,
        context=parent_ctx,
        attributes=_base_attrs(attributes),
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


@contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Start a child span with correlation attributes."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name, attributes=_base_attrs(attributes)) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def set_span_attributes(attributes: dict[str, Any]) -> None:
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)


def record_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=_base_attrs(attributes))
