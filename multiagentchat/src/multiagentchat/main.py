"""CLI entrypoint for CAIChatFlow."""

from __future__ import annotations

import uuid

from dotenv import load_dotenv

from multiagentchat.flows.CAI_chat_flow import CAIChatFlow, CAIFlowState


def run_flow() -> None:
    load_dotenv()
    sample = CAIFlowState(
        session_id=str(uuid.uuid4()),
        message="How do I reactivate a deactivated user account in CAI?",
        language="en",
        portal_hint="facilities",
        is_session_start=True,
    )
    flow = CAIChatFlow()
    flow.kickoff(inputs=sample.model_dump())
    response = flow.state.chat_response
    if response:
        print("\n--- Chat Response ---")
        print(f"Answer: {response.answer}")
        print(f"In scope: {response.in_scope}")
        print(f"Citations: {len(response.citations)}")
        print(f"Intent: {response.intent}")
    else:
        print("No response produced.")


if __name__ == "__main__":
    run_flow()
