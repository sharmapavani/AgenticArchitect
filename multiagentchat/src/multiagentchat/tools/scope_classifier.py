"""CAI scope classification — hybrid rules + keyword matching."""

from __future__ import annotations

import json
import re
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from multiagentchat.observability.tool_metrics import instrument_tool

CAI_ALLOW_PATTERNS = [
    r"\bCAI\b",
    r"\bocf\b",
    r"\benrol",
    r"\badjudic",
    r"\binsurer",
    r"\bfacilit",
    r"\bclaim",
    r"\btreatment plan",
    r"\buser manag",
    r"\bpassword",
    r"\b2fa\b",
    r"\bprovider",
    r"\binvoice",
    r"\bform 1\b",
    r"\bCAIinfo",
    r"\bpms\b",
    r"\bvirtual service",
    r"\breason code",
    r"\bsubmit",
    r"\bdeactivat",
    r"\breactivat",
]

DENY_PATTERNS = [
    r"\belection\b",
    r"\bpolitic",
    r"\bpartisan",
    r"\bweather\b",
    r"\bsports\b",
    r"\brecipe\b",
    r"\bcryptocurrency\b",
    r"\bstock market\b",
]

INTENT_KEYWORDS = {
    "user_management": [
        r"user", r"password", r"2fa", r"login", r"deactivat", r"reactivat",
        r"inactive", r"role", r"permission", r"account",
    ],
    "ocf_submission": [
        r"submit", r"ocf-?18", r"ocf-?21", r"ocf-?23", r"form 1",
        r"virtual service", r"tracking plan", r"invoice",
    ],
    "ocf_adjudication": [
        r"adjudic", r"reason code", r"approval", r"decision support",
        r"deny", r"approve", r"attribute code",
    ],
}


class ScopeClassifierInput(BaseModel):
    message: str = Field(..., description="User message to classify for CAI scope")


class ScopeClassifierTool(BaseTool):
    name: str = "scope_classifier"
    description: str = (
        "Determine if a user query is within CAI/NYC auto insurance health claims scope. "
        "Returns in_scope, portal hint, language hint, and intent."
    )
    args_schema: Type[BaseModel] = ScopeClassifierInput

    @instrument_tool("scope_classifier")
    def _run(self, message: str) -> str:
        text = message.strip()
        lower = text.lower()

        for pattern in DENY_PATTERNS:
            if re.search(pattern, lower):
                return json.dumps(
                    {
                        "in_scope": False,
                        "scope_rejection_reason": "off_topic_or_political",
                        "portal": "facilities",
                        "language": "fr" if _looks_french(text) else "en",
                        "intent": "general",
                    }
                )

        in_scope = any(re.search(p, lower) for p in CAI_ALLOW_PATTERNS)
        if not in_scope and len(text) > 20:
            in_scope = any(
                word in lower
                for word in ("insurance", "NYC", "health claim", "treatment", "adjuster")
            )

        intent = "general"
        for intent_name, patterns in INTENT_KEYWORDS.items():
            if any(re.search(p, lower) for p in patterns):
                intent = intent_name
                break

        portal = "facilities"
        if any(w in lower for w in ("insurer", "adjuster", "adjudic", "approval")):
            portal = "insurers"
        elif any(w in lower for w in ("pms", "vendor", "integration", "software")):
            portal = "pms_vendors"

        language = "fr" if _looks_french(text) else "en"

        return json.dumps(
            {
                "in_scope": in_scope,
                "scope_rejection_reason": None if in_scope else "not_CAI_related",
                "portal": portal,
                "language": language,
                "intent": intent,
            }
        )


def _looks_french(text: str) -> bool:
    french_markers = ["bonjour", "comment", "réclam", "assurance", "utilisateur", "français"]
    lower = text.lower()
    return any(m in lower for m in french_markers)


classify_scope = ScopeClassifierTool()
