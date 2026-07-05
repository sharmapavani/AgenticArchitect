# CAI Pilot Integration Plan — Progress Tracker

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @integration.eng  
**Runtime:** `AAMAD_TARGET_RUNTIME=crewai`  
**Plan date:** 2026-06-26  
**Last updated:** 2026-07-02 (observability integration)

---

## Plan Overview

Wire the Next.js **Critical Research Workflow** frontend to the FastAPI `POST /chat` gateway using **sync REST wrapped in the existing `startRun`/`getRunStatus` polling surface**. Preserve FSM (`idle → running → done`) and hook surface (`submit`, `reset`, `retry`).

**Related artifacts:**

| Artifact | Path |
|----------|------|
| Frontend build | [`frontend.md`](frontend.md) |
| Backend build | [`backend.md`](backend.md) |
| Integration summary | [`integration.md`](integration.md) |
| Implementation | `frontend/`, `multiagentchat/` |

---

## Frontend-Backend Integration

| Item | Detail |
|------|--------|
| Service layer | Replace stub Map in `runService.ts` with in-flight `POST /chat` promises keyed by `runId` |
| Session | `session_id` persisted in `sessionStorage` (`caiSessionId`) via `frontend/src/lib/session.ts` |
| Session start | First browser message sets `is_session_start: true`; backend also tracks server-side sessions |
| Schema mapping | `frontend/src/lib/apiMapper.ts` — `RunInput` ↔ `ChatRequest`, `ChatResponse` ↔ `RunResult` |
| Polling | 500 ms interval; 120 s max duration; spinner until HTTP completes |

---

## API Connection Setup

| Setting | Value |
|---------|-------|
| Base URL | `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000`) |
| Health | `GET /health` |
| Chat | `POST /chat` |
| CORS | `allow_origins=["*"]` in `multiagentchat/src/multiagentchat/api/app.py` |
| Dev proxy | Optional Next.js rewrite `/api/*` → `http://127.0.0.1:8000/:path*` |

---

## External Service Integrations

| Service | Frontend wiring | Status |
|---------|-----------------|--------|
| FastAPI gateway | `POST /chat`, `GET /health` | MVP |
| OpenAI API | Backend only (`OPENAI_API_KEY`) | Prerequisite for in-scope runs |
| ChromaDB | Backend only (`CHROMA_PATH`) | Local; run `build_kb.py` |
| ServiceNow Case | Backend stub | Deferred |
| CAIInfo.ca crawler | Backend deferred | Deferred |
| SSE `/chat/stream` | Wired with `run_started` + correlation ids | ✅ Done |
| OTel Collector (dev) | Backend OTLP export | ✅ Done — optional `OTEL_ENABLED=1` |

### Observability integration

| Item | Detail |
|------|--------|
| Correlation | `session_id` (multi-turn) + `run_id` (per message, server-generated) |
| SSE sequence | `run_started` → `flow_step` / `pipeline` / `agent_task` → `result` |
| Headers | `X-Run-Id` forwarded by Next.js `/api/chat` and `/api/chat/stream` proxies |
| Frontend | Adopts server `run_id` from SSE; history stores resolved id |
| Ops | Jaeger UI at `:16686` when docker observability stack running |

---

## Configuration

| File | Variables |
|------|-----------|
| `multiagentchat/.env` | `OPENAI_API_KEY`, `CHROMA_PATH`, `API_PORT`, optional SN vars |
| `frontend/.env.local` | `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` |
| `frontend/.env.example` | Documents `NEXT_PUBLIC_API_BASE_URL` |

**Note:** `project-context/2.build/setup.md` was never created; run commands are consolidated in [`integration.md`](integration.md).

---

## Testing Approach

| Layer | Test | Expected |
|-------|------|----------|
| Pre-flight | `curl http://127.0.0.1:8000/health` | `{"status":"ok"}` |
| Backend | Out-of-scope query ("What's the weather?") | `in_scope=false` |
| Frontend E2E | Run → spinner → scope refusal or answer | Results + History updated |
| In-scope | User-management / OCF query | Answer + citations (needs API key + KB) |
| Error | Backend stopped | Inline error + Retry |
| Timeout | Run exceeds 120 s | Poll timeout error |
| Build | `npm run build` in `frontend/` | Pass |

---

## Execution Checklist

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create `integration-plan.md` | ✅ Done | This file |
| 2 | Create `apiMapper.ts` + `session.ts` | ✅ Done | Schema + session_id |
| 3 | Replace `runService.ts` stubs | ✅ Done | Sync REST + polling wrapper |
| 4 | Add `frontend/.env.example` + optional proxy | ✅ Done | `NEXT_PUBLIC_API_BASE_URL` |
| 5 | Fix `scope_refusal_reason` in flow | ✅ Done | `CAI_chat_flow.py` |
| 6 | Add poll timeout in `useRunWorkflow` | ✅ Done | 120 s max |
| 7 | Health preflight validation | ✅ Pass | `GET /health` |
| 8 | Scope-refusal E2E | ✅ Pass | Out-of-scope weather query |
| 9 | In-scope E2E | ✅ Pass | Crew run ~106 s; `in_scope=true`, `intent=user_management` |
| 10 | Error / retry path | ✅ Done | Fetch failure → FAIL + Retry |
| 11 | `npm run build` | ✅ Pass | Next.js 14.2.35 |
| 12 | Create `integration.md` artifact | ✅ Done | Sources, Audit, test results |
| 13 | Observability end-to-end (`run_id`, SSE, OTel) | ✅ Done | Backend + frontend + proxy headers |
| 14 | Verify run_id in audit MCP | ⬜ Manual | `query_chat_audit(run_id=...)` |

## Local Dev Run Order

```bash
# Terminal 1 — backend
cd multiagentchat
uvicorn multiagentchat.api.app:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
# Open http://localhost:3000
```

---

## Sources

| # | Source | Use |
|---|--------|-----|
| 1 | `project-context/1.define/prd.md` | Chat MVP scope, F14 scope refusal |
| 2 | `project-context/1.define/sad.md` | API §4.1 `/chat` schemas |
| 3 | `project-context/2.build/frontend.md` | Stub handoff, FSM contract |
| 4 | `project-context/2.build/backend.md` | API endpoints, gaps |
| 5 | `.cursor/agents/integration-eng.md` | Persona scope |

---

## Assumptions

1. SSE primary for agent progress; sync REST fallback retained.
2. ServiceNow remains stub; no live Case API in this epic.
3. Scope-refusal path validates wiring without `OPENAI_API_KEY`.

---

## Open Questions

| ID | Question | Owner | Status |
|----|----------|-------|--------|
| OQ-FE-1 | SSE vs sync REST for P0 | @integration.eng | **Resolved** — SSE primary |
| OQ-BE-1 | SSE `/chat/stream` for P0 | @integration.eng | **Resolved** — implemented |
| OQ-INT-1 | ServiceNow live integration timeline | @integration.eng | Post-MVP stub |

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02 |
| **Persona** | @integration.eng |
| **Action** | Observability integration — run_id correlation, SSE run_started, X-Run-Id proxy, OTel dev stack |
| **Prompt Trace** | End-to-end correlation documented; Jaeger verification optional |
