"""Tool execution wrapper — span + step duration metrics."""

from __future__ import annotations

import functools
from time import perf_counter
from typing import Callable, TypeVar

from multiagentchat.observability.metrics import record_step
from multiagentchat.observability.spans import start_span

F = TypeVar("F", bound=Callable)


def instrument_tool(tool_name: str) -> Callable[[F], F]:
    """Decorator for CrewAI tool _run methods."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = perf_counter()
            with start_span(
                f"tool.{tool_name}",
                attributes={"tool.name": tool_name},
            ):
                try:
                    return func(*args, **kwargs)
                finally:
                    record_step("tool", tool_name, perf_counter() - started)

        return wrapper  # type: ignore[return-value]

    return decorator
