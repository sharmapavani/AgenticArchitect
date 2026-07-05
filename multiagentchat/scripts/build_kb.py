#!/usr/bin/env python3
"""Build ChromaDB knowledge base from bundled CAI PDF manuals."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from multiagentchat.kb.chroma_client import COLLECTION_NAME, get_chroma_path  # noqa: E402
from multiagentchat.kb.intent_map import chunk_text, infer_intent, infer_portal  # noqa: E402

import chromadb  # noqa: E402
from chromadb.config import Settings  # noqa: E402


def embed_texts(client: OpenAI, texts: list[str], model: str) -> list[list[float]]:
    if not texts:
        return []
    response = client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


def collect_pdfs(fac_dir: Path, ins_dir: Path) -> list[Path]:
    pdfs: list[Path] = []
    for directory in (fac_dir, ins_dir):
        if directory.exists():
            pdfs.extend(sorted(directory.glob("*.pdf")))
    return pdfs


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Copy .env.example to .env and configure.")
        return 1

    fac_dir = ROOT / os.getenv("KNOWLEDGE_FAC_DIR", "knowledge/pdf_fac_data")
    ins_dir = ROOT / os.getenv("KNOWLEDGE_INS_DIR", "knowledge/pdf_ins_data")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    pdfs = collect_pdfs(fac_dir, ins_dir)
    if not pdfs:
        print(f"WARNING: No PDFs found in {fac_dir} or {ins_dir}.")
        print("Place CAI manuals in knowledge/pdf_fac_data and knowledge/pdf_ins_data, then re-run.")
        return 0

    chroma_path = get_chroma_path()
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    openai_client = OpenAI(api_key=api_key)
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    batch_size = 32

    for pdf_path in pdfs:
        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:
            print(f"SKIP {pdf_path.name}: {exc}")
            continue

        portal = infer_portal(pdf_path, fac_dir.name, ins_dir.name)
        intent = infer_intent(pdf_path.stem)

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            for chunk_idx, chunk in enumerate(chunk_text(text)):
                doc_id = hashlib.sha256(
                    f"{pdf_path.name}:{page_num}:{chunk_idx}".encode()
                ).hexdigest()[:32]
                ids.append(doc_id)
                documents.append(chunk)
                metadatas.append(
                    {
                        "portal": portal,
                        "intent": intent,
                        "source_file": pdf_path.name,
                        "page": str(page_num),
                    }
                )

    if not documents:
        print("WARNING: No text extracted from PDFs.")
        return 0

    print(f"Indexing {len(documents)} chunks from {len(pdfs)} PDFs...")
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        embeddings = embed_texts(openai_client, batch_docs, embedding_model)
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_meta,
            embeddings=embeddings,
        )
        print(f"  Indexed {min(i + batch_size, len(documents))}/{len(documents)}")

    print(f"Done. ChromaDB stored at {chroma_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
