"""FastAPI gateway for MultiAgentChat backend."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry import context as otel_context
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from multiagentchat.audit.logger import log_chat_exchange
from multiagentchat.audit.sqlite_db import init_db, is_audit_enabled
from multiagentchat.flows.CAI_chat_flow import CAIChatFlow, CAIFlowState
from multiagentchat.observability.context import bind_run_context
from multiagentchat.observability.logging import install_correlation_logging
from multiagentchat.observability.metrics import (
    RunStatus,
    new_run_collector,
    record_request,
    record_run_outcome,
    resolve_run_status,
)
from multiagentchat.observability.openai_instrumentation import install_openai_instrumentation
from multiagentchat.observability.otel import flush_telemetry, init_otel, is_otel_enabled
from multiagentchat.observability.run_collector import bind_run_collector, reset_run_collector
from multiagentchat.observability.run_metrics_db import init_metrics_db, is_metrics_enabled
from multiagentchat.observability.run_metrics_store import persist_run_metrics
from multiagentchat.observability.spans import start_root_span
from multiagentchat.schemas.chat import ChatRequest, ChatResponse
from multiagentchat.utils.progress_emitter import emit_run_started, envelope

# Load multiagentchat/.env regardless of process cwd (repo root vs package dir).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env")

if is_audit_enabled():
    init_db()

if is_metrics_enabled():
    init_metrics_db()

init_otel("multiagentchat")
install_openai_instrumentation()

_logger = logging.getLogger("multiagentchat.api")
if is_otel_enabled():
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    _logger.info("OpenTelemetry enabled — exporting traces to %s", endpoint)
else:
    _logger.info(
        "OpenTelemetry disabled — set OTEL_ENABLED=1 in multiagentchat/.env and restart"
    )

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
install_correlation_logging()

app = FastAPI(
    title="MultiAgentChat CAI Backend",
    description="CrewAI Flow + nine-agent crew for CAIInfo queries",
    version="0.1.0",
)

if is_otel_enabled():
    FastAPIInstrumentor.instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: set[str] = set()
_session_lock = asyncio.Lock()


async def _is_first_message(session_id: str) -> bool:
    async with _session_lock:
        if session_id in _sessions:
            return False
        _sessions.add(session_id)
        return True


def _build_flow_state(
    request: ChatRequest,
    session_start: bool,
    run_id: str,
) -> CAIFlowState:
    return CAIFlowState(
        session_id=request.session_id or str(uuid.uuid4()),
        run_id=run_id,
        message=request.message.strip(),
        language=request.language,
        portal_hint=request.portal_hint,
        skip_rag=request.skip_rag,
        is_session_start=session_start,
        conversation_history=request.conversation_history,
    )


async def _execute_chat_flow(
    state: CAIFlowState,
    progress_emitter=None,
) -> ChatResponse:
    flow = CAIChatFlow()
    flow._progress_emitter = progress_emitter
    await flow.kickoff_async(inputs=state.model_dump())
    if flow.state.chat_response is None:
        raise HTTPException(status_code=500, detail="Flow did not produce a chat response")
    response = flow.state.chat_response
    if not response.run_id:
        response.run_id = state.run_id
    return response


def _execute_chat_flow_sync(
    state: CAIFlowState,
    progress_emitter,
) -> ChatResponse:
    flow = CAIChatFlow()
    flow._progress_emitter = progress_emitter
    flow.kickoff(inputs=state.model_dump())
    if flow.state.chat_response is None:
        raise HTTPException(status_code=500, detail="Flow did not produce a chat response")
    response = flow.state.chat_response
    if not response.run_id:
        response.run_id = state.run_id
    return response


def _run_flow_in_context(
    otel_ctx,
    state: CAIFlowState,
    progress_emitter: Callable[[dict], None] | None,
) -> ChatResponse:
    token = otel_context.attach(otel_ctx)
    try:
        with bind_run_context(run_id=state.run_id, session_id=state.session_id):
            with start_root_span(
                "chat.request",
                run_id=state.run_id,
                attributes={"http.route": "/chat/stream"},
            ):
                return _execute_chat_flow_sync(state, progress_emitter)
    finally:
        otel_context.detach(token)


@dataclass
class _RunMetricsContext:
    collector_token: object
    started: float
    route: str


def _begin_run_metrics(run_id: str, session_id: str, route: str) -> _RunMetricsContext:
    collector = new_run_collector(run_id, session_id)
    token = bind_run_collector(collector)
    collector.start()
    return _RunMetricsContext(collector_token=token, started=perf_counter(), route=route)


def _finalize_run_metrics(
    ctx: _RunMetricsContext,
    *,
    status: RunStatus,
    error_message: str | None = None,
) -> None:
    from multiagentchat.observability.run_collector import get_run_collector

    duration_s = perf_counter() - ctx.started
    record_request(duration_s, ctx.route, status)
    record_run_outcome(status)
    run_collector = get_run_collector()
    if run_collector is not None:
        persist_run_metrics(
            run_collector,
            status=status,
            duration_ms=duration_s * 1000,
            error_message=error_message,
        )
    reset_run_collector(ctx.collector_token)
    flush_telemetry()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "multiagentchat"}


@app.post("/chat")
async def chat(request: ChatRequest) -> JSONResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")

    run_id = str(uuid.uuid4())
    session_start = request.is_session_start or await _is_first_message(request.session_id)
    state = _build_flow_state(request, session_start, run_id)

    metrics_ctx = _begin_run_metrics(run_id, state.session_id, "/chat")
    status: RunStatus = "error"
    error_message: str | None = None
    response: ChatResponse | None = None
    try:
        with bind_run_context(run_id=run_id, session_id=state.session_id):
            with start_root_span(
                "chat.request",
                run_id=run_id,
                attributes={"http.route": "/chat"},
            ):
                response = await _execute_chat_flow(state)
        status = resolve_run_status(response.in_scope, error=False)
    except HTTPException as exc:
        error_message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        raise
    except Exception:
        error_message = "internal_error"
        raise
    finally:
        _finalize_run_metrics(metrics_ctx, status=status, error_message=error_message)

    log_chat_exchange(request, response)
    return JSONResponse(
        content=response.model_dump(mode="json"),
        headers={"X-Run-Id": run_id},
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")

    run_id = str(uuid.uuid4())
    session_start = request.is_session_start or await _is_first_message(request.session_id)
    state = _build_flow_state(request, session_start, run_id)

    queue: asyncio.Queue[dict | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def emit(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    emit_run_started(emit, run_id=run_id, session_id=state.session_id)

    otel_ctx = otel_context.get_current()

    async def run_flow() -> None:
        metrics_ctx = _begin_run_metrics(run_id, state.session_id, "/chat/stream")
        status: RunStatus = "error"
        error_message: str | None = None
        try:
            with bind_run_context(run_id=run_id, session_id=state.session_id):
                chat_response = await asyncio.to_thread(
                    _run_flow_in_context,
                    otel_ctx,
                    state,
                    emit,
                )
            log_chat_exchange(request, chat_response)
            status = resolve_run_status(chat_response.in_scope, error=False)
            await queue.put(
                envelope(
                    {
                        "type": "result",
                        "payload": chat_response.model_dump(mode="json"),
                    },
                    run_id=run_id,
                    session_id=state.session_id,
                )
            )
        except HTTPException as exc:
            error_message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            detail = error_message or "Request failed"
            await queue.put(
                envelope(
                    {"type": "error", "message": detail},
                    run_id=run_id,
                    session_id=state.session_id,
                )
            )
        except Exception as exc:
            error_message = "internal_error"
            logging.getLogger("multiagentchat.api").exception("chat/stream failed")
            await queue.put(
                envelope(
                    {"type": "error", "message": "An error occurred while processing your request."},
                    run_id=run_id,
                    session_id=state.session_id,
                )
            )
        finally:
            _finalize_run_metrics(metrics_ctx, status=status, error_message=error_message)
            await queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_flow())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Run-Id": run_id,
        },
    )


def serve() -> None:
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("multiagentchat.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    serve()
