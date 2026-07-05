"""Shared LLM configuration for CrewAI agents."""

from __future__ import annotations

import os

from crewai import LLM

from multiagentchat.observability.portkey import is_portkey_enabled, portkey_base_url, portkey_headers


def get_llm() -> LLM:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    kwargs: dict = {"model": model}
    if not any(tag in model.lower() for tag in ("gpt-5", "o1", "o3")):
        kwargs["temperature"] = temperature

    if is_portkey_enabled():
        base_url = portkey_base_url()
        headers = portkey_headers()
        if base_url:
            kwargs["base_url"] = base_url
        if headers:
            kwargs["extra_headers"] = headers

    return LLM(**kwargs)
