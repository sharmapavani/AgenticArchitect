"""PII scrubbing for outbound CAI support responses."""

from __future__ import annotations

import json
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from multiagentchat.observability.tool_metrics import instrument_tool

HEALTH_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{3}[-\s]?\d{3}[-\s]?[A-Z]{2}\b", re.I)
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class PiiScrubberInput(BaseModel):
    text: str = Field(..., description="Text to scrub of PII before delivery")


class PiiScrubberTool(BaseTool):
    name: str = "pii_scrubber"
    description: str = "Remove health card numbers, phone numbers, and email addresses from outbound text."
    args_schema: Type[BaseModel] = PiiScrubberInput

    @instrument_tool("pii_scrubber")
    def _run(self, text: str) -> str:
        scrubbed = HEALTH_CARD_PATTERN.sub("[REDACTED]", text)
        scrubbed = PHONE_PATTERN.sub("[REDACTED]", scrubbed)
        scrubbed = EMAIL_PATTERN.sub("[REDACTED]", scrubbed)
        return json.dumps({"scrubbed_text": scrubbed, "pii_found": scrubbed != text})


scrub_pii = PiiScrubberTool()
