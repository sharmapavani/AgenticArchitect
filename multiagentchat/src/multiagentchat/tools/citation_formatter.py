"""Format retrieved chunks as canonical citations."""

from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from multiagentchat.observability.tool_metrics import instrument_tool


class CitationFormatterInput(BaseModel):
    chunks_json: str = Field(..., description="JSON string from vector_search output")


class CitationFormatterTool(BaseTool):
    name: str = "citation_formatter"
    description: str = "Format retrieved knowledge chunks into citation objects with url and title."
    args_schema: Type[BaseModel] = CitationFormatterInput

    @instrument_tool("citation_formatter")
    def _run(self, chunks_json: str) -> str:
        try:
            data = json.loads(chunks_json) if isinstance(chunks_json, str) else chunks_json
            chunks = data.get("chunks", data) if isinstance(data, dict) else data
            citations = []
            seen: set[str] = set()
            for chunk in chunks:
                source = chunk.get("source_file", "unknown")
                page = chunk.get("page", "?")
                key = f"{source}:{page}"
                if key in seen:
                    continue
                seen.add(key)
                citations.append(
                    {
                        "url": f"file://knowledge/{source}#page={page}",
                        "title": f"{source} p.{page}",
                    }
                )
            return json.dumps({"citations": citations})
        except Exception as exc:
            return json.dumps({"citations": [], "error": str(exc)})


format_citations = CitationFormatterTool()
