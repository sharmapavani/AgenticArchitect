"""SSE progress event schemas for /chat/stream."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from multiagentchat.schemas.chat import ChatResponse

FlowStepName = Literal[
    "greet_and_intake",
    "classify_scope",
    "run_CAI_crew",
    "assemble_chat_response",
    "scope_refusal",
]

StepStatus = Literal["started", "completed"]

FLOW_STEP_SUMMARIES: dict[FlowStepName, str] = {
    "greet_and_intake": "Starting your session",
    "classify_scope": "Checking if your question is in scope",
    "run_CAI_crew": "Running the CAI agent pipeline",
    "assemble_chat_response": "Preparing your answer",
    "scope_refusal": "Reviewing scope guidelines",
}


class CorrelationFields(BaseModel):
    run_id: str
    session_id: str


class RunStartedEvent(CorrelationFields):
    type: Literal["run_started"] = "run_started"
    message: str = "Processing your request…"


class PipelineTaskInfo(BaseModel):
    task_id: str
    agent_id: str
    label: str


class PipelineEvent(CorrelationFields):
    type: Literal["pipeline"] = "pipeline"
    total_tasks: int
    tasks: list[PipelineTaskInfo] = Field(default_factory=list)


class FlowStepEvent(CorrelationFields):
    type: Literal["flow_step"] = "flow_step"
    step: FlowStepName
    status: StepStatus
    summary: str = ""


class AgentTaskEvent(CorrelationFields):
    type: Literal["agent_task"] = "agent_task"
    task_id: str
    agent_id: str
    label: str
    index: int
    total: int
    status: StepStatus
    summary: str = ""
    duration_s: float | None = None
    cumulative_s: float | None = None


class ResultEvent(CorrelationFields):
    type: Literal["result"] = "result"
    payload: ChatResponse


class ErrorEvent(CorrelationFields):
    type: Literal["error"] = "error"
    message: str
