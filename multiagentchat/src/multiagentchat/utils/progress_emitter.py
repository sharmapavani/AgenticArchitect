"""Progress event helpers for SSE streaming."""

from __future__ import annotations

from typing import Callable

from multiagentchat.schemas.progress import FLOW_STEP_SUMMARIES

ProgressEmitter = Callable[[dict], None]


def envelope(
    event: dict,
    *,
    run_id: str,
    session_id: str,
) -> dict:
    """Attach correlation ids to every product observability event."""
    return {
        **event,
        "run_id": run_id,
        "session_id": session_id,
    }


def emit_run_started(
    emit: ProgressEmitter | None,
    *,
    run_id: str,
    session_id: str,
    message: str = "Processing your request…",
) -> None:
    if emit is None:
        return
    emit(
        envelope(
            {"type": "run_started", "message": message},
            run_id=run_id,
            session_id=session_id,
        )
    )


def emit_flow_step(
    emit: ProgressEmitter | None,
    step: str,
    status: str,
    *,
    run_id: str = "",
    session_id: str = "",
) -> None:
    if emit is None:
        return
    summary = FLOW_STEP_SUMMARIES.get(step, step.replace("_", " ").title())
    event = {
        "type": "flow_step",
        "step": step,
        "status": status,
        "summary": summary,
    }
    if run_id and session_id:
        event = envelope(event, run_id=run_id, session_id=session_id)
    emit(event)


def emit_pipeline(
    emit: ProgressEmitter | None,
    tasks: list[dict[str, str]],
    *,
    run_id: str = "",
    session_id: str = "",
) -> None:
    if emit is None:
        return
    event = {
        "type": "pipeline",
        "total_tasks": len(tasks),
        "tasks": [
            {
                "task_id": t["task_id"],
                "agent_id": t["agent_id"],
                "label": t["label"],
            }
            for t in tasks
        ],
    }
    if run_id and session_id:
        event = envelope(event, run_id=run_id, session_id=session_id)
    emit(event)
