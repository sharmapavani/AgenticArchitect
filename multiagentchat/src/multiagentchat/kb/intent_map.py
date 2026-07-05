"""Intent metadata mapping for PDF knowledge base indexing."""

from __future__ import annotations

import re
from pathlib import Path

# Filename patterns → intent tag
INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)managing.?users|inactive.?users|password|2fa|verification|login|insurer.?user|insurer.?management|managing.?your.?facility|roles.?and.?tasks|sign.?in", "user_management"),
    (r"(?i)ocf[-_]?(18|21|23)|form.?1|submitting|virtual.?services|signaling|tracking.?plans|unit.?measures|provider.?type|facility.?reports|gap|mig|viewing.?attribute", "ocf_submission"),
    (r"(?i)adjudication|approval.?reason|decision.?support|decison.?support|attribute.?code", "ocf_adjudication"),
]

DEFAULT_INTENT = "general"


def infer_intent(filename: str) -> str:
    for pattern, intent in INTENT_PATTERNS:
        if re.search(pattern, filename):
            return intent
    return DEFAULT_INTENT


def infer_portal(path: Path, fac_dir_name: str, ins_dir_name: str) -> str:
    parts = {p.lower() for p in path.parts}
    if ins_dir_name.lower() in parts:
        return "insurers"
    if fac_dir_name.lower() in parts:
        return "facilities"
    return "facilities"


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(end - overlap, start + 1)
    return chunks
