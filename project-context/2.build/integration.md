# Integration Build Artifact — CAI Pilot

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @integration.eng  
**Epic:** Integration (`*integrate-api`)  
**Status:** MVP wiring + observability correlation complete (2026-07-02)

**Progress tracker:** [`integration-plan.md`](integration-plan.md)

---

## Summary

The Next.js **Critical Research Workflow** frontend is wired to the FastAPI gateway via `runService.ts`. Primary path: **`POST /chat/stream` SSE** for live agent progress; **`POST /chat`** retained as fallback. Correlation uses **`session_id`** (multi-turn) and **`run_id`** (server-generated per request, Option B).

---

## Correlation IDs

| ID | Where generated | Scope | End-to-end path |
|----|-----------------|-------|-----------------|
| `session_id` | Frontend `sessionStorage` | Conversation | `ChatRequest` → flow → audit |
| `run_id` | FastAPI `uuid.uuid4()` | Single message/run | SSE `run_started` → all events → `ChatResponse` → audit → OTel trace |

- Response headers: `X-Run-Id` on `/chat` and `/chat/stream` (forwarded by Next.js Route Handlers)
- OTel `trace_id` = `run_id` without hyphens (32 hex)
- Frontend adopts server `run_id` from first SSE event; history stores resolved id

---

## What Was Integrated

| Component | Change |
|-----------|--------|
| `frontend/src/lib/session.ts` | `session_id` in `sessionStorage`; `is_session_start` tracking |
| `frontend/src/lib/apiMapper.ts` | `RunInput` → `ChatRequest`, `ChatResponse` → `RunResult` |
| `frontend/src/services/runService.ts` | SSE consumer; server `run_id` adoption; `getServerRunId()` |
| `frontend/src/hooks/useRunWorkflow.ts` | Updates `runId` on `run_started`; progress + poll |
| `frontend/src/lib/agentPipeline.ts` | `run_started`, `currentSummary`, correlation fields |
| `frontend/src/app/api/chat/stream/route.ts` | Proxies SSE + `X-Run-Id` |
| `frontend/src/app/api/chat/route.ts` | Proxies JSON + `X-Run-Id` |
| `multiagentchat/observability/` | OTel init, spans, context, Portkey helpers |
| `multiagentchat/src/multiagentchat/api/app.py` | `run_id`, `run_started` SSE, `X-Run-Id` |
| `multiagentchat/flows/CAI_chat_flow.py` | Spans + correlated SSE |
| `multiagentchat/audit/sqlite_db.py` | `run_id` column + MCP query |

---

## API Contract

### Endpoints wired

| Endpoint | Method | Frontend usage |
|----------|--------|----------------|
| `/health` | GET | `checkApiHealth()` |
| `/chat/stream` | POST | Primary — SSE: `run_started` → progress → `result` |
| `/chat` | POST | Fallback; read `X-Run-Id` / `run_id` in body |

### SSE sequence

```
run_started → flow_step* → pipeline → agent_task* → result | error
```

All events include `run_id` and `session_id`. Product summaries exclude PII and tool output.

---

## Configuration

### Backend (`multiagentchat/.env`)

```bash
OPENAI_API_KEY=sk-...
CHROMA_PATH=.chroma
API_PORT=8000
OTEL_ENABLED=0
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Optional: `PORTKEY_API_KEY`, `PORTKEY_BASE_URL` for gateway + hierarchical traces.

### Observability dev stack

```bash
cd multiagentchat/docker
docker compose -f docker-compose.observability.yml up -d
# Set OTEL_ENABLED=1 and RUN_METRICS_ENABLED=1 in .env
# Jaeger http://localhost:16686 | Prometheus http://localhost:9090 | Grafana http://localhost:3001 (admin/admin)
```

See `multiagentchat/docs/observability.md`.

---

## External Services

| Service | Integration status |
|---------|-------------------|
| FastAPI gateway | Wired |
| OpenAI API | Backend prerequisite |
| ChromaDB | Local; run `build_kb.py` |
| OTel Collector + Jaeger + Prometheus + Grafana | Dev optional |
| Portkey gateway | Optional env-gated |
| ServiceNow | Stub |
| CAIInfo.ca crawler | Deferred |

---

## Observability verification

1. `POST /chat/stream` — first event is `run_started` with UUID `run_id`.
2. All SSE events share same `run_id`.
3. `ChatResponse.run_id` matches SSE.
4. Audit row includes `run_id`; MCP `get_chat_audit_by_run_id`.
5. With `OTEL_ENABLED=1`, Jaeger shows nested flow + crew spans for trace id (hex).
6. UI progress panel shows `currentSummary`; cancel uses resolved server id.
7. After one in-scope chat: Prometheus `chat_request_duration_count` increments (`http://localhost:9090`).
8. Grafana **MultiAgentChat Metrics** dashboard success-rate panel > 0% after successful run.
9. SQLite `run_metrics` row exists with `duration_ms`, tokens, `cost_usd`; MCP `get_run_metrics(run_id)`.
10. Scope refusal increments `chat_runs_total{status="scope_refusal"}`, not `error`.

---

## Known Gaps / Caveats

1. In-scope crew runs require valid `OPENAI_API_KEY`.
2. Full nine-agent crew may exceed 15 s KPI; 600 s poll timeout configured.
3. Python package requires `>=3.10,<3.14`.
4. ServiceNow `case_number` always null from stub.
5. Frontend OTel instrumentation deferred — backend exports spans only.

---

## Deferred (Post-MVP)

- `/chat/escalate` manual handoff route
- ServiceNow live Case API
- Copilot internal routes
- `conversation_history` round-trip from UI
- WebSocket progress channel
- Prometheus Alertmanager rules

---

## Open Questions

| ID | Question | Owner | Status |
|----|----------|-------|--------|
| OQ-FE-1 | SSE vs sync REST for P0 | @integration.eng | **Resolved** — SSE primary |
| OQ-BE-1 | SSE `/chat/stream` for P0 | @integration.eng | **Resolved** — implemented |
| OQ-INT-1 | ServiceNow live integration timeline | @integration.eng | Post-MVP stub |
| OQ-BE-3 | Production OTLP backend | @backend.eng | Open |

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02 |
| **Persona** | @integration.eng |
| **Action** | Observability integration — run_id end-to-end, SSE run_started, OTel dev stack, doc sync |
| **Runtime** | `AAMAD_TARGET_RUNTIME=crewai` |
| **API mode** | SSE primary + sync REST fallback |
| **Prompt Trace** | Operational OTel spans + product SSE progress unified by run_id |
