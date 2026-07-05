"""SQLite persistence for per-run operational metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from multiagentchat.observability.run_collector import RunMetricsCollector
from multiagentchat.observability.run_metrics_db import (
    RunMetricsRecord,
    insert_run_metrics,
    insert_run_step_metrics,
    is_metrics_enabled,
)

RunStatus = Literal["success", "error", "scope_refusal"]


def persist_run_metrics(
    collector: RunMetricsCollector,
    *,
    status: RunStatus,
    duration_ms: float | None = None,
    error_message: str | None = None,
) -> None:
    if not is_metrics_enabled():
        return
    record = RunMetricsRecord(
        run_id=collector.run_id,
        session_id=collector.session_id,
        status=status,
        duration_ms=duration_ms if duration_ms is not None else collector.elapsed_ms(),
        input_tokens=collector.input_tokens,
        output_tokens=collector.output_tokens,
        total_tokens=collector.total_tokens,
        cost_usd=collector.cost_usd,
        model=collector.model,
        error_message=error_message,
        created_datetime=datetime.now(timezone.utc),
    )
    insert_run_metrics(record)
    if collector.steps:
        insert_run_step_metrics(collector.run_id, collector.steps)
