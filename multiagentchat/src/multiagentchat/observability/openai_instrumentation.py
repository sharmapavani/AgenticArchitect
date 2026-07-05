"""OpenAI SDK auto-instrumentation for LLM spans and step-level token metrics."""

from __future__ import annotations

import logging

from multiagentchat.observability.otel import is_otel_enabled

_logger = logging.getLogger("multiagentchat.observability")
_installed = False


def install_openai_instrumentation() -> None:
    """Enable OpenAI v2 OTel instrumentation when OTEL is enabled."""
    global _installed
    if _installed or not is_otel_enabled():
        return
    try:
        from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

        OpenAIInstrumentor().instrument()
        _installed = True
        _logger.info("OpenAI SDK instrumentation enabled")
    except Exception as exc:
        _logger.warning("OpenAI instrumentation unavailable: %s", exc)
