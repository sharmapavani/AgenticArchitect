"""In-memory per-run metrics aggregation for SQLite rollup."""

from __future__ import annotations

import contextvars
import os
from dataclasses import dataclass, field
from time import perf_counter

from multiagentchat.observability.pricing import compute_cost_usd

_run_collector_var: contextvars.ContextVar[RunMetricsCollector | None] = contextvars.ContextVar(
    "run_metrics_collector", default=None
)


@dataclass
class StepMetricRecord:
    step_type: str
    step_name: str
    duration_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


@dataclass
class RunMetricsCollector:
    run_id: str
    session_id: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    steps: list[StepMetricRecord] = field(default_factory=list)
    _started: float = field(default=0.0, repr=False)

    def start(self) -> None:
        self._started = perf_counter()

    def elapsed_ms(self) -> float:
        if self._started == 0.0:
            return 0.0
        return (perf_counter() - self._started) * 1000

    def record_step(
        self,
        step_type: str,
        step_name: str,
        duration_s: float,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model: str | None = None,
    ) -> None:
        cost = None
        if input_tokens is not None or output_tokens is not None:
            cost = compute_cost_usd(
                model or self.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                input_tokens or 0,
                output_tokens or 0,
            )
        self.steps.append(
            StepMetricRecord(
                step_type=step_type,
                step_name=step_name,
                duration_ms=duration_s * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
        )

    def add_tokens(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str | None = None,
    ) -> float:
        resolved_model = model or self.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        cost = compute_cost_usd(resolved_model, input_tokens, output_tokens)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens
        self.cost_usd = round(self.cost_usd + cost, 6)
        return cost


def get_run_collector() -> RunMetricsCollector | None:
    return _run_collector_var.get()


def bind_run_collector(collector: RunMetricsCollector):
    return _run_collector_var.set(collector)


def reset_run_collector(token) -> None:
    _run_collector_var.reset(token)
