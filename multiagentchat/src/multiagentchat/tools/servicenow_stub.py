"""ServiceNow Case creation stub until integration epic."""

from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from multiagentchat.observability.tool_metrics import instrument_tool


class ServiceNowStubInput(BaseModel):
    portal: str = Field(default="facilities", description="Portal for assignment group routing")
    summary: str = Field(..., description="Case summary")
    suggested_resolution: str = Field(default="", description="Suggested resolution text")


class ServiceNowStubTool(BaseTool):
    name: str = "servicenow_case_api"
    description: str = "Create a ServiceNow Case (stub — returns null case_number until integration)."
    args_schema: Type[BaseModel] = ServiceNowStubInput

    @instrument_tool("servicenow_case_api")
    def _run(self, portal: str = "facilities", summary: str = "", suggested_resolution: str = "") -> str:
        return json.dumps(
            {
                "case_number": None,
                "assignment_group": f"CAI - {portal.title()} Support",
                "stub": True,
                "summary": summary,
                "suggested_resolution": suggested_resolution,
            }
        )


create_case_stub = ServiceNowStubTool()
