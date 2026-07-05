"""Wall-clock timing for CrewAI kickoff and per-task completion callbacks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from crewai.tasks.task_output import TaskOutput
from opentelemetry.trace import Span

from multiagentchat.observability.metrics import ingest_crew_token_usage, record_step
from multiagentchat.observability.otel import get_tracer
from multiagentchat.observability.spans import set_span_attributes
from multiagentchat.utils.progress_emitter import ProgressEmitter, envelope

logger = logging.getLogger("multiagentchat.crew")

TASK_LABELS = [
    "triage_task",
    "retrieve_task",
    "insurer_validate_task",
    "training_task",
    "respond_task",
    "sentiment_task",
    "ticket_task",
    "handoff_task",
    "copilot_task",
]


@dataclass
class TaskTimingRecord:
    index: int
    label: str
    agent: str
    duration_s: float
    cumulative_s: float
    completed_at: str
    output_name: str | None
    raw_chars: int


@dataclass
class _ActiveTaskSpan:
    span: Span
    started: float


@dataclass
class CrewTimingTracker:
    """Records per-task durations via Crew.task_callback (between completions)."""

    run_id: str = ""
    session_id: str = ""
    message_preview: str = ""
    task_manifest: list[dict[str, str]] = field(default_factory=list)
    emit: ProgressEmitter | None = None
    _kickoff_started: float = field(default=0.0, repr=False)
    _last_mark: float = field(default=0.0, repr=False)
    records: list[TaskTimingRecord] = field(default_factory=list)
    _active_tasks: dict[int, _ActiveTaskSpan] = field(default_factory=dict, repr=False)

    def _manifest_entry(self, index: int) -> dict[str, str] | None:
        if 0 <= index < len(self.task_manifest):
            return self.task_manifest[index]
        return None

    def _start_task_span(self, index: int) -> None:
        entry = self._manifest_entry(index)
        if entry is None:
            return
        task_id = entry["task_id"]
        agent_id = entry["agent_id"]
        tracer = get_tracer()
        span = tracer.start_span(
            f"crew.task.{task_id}",
            attributes={
                "crew.task_id": task_id,
                "crew.agent_id": agent_id,
                "run_id": self.run_id or None,
                "session_id": self.session_id or None,
            },
        )
        self._active_tasks[index] = _ActiveTaskSpan(span=span, started=perf_counter())

    def _finish_task_span(self, index: int, task_id: str, duration_s: float) -> None:
        active = self._active_tasks.pop(index, None)
        if active is None:
            record_step("crew", task_id, duration_s)
            return
        span = active.span
        if span.is_recording():
            span.set_attribute("crew.duration_s", duration_s)
            span.end()
        record_step("crew", task_id, duration_s)

    def _emit_agent_task(
        self,
        index: int,
        status: str,
        *,
        duration_s: float | None = None,
        cumulative_s: float | None = None,
    ) -> None:
        if status == "started":
            self._start_task_span(index)
        if self.emit is None:
            return
        entry = self._manifest_entry(index)
        if entry is None:
            return
        event: dict[str, Any] = {
            "type": "agent_task",
            "task_id": entry["task_id"],
            "agent_id": entry["agent_id"],
            "label": entry["label"],
            "index": index,
            "total": len(self.task_manifest),
            "status": status,
            "summary": entry["label"],
        }
        if duration_s is not None:
            event["duration_s"] = duration_s
        if cumulative_s is not None:
            event["cumulative_s"] = cumulative_s
        if self.run_id and self.session_id:
            event = envelope(event, run_id=self.run_id, session_id=self.session_id)
        self.emit(event)

    def mark_kickoff_start(self) -> None:
        now = perf_counter()
        self._kickoff_started = now
        self._last_mark = now
        preview = self.message_preview[:80].replace("\n", " ")
        logger.info(
            "crew.kickoff START run_id=%s session_id=%s message=%r",
            self.run_id,
            self.session_id,
            preview,
        )
        if self.task_manifest:
            self._emit_agent_task(0, "started")

    def on_task_complete(self, output: TaskOutput) -> None:
        """Crew.task_callback — fired after each task finishes."""
        now = perf_counter()
        if self._kickoff_started == 0.0:
            self.mark_kickoff_start()

        duration = now - self._last_mark
        cumulative = now - self._kickoff_started
        self._last_mark = now

        index = len(self.records)
        label = TASK_LABELS[index] if index < len(TASK_LABELS) else f"task_{index}"
        agent = getattr(output, "agent", "?") or "?"
        name = getattr(output, "name", None)
        raw = getattr(output, "raw", "") or ""
        completed_at = datetime.now(timezone.utc).isoformat()

        entry = self._manifest_entry(index)
        task_id = entry["task_id"] if entry else label
        agent_id = entry["agent_id"] if entry else agent

        self._finish_task_span(index, task_id, duration)

        record = TaskTimingRecord(
            index=index,
            label=label,
            agent=agent,
            duration_s=duration,
            cumulative_s=cumulative,
            completed_at=completed_at,
            output_name=name,
            raw_chars=len(raw),
        )
        self.records.append(record)

        self._emit_agent_task(
            index,
            "completed",
            duration_s=duration,
            cumulative_s=cumulative,
        )
        next_index = index + 1
        if next_index < len(self.task_manifest):
            self._emit_agent_task(next_index, "started")

        logger.info(
            "crew.task DONE #%d %s agent=%s duration=%.2fs cumulative=%.2fs "
            "run_id=%s session_id=%s completed_at=%s raw_chars=%d output_name=%r",
            record.index + 1,
            record.label,
            record.agent,
            record.duration_s,
            record.cumulative_s,
            self.run_id,
            self.session_id,
            record.completed_at,
            record.raw_chars,
            record.output_name,
        )

    def log_summary(self, result: Any, total_elapsed_s: float) -> None:
        """Log kickoff totals and inspect result.tasks_output metadata."""
        task_outputs: list[Any] = getattr(result, "tasks_output", None) or []
        token_usage = getattr(result, "token_usage", None)

        logger.info(
            "crew.kickoff END run_id=%s session_id=%s total=%.2fs tasks=%d",
            self.run_id,
            self.session_id,
            total_elapsed_s,
            len(task_outputs),
        )

        ingest_crew_token_usage(result)

        if token_usage is not None:
            logger.debug("crew.token_usage: %s", token_usage)
            usage_attrs: dict[str, Any] = {}
            if hasattr(token_usage, "prompt_tokens"):
                usage_attrs["gen_ai.usage.input_tokens"] = token_usage.prompt_tokens
            if hasattr(token_usage, "completion_tokens"):
                usage_attrs["gen_ai.usage.output_tokens"] = token_usage.completion_tokens
            if hasattr(token_usage, "total_tokens"):
                usage_attrs["gen_ai.usage.total_tokens"] = token_usage.total_tokens
            if isinstance(token_usage, dict):
                usage_attrs["gen_ai.usage.input_tokens"] = token_usage.get("prompt_tokens")
                usage_attrs["gen_ai.usage.output_tokens"] = token_usage.get("completion_tokens")
            set_span_attributes({k: v for k, v in usage_attrs.items() if v is not None})

        for active in self._active_tasks.values():
            if active.span.is_recording():
                active.span.end()
        self._active_tasks.clear()
