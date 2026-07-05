"""CAIChatFlow — CrewAI Flow orchestrating greeting, scope gate, and crew pipeline."""

from __future__ import annotations

import json
import time

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel, Field

from multiagentchat.crew import CAISupportCrew, active_task_manifest
from multiagentchat.flows.greeting import (
    get_greeting,
    get_retrieval_failure,
    get_scope_refusal,
)
from multiagentchat.flows.response_parser import (
    extract_json,
    normalize_workflow_map,
    parse_crew_outputs,
)
from multiagentchat.observability.flow_metrics import flow_step_span
from multiagentchat.observability.spans import record_span_event, set_span_attributes
from multiagentchat.schemas.chat import ChatResponse, Citation, WorkflowMap
from multiagentchat.tools.scope_classifier import classify_scope
from multiagentchat.utils.crew_timing import CrewTimingTracker
from multiagentchat.utils.progress_emitter import ProgressEmitter, emit_flow_step, emit_pipeline
from multiagentchat.utils.request_timing import RequestTimingTracker


class CAIFlowState(BaseModel):
    session_id: str = ""
    run_id: str = ""
    message: str = ""
    language: str = "auto"
    portal_hint: str | None = None
    skip_rag: bool = False
    is_session_start: bool = False
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    greeting_text: str | None = None
    resolved_language: str = "en"
    in_scope: bool = True
    scope_rejection_reason: str | None = None
    classified_intent: str = "general"
    crew_raw: str = ""
    crew_outputs: dict = Field(default_factory=dict)
    chat_response: ChatResponse | None = None


class CAIChatFlow(Flow[CAIFlowState]):
    """Flow entrypoint for CAI MultiAgentChat backend."""

    _request_timing: RequestTimingTracker | None = None
    _progress_emitter: ProgressEmitter | None = None

    def _correlation(self) -> tuple[str, str]:
        return self.state.run_id, self.state.session_id

    def _init_request_timing(self) -> RequestTimingTracker:
        if self._request_timing is None:
            self._request_timing = RequestTimingTracker(
                run_id=self.state.run_id,
                session_id=self.state.session_id,
                message_preview=self.state.message,
            )
            self._request_timing.start()
        return self._request_timing

    @start()
    def greet_and_intake(self) -> None:
        run_id, session_id = self._correlation()
        with flow_step_span("greet_and_intake"):
            emit_flow_step(
                self._progress_emitter,
                "greet_and_intake",
                "started",
                run_id=run_id,
                session_id=session_id,
            )
            self._init_request_timing()
            if self.state.is_session_start:
                lang = self.state.language if self.state.language in ("en", "fr") else "en"
                self.state.greeting_text = get_greeting(lang)
                self.state.resolved_language = lang
            elif self.state.language in ("en", "fr"):
                self.state.resolved_language = self.state.language
            timing = self._init_request_timing()
            timing.end_step("greet_and_intake")
            emit_flow_step(
                self._progress_emitter,
                "greet_and_intake",
                "completed",
                run_id=run_id,
                session_id=session_id,
            )

    @listen(greet_and_intake)
    def classify_scope(self) -> None:
        run_id, session_id = self._correlation()
        with flow_step_span("classify_scope"):
            emit_flow_step(
                self._progress_emitter,
                "classify_scope",
                "started",
                run_id=run_id,
                session_id=session_id,
            )
            timing = self._init_request_timing()
            if self.state.skip_rag:
                self.state.in_scope = True
            else:
                result_json = classify_scope._run(self.state.message)
                payload = extract_json(result_json)
                self.state.in_scope = bool(payload.get("in_scope", False))
                self.state.scope_rejection_reason = payload.get("scope_rejection_reason")
                self.state.classified_intent = payload.get("intent", "general")
                if payload.get("language"):
                    self.state.resolved_language = payload["language"]
                if not self.state.portal_hint and payload.get("portal"):
                    self.state.portal_hint = payload["portal"]
            set_span_attributes(
                {
                    "scope.in_scope": self.state.in_scope,
                    "scope.intent": self.state.classified_intent,
                    "scope.portal": self.state.portal_hint,
                }
            )
            timing.end_step("classify_scope")
            emit_flow_step(
                self._progress_emitter,
                "classify_scope",
                "completed",
                run_id=run_id,
                session_id=session_id,
            )

    @router(classify_scope)
    def route_scope(self) -> str:
        return "in_scope" if self.state.in_scope else "refuse"

    @listen("refuse")
    def scope_refusal(self) -> None:
        run_id, session_id = self._correlation()
        with flow_step_span("scope_refusal"):
            emit_pipeline(self._progress_emitter, [], run_id=run_id, session_id=session_id)
            emit_flow_step(
                self._progress_emitter,
                "scope_refusal",
                "started",
                run_id=run_id,
                session_id=session_id,
            )
            record_span_event(
                "scope.refused",
                {"scope.rejection_reason": self.state.scope_rejection_reason or "not_CAI_related"},
            )
            lang = self.state.resolved_language
            answer = get_scope_refusal(lang)
            if self.state.greeting_text:
                answer = f"{self.state.greeting_text}\n\n{answer}"
            self.state.chat_response = ChatResponse(
                answer=answer,
                session_id=self.state.session_id,
                run_id=self.state.run_id,
                in_scope=False,
                scope_refusal_reason=self.state.scope_rejection_reason or "not_CAI_related",
                greeting_included=bool(self.state.greeting_text),
            )
            timing = self._init_request_timing()
            timing.end_step("scope_refusal")
            timing.log_request_summary(path="refuse")
            emit_flow_step(
                self._progress_emitter,
                "scope_refusal",
                "completed",
                run_id=run_id,
                session_id=session_id,
            )

    @listen("in_scope")
    def run_CAI_crew(self) -> None:
        run_id, session_id = self._correlation()
        with flow_step_span("run_CAI_crew"):
            flow_timing = self._init_request_timing()
            manifest = active_task_manifest()
            emit_pipeline(self._progress_emitter, manifest, run_id=run_id, session_id=session_id)
            emit_flow_step(
                self._progress_emitter,
                "run_CAI_crew",
                "started",
                run_id=run_id,
                session_id=session_id,
            )
            portal = self.state.portal_hint or "facilities"
            history_str = json.dumps(self.state.conversation_history[-10:])
            preclassified_scope = json.dumps(
                {
                    "in_scope": self.state.in_scope,
                    "portal": portal,
                    "language": self.state.resolved_language,
                    "intent": self.state.classified_intent,
                    "scope_rejection_reason": self.state.scope_rejection_reason,
                }
            )
            inputs = {
                "message": self.state.message,
                "portal_hint": portal,
                "language": self.state.resolved_language,
                "conversation_history": history_str,
                "preclassified_scope": preclassified_scope,
            }
            timing = CrewTimingTracker(
                run_id=self.state.run_id,
                session_id=self.state.session_id,
                message_preview=self.state.message,
                task_manifest=manifest,
                emit=self._progress_emitter,
            )
            crew = CAISupportCrew().crew()
            crew.task_callback = timing.on_task_complete
            timing.mark_kickoff_start()
            kickoff_started = time.perf_counter()
            result = crew.kickoff(inputs=inputs)
            crew_elapsed = time.perf_counter() - kickoff_started
            timing.log_summary(result, crew_elapsed)
            flow_timing.end_step("run_CAI_crew", detail=f"crew {crew_elapsed:.1f}s")
            flow_timing.add_crew_steps(timing.records)
            emit_flow_step(
                self._progress_emitter,
                "run_CAI_crew",
                "completed",
                run_id=run_id,
                session_id=session_id,
            )
            self.state.crew_raw = result.raw if hasattr(result, "raw") else str(result)
            task_outputs = getattr(result, "tasks_output", None) or []
            self.state.crew_outputs = parse_crew_outputs(self.state.crew_raw, task_outputs)

    @listen(run_CAI_crew)
    def assemble_chat_response(self) -> None:
        run_id, session_id = self._correlation()
        with flow_step_span("assemble_chat_response"):
            emit_flow_step(
                self._progress_emitter,
                "assemble_chat_response",
                "started",
                run_id=run_id,
                session_id=session_id,
            )
            outputs = self.state.crew_outputs
            triage = outputs.get("triage", {})
            respond = outputs.get("respond", outputs.get("final", {}))
            sentiment = outputs.get("sentiment", {})
            ticket = outputs.get("ticket", {})

            lang = triage.get("language", self.state.resolved_language)
            answer = respond.get("answer", "")
            citations_raw = respond.get("citations", [])
            confidence = float(respond.get("confidence", sentiment.get("confidence", 0.0)))
            retrieval = outputs.get("retrieve", {})
            retrieval_score = float(retrieval.get("retrieval_score", 0.0))

            if not answer and retrieval_score == 0.0:
                answer = get_retrieval_failure(lang)
                confidence = 0.0

            citations = [
                Citation(url=c.get("url", ""), title=c.get("title", ""))
                for c in citations_raw
                if isinstance(c, dict)
            ]

            wf = respond.get("workflow_map") or {}
            normalized_wf = normalize_workflow_map(wf, portal_fallback=triage.get("portal"))
            workflow_map = WorkflowMap(**normalized_wf) if normalized_wf else None

            if self.state.greeting_text and answer:
                answer = f"{self.state.greeting_text}\n\n{answer}"

            escalate = bool(sentiment.get("escalate", confidence < 0.7 and retrieval_score == 0))
            case_number = ticket.get("case_number")

            self.state.chat_response = ChatResponse(
                answer=answer,
                citations=citations,
                workflow_map=workflow_map,
                confidence=confidence,
                translated_from_en=bool(respond.get("translated_from_en", False)),
                escalate=escalate,
                case_number=case_number,
                session_id=self.state.session_id,
                run_id=self.state.run_id,
                in_scope=True,
                tone_check_passed=bool(respond.get("tone_check_passed", True)),
                greeting_included=bool(self.state.greeting_text),
                intent=triage.get("intent"),
                portal=triage.get("portal", self.state.portal_hint),
            )
            set_span_attributes(
                {
                    "response.confidence": confidence,
                    "response.escalate": escalate,
                    "response.guardrail_blocked": self.state.chat_response.guardrail_blocked,
                }
            )
            timing = self._init_request_timing()
            timing.end_step("assemble_chat_response")
            timing.log_request_summary(path="in_scope")
            emit_flow_step(
                self._progress_emitter,
                "assemble_chat_response",
                "completed",
                run_id=run_id,
                session_id=session_id,
            )
