"""Test full 9-task crew pipeline (CREW_SKIP_SUPPORT_TASKS=0)."""
import json
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
os.environ["CREW_SKIP_SUPPORT_TASKS"] = "0"

import httpx

BASE = "http://127.0.0.1:8000"


def main():
    # Note: running server may still use CREW_SKIP_SUPPORT_TASKS=1 from its env.
    # Direct flow test bypasses server env.
    from multiagentchat.flows.CAI_chat_flow import CAIChatFlow

    flow = CAIChatFlow()
    inputs = {
        "session_id": str(uuid.uuid4()),
        "message": "How do I reactivate a deactivated user?",
        "language": "en",
        "portal_hint": "facilities",
        "channel": "chat",
        "skip_rag": False,
        "is_session_start": False,
        "conversation_history": [],
    }
    t0 = time.time()
    result = flow.kickoff(inputs=inputs)
    elapsed = time.time() - t0
    resp = result.get("chat_response") if isinstance(result, dict) else None
    if resp is None and hasattr(result, "model_dump"):
        resp = result.model_dump()
    elif resp is None and hasattr(result, "dict"):
        resp = result.dict()
    out = {
        "elapsed_s": round(elapsed, 1),
        "case_number": getattr(resp, "case_number", None) if resp and not isinstance(resp, dict) else (resp or {}).get("case_number"),
        "escalate": getattr(resp, "escalate", None) if resp and not isinstance(resp, dict) else (resp or {}).get("escalate"),
        "citations": len((resp or {}).get("citations", []) if isinstance(resp, dict) else (getattr(resp, "citations", None) or [])),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
