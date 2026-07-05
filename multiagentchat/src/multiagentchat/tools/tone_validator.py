"""Professional tone validation for user-facing responses."""

from __future__ import annotations

import json
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from multiagentchat.observability.tool_metrics import instrument_tool

UNPROFESSIONAL_PATTERNS = [
    r"\blol\b",
    r"\blmao\b",
    r"\bwtf\b",
    r"\bstupid\b",
    r"\bidiot\b",
    r"\bsucks\b",
    r"!!!+",
    r"\bsarcas",
]


class ToneValidatorInput(BaseModel):
    text: str = Field(..., description="Response text to validate for professional tone")


class ToneValidatorTool(BaseTool):
    name: str = "tone_validator"
    description: str = "Check that response text uses warm, professional, support-appropriate language."
    args_schema: Type[BaseModel] = ToneValidatorInput

    @instrument_tool("tone_validator")
    def _run(self, text: str) -> str:
        lower = text.lower()
        violations = [p for p in UNPROFESSIONAL_PATTERNS if re.search(p, lower)]
        passed = len(violations) == 0 and len(text.strip()) > 0
        return json.dumps(
            {
                "tone_check_passed": passed,
                "violations": violations,
            }
        )


validate_tone = ToneValidatorTool()
