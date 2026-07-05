"""Flow step timing helper — span + histogram."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from multiagentchat.observability.metrics import record_step
from multiagentchat.observability.spans import start_span


@contextmanager
def flow_step_span(step_name: str) -> Iterator[None]:
    started = perf_counter()
    with start_span(f"flow.{step_name}"):
        try:
            yield
        finally:
            record_step("flow", step_name, perf_counter() - started)
