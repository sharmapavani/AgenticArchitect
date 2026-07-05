"""ChromaDB client helpers for CAI knowledge base."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

COLLECTION_NAME = "CAI_kb"


def get_chroma_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    rel = os.getenv("CHROMA_PATH", ".chroma")
    path = root / rel
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_collection():
    client = chromadb.PersistentClient(
        path=str(get_chroma_path()),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
