"""Compare crew kickoff latency with and without ticket/handoff/copilot tasks."""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# Windows console + CrewAI emoji output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Ensure package is importable when run from repo root or multiagentchat/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multiagentchat.crew import CAISupportCrew  # noqa: E402

SAMPLE_MESSAGE = os.getenv(
    "BENCH_MESSAGE",
    "How do I submit an OCF-18 treatment plan in the facilities portal?",
)
SAMPLE_INPUTS = {
    "message": SAMPLE_MESSAGE,
    "portal_hint": "facilities",
    "language": "en",
    "conversation_history": "[]",
    "preclassified_scope": (
        '{"in_scope":true,"portal":"facilities","language":"en",'
        '"intent":"ocf_submission","scope_rejection_reason":null}'
    ),
}


def run_once(label: str, skip_support: bool) -> float:
    os.environ["CREW_SKIP_SUPPORT_TASKS"] = "1" if skip_support else "0"
    task_count = 6 if skip_support else 9
    print(f"\n{'=' * 60}")
    print(f"Run: {label} ({task_count} tasks)")
    print(f"Query: {SAMPLE_MESSAGE[:80]}...")
    print(f"{'=' * 60}")

    started = time.perf_counter()
    crew = CAISupportCrew().crew()
    result = crew.kickoff(inputs=SAMPLE_INPUTS)
    elapsed = time.perf_counter() - started

    raw_preview = (result.raw if hasattr(result, "raw") else str(result))[:120]
    print(f"Finished in {elapsed:.1f}s")
    print(f"Output preview: {raw_preview}...")
    return elapsed


def main() -> None:
    print("Crew latency benchmark (requires OPENAI_API_KEY + populated Chroma KB)")
    slim = run_once("slim (no ticket/handoff/copilot)", skip_support=True)
    full = run_once("full (nine-task pipeline)", skip_support=False)

    saved = full - slim
    pct = (saved / full * 100) if full > 0 else 0.0

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Slim (6 tasks):  {slim:.1f}s")
    print(f"  Full (9 tasks):  {full:.1f}s")
    print(f"  Delta saved:     {saved:.1f}s ({pct:.0f}% faster without support tasks)")


if __name__ == "__main__":
    main()
