"""OpenTelemetry metric instruments and recording helpers."""

from __future__ import annotations

import os
from typing import Literal

from opentelemetry import metrics

from multiagentchat.observability.otel import is_otel_enabled
from multiagentchat.observability.pricing import compute_cost_usd
from multiagentchat.observability.run_collector import RunMetricsCollector, get_run_collector

StepType = Literal["flow", "crew", "tool", "llm"]
RunStatus = Literal["success", "error", "scope_refusal"]
Scope = Literal["run", "step"]

_meter = None
_request_duration = None
_step_duration = None
_tokens_input = None
_tokens_output = None
_tokens_total = None
_cost_usd = None
_runs_total = None


def _init_instruments() -> None:
    global _meter, _request_duration, _step_duration
    global _tokens_input, _tokens_output, _tokens_total, _cost_usd, _runs_total
    if _meter is not None or not is_otel_enabled():
        return
    _meter = metrics.get_meter("multiagentchat.metrics")
    _request_duration = _meter.create_histogram(
        "chat.request.duration",
        description="Server-side end-to-end chat request duration",
        unit="s",
    )
    _step_duration = _meter.create_histogram(
        "chat.step.duration",
        description="Duration of flow, crew, tool, or LLM steps",
        unit="s",
    )
    _tokens_input = _meter.create_counter(
        "chat.tokens.input",
        description="Input tokens consumed",
    )
    _tokens_output = _meter.create_counter(
        "chat.tokens.output",
        description="Output tokens consumed",
    )
    _tokens_total = _meter.create_counter(
        "chat.token.usage",
        description="Total tokens consumed",
    )
    _cost_usd = _meter.create_counter(
        "chat.cost.usd",
        description="Estimated USD cost",
    )
    _runs_total = _meter.create_counter(
        "chat.runs.total",
        description="Chat run outcomes",
    )


def _default_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def record_request(duration_s: float, route: str, status: RunStatus) -> None:
    _init_instruments()
    if _request_duration is not None:
        _request_duration.record(duration_s, {"route": route, "status": status})


def record_step(step_type: StepType, step_name: str, duration_s: float) -> None:
    _init_instruments()
    if _step_duration is not None:
        _step_duration.record(duration_s, {"step_type": step_type, "step_name": step_name})
    collector = get_run_collector()
    if collector is not None:
        collector.record_step(step_type, step_name, duration_s)


def record_tokens(
    *,
    scope: Scope,
    step_name: str,
    model: str | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    _init_instruments()
    resolved_model = model or _default_model()
    total = input_tokens + output_tokens
    attrs = {"scope": scope, "step_name": step_name, "model": resolved_model}
    if _tokens_input is not None:
        _tokens_input.add(input_tokens, attrs)
    if _tokens_output is not None:
        _tokens_output.add(output_tokens, attrs)
    if _tokens_total is not None:
        _tokens_total.add(total, attrs)
    cost = compute_cost_usd(resolved_model, input_tokens, output_tokens)
    record_cost(scope=scope, step_name=step_name, model=resolved_model, cost_usd=cost)
    collector = get_run_collector()
    if collector is not None and scope == "run":
        collector.add_tokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=resolved_model,
        )
    return cost


def record_cost(*, scope: Scope, step_name: str, model: str | None, cost_usd: float) -> None:
    _init_instruments()
    if _cost_usd is not None:
        _cost_usd.add(
            cost_usd,
            {"scope": scope, "step_name": step_name, "model": model or _default_model()},
        )


def record_run_outcome(status: RunStatus) -> None:
    _init_instruments()
    if _runs_total is not None:
        _runs_total.add(1, {"status": status})


def resolve_run_status(response_in_scope: bool | None, *, error: bool) -> RunStatus:
    if error:
        return "error"
    if response_in_scope is False:
        return "scope_refusal"
    return "success"


def ingest_crew_token_usage(result: object, model: str | None = None) -> None:
    """Read CrewAI kickoff token_usage and record run-level metrics."""
    token_usage = getattr(result, "token_usage", None)
    if token_usage is None:
        return
    input_t = output_t = 0
    if hasattr(token_usage, "prompt_tokens"):
        input_t = int(token_usage.prompt_tokens or 0)
        output_t = int(getattr(token_usage, "completion_tokens", 0) or 0)
    elif isinstance(token_usage, dict):
        input_t = int(token_usage.get("prompt_tokens", 0) or 0)
        output_t = int(token_usage.get("completion_tokens", 0) or 0)
    if input_t or output_t:
        record_tokens(
            scope="run",
            step_name="crew",
            model=model,
            input_tokens=input_t,
            output_tokens=output_t,
        )


def new_run_collector(run_id: str, session_id: str) -> RunMetricsCollector:
    return RunMetricsCollector(
        run_id=run_id,
        session_id=session_id,
        model=_default_model(),
    )
