#!/bin/sh
set -e

mkdir -p /app/data

if [ "${CHAT_AUDIT_ENABLED:-1}" = "1" ]; then
    echo "Initializing audit database..."
    init-access-audit-db || true
fi

# Build KB when PDFs exist and Chroma collection is empty
if [ -n "${OPENAI_API_KEY}" ]; then
    PDF_COUNT=$(find /app/knowledge -name '*.pdf' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$PDF_COUNT" -gt 0 ]; then
        echo "Checking Chroma knowledge base ($PDF_COUNT PDFs found)..."
        python - <<'PY'
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app/src")

from multiagentchat.kb.chroma_client import COLLECTION_NAME, get_chroma_path

import chromadb
from chromadb.config import Settings

path = get_chroma_path()
client = chromadb.PersistentClient(
    path=str(path),
    settings=Settings(anonymized_telemetry=False),
)
try:
    col = client.get_collection(COLLECTION_NAME)
    count = col.count()
except Exception:
    count = 0

if count == 0:
    print("Chroma collection empty — running build_kb.py")
    import subprocess
    subprocess.run(["python", "scripts/build_kb.py"], check=False)
else:
    print(f"Chroma collection has {count} documents — skipping KB build")
PY
    else
        echo "No PDFs in knowledge/ — skipping KB build"
    fi
else
    echo "WARNING: OPENAI_API_KEY not set — KB build skipped"
fi

echo "Starting backend..."
exec "$@"
