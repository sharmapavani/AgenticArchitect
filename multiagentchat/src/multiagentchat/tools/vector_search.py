"""Semantic search over CAI PDF knowledge base."""

from __future__ import annotations

import json
import os
from typing import Type

from crewai.tools import BaseTool
from openai import OpenAI
from pydantic import BaseModel, Field

from multiagentchat.kb.chroma_client import get_collection
from multiagentchat.observability.metrics import record_tokens
from multiagentchat.observability.portkey import is_portkey_enabled, portkey_base_url, portkey_headers
from multiagentchat.observability.tool_metrics import instrument_tool


class VectorSearchInput(BaseModel):
    query: str = Field(..., description="User question to search against CAI manuals")
    portal: str = Field(
        default="facilities",
        description="Portal filter: facilities, insurers, or pms_vendors",
    )
    intent: str = Field(
        default="general",
        description="Intent filter: user_management, ocf_submission, ocf_adjudication, or general",
    )
    top_k: int = Field(default=5, description="Number of chunks to retrieve")


def _build_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("no_api_key")

    if is_portkey_enabled():
        base_url = portkey_base_url()
        default_headers = portkey_headers()
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers or None,
        )
    return OpenAI(api_key=api_key)


class VectorSearchTool(BaseTool):
    name: str = "vector_search"
    description: str = (
        "Search the CAI knowledge base (bundled PDF manuals) for relevant passages. "
        "Always use before answering OCF or CAI procedural questions."
    )
    args_schema: Type[BaseModel] = VectorSearchInput

    @instrument_tool("vector_search")
    def _run(self, query: str, portal: str = "facilities", intent: str = "general", top_k: int = 5) -> str:
        try:
            collection = get_collection()
            count = collection.count()
            if count == 0:
                return json.dumps({"chunks": [], "retrieval_score": 0.0, "error": "kb_empty"})

            embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            client = _build_openai_client()
            embedding_response = client.embeddings.create(input=[query], model=embedding_model)
            usage = getattr(embedding_response, "usage", None)
            if usage is not None:
                input_tokens = int(
                    getattr(usage, "prompt_tokens", None)
                    or getattr(usage, "total_tokens", 0)
                    or 0
                )
                if input_tokens:
                    record_tokens(
                        scope="step",
                        step_name="vector_search.embedding",
                        model=embedding_model,
                        input_tokens=input_tokens,
                        output_tokens=0,
                    )
            embedding = embedding_response.data[0].embedding

            where: dict | None = None
            if portal in ("facilities", "insurers"):
                where = {"portal": portal}
            if intent != "general":
                intent_filter = {"intent": intent}
                where = {"$and": [where, intent_filter]} if where else intent_filter

            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, count),
                where=where,
            )

            chunks = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(documents, metadatas, distances):
                score = max(0.0, 1.0 - float(dist))
                chunks.append(
                    {
                        "text": doc,
                        "source_file": meta.get("source_file", "unknown"),
                        "page": meta.get("page", "?"),
                        "portal": meta.get("portal", portal),
                        "intent": meta.get("intent", intent),
                        "score": round(score, 3),
                    }
                )

            top_score = chunks[0]["score"] if chunks else 0.0
            return json.dumps({"chunks": chunks, "retrieval_score": top_score})
        except Exception as exc:
            return json.dumps({"chunks": [], "retrieval_score": 0.0, "error": str(exc)})


search_knowledge_base = VectorSearchTool()
