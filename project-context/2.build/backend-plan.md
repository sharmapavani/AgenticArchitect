# MultiAgentChat Backend Plan — Progress Tracker

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @backend.eng  
**Runtime:** `AAMAD_TARGET_RUNTIME=crewai`  
**Plan date:** 2026-06-20  
**Last updated:** 2026-07-02

---

## Plan Overview

Implement CrewAI **Flow** + full **SAD nine-agent sequential crew** for CAIInfo user queries (UserManagement, OCF_Submission, OCF_Adjudication), with bundled PDF RAG, guardrails, warm session greeting, and FastAPI `/chat`.

**Related artifacts:**

| Artifact | Path |
|----------|------|
| Functional spec | [`backend-funcional-spec.md`](backend-funcional-spec.md) |
| Build summary | [`backend.md`](backend.md) |
| Implementation | `multiagentchat/` |

---

## Execution Checklist

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create `backend-funcional-spec.md` | ✅ Done | Inputs / Run / Results / History, guardrails, KB, Spec Sync checklist |
| 2 | Scaffold `multiagentchat/` package | ✅ Done | `pyproject.toml`, `.env.example`, schemas, package layout |
| 3 | PDF knowledge base + ChromaDB indexer | ✅ Done | `scripts/build_kb.py`, `kb/`, portal + intent metadata |
| 4 | Tools (scope, RAG, PII, tone, SN stub) | ✅ Done | `tools/` module |
| 5 | Guardrails on triage + respond tasks | ✅ Done | `guardrails/triage_guardrails.py` |
| 6 | Nine-agent crew (YAML + `crew.py`) | ✅ Done | 9 agents, 9 tasks incl. `insurer_validate_task` |
| 7 | `CAIChatFlow` (greet → scope → crew → response) | ✅ Done | `flows/CAI_chat_flow.py` |
| 8 | FastAPI `GET /health`, `POST /chat` | ✅ Done | `api/app.py` |
| 9 | Document in `backend.md` | ✅ Done | Audit block included |
| 10 | Create this progress tracker | ✅ Done | `backend-plan.md` |
| 11 | SQLite audit log + MCP server (F10 minimal) | ✅ Done | `audit/`, `mcp/access_audit_server.py`, auto-log in `app.py` |
| 12 | Index PDF corpus + run `build_kb.py` | ⬜ Pending | Requires PDFs in `knowledge/pdf_*_data/` |
| 13 | End-to-end in-scope crew run (live LLM) | ⬜ Pending | Requires `OPENAI_API_KEY` + indexed KB |
| 14 | ServiceNow live integration | ⬜ Deferred | Stub only; `@integration.eng` |
| 15 | Copilot internal routes | ⬜ Deferred | Post-MVP |
| 16 | SSE `/chat/stream` | ✅ Done | Implemented in `api/app.py` |
| 17 | CAIInfo.ca crawler | ⬜ Deferred | OQ-BE-2 |
| 18 | OTel module + FastAPI instrumentation | ✅ Done | `observability/` package |
| 19 | `run_id` generation + context propagation | ✅ Done | Option B in `api/app.py` |
| 20 | Manual spans (flow, crew, tools) | ✅ Done | `CAI_chat_flow.py`, `crew_timing.py`, `vector_search.py` |
| 21 | Product SSE events (`run_started`, summaries) | ✅ Done | `schemas/progress.py`, `progress_emitter.py` |
| 22 | Audit DB `run_id` migration + MCP filter | ✅ Done | `sqlite_db.py`, `access_audit_server.py` |
| 23 | Optional Portkey trace headers | ✅ Done | `llmUtils.py`, `vector_search.py` |
| 24 | OTel Collector dev stack + `observability.md` | ✅ Done | `docker/otel-collector-config.yaml` |
| 25 | OTel Metrics SDK (histograms + counters) | ✅ Done | `observability/metrics.py`, `otel.py` |
| 26 | E2E + flow step instrumentation | ✅ Done | `api/app.py`, `flow_metrics.py`, `CAI_chat_flow.py` |
| 27 | Crew + tool + OpenAI instrumentation | ✅ Done | `crew_timing.py`, `tool_metrics.py`, OpenAI v2 |
| 28 | SQLite `run_metrics` rollup | ✅ Done | `run_metrics_db.py`, `run_collector.py` |
| 29 | Prometheus + Grafana dev stack | ✅ Done | `docker-compose.observability.yml`, dashboard JSON |
| 30 | MCP run metrics query tools | ✅ Done | `access_audit_server.py` |

---

## What Was Built

### Flow (`CAIChatFlow`)

| Step | Decorator | Purpose |
|------|-----------|---------|
| `greet_and_intake` | `@start()` | Warm EN/FR greeting when `is_session_start=true` |
| `classify_scope` | `@listen` | `scope_classifier` — CAI-only gate |
| `route_scope` | `@router` | Branch: `"in_scope"` \| `"refuse"` |
| `scope_refusal` | `@listen("refuse")` | Scope refusal; no crew / no RAG |
| `run_CAI_crew` | `@listen("in_scope")` | Kicks off `CAISupportCrew` |
| `assemble_chat_response` | `@listen` | Greeting + crew output → `ChatResponse` |

### Crew (`CAISupportCrew`)

Sequential pipeline:

`triage_task` → `retrieve_task` → `insurer_validate_task` → `training_task` → `respond_task` → `sentiment_task` → `ticket_task` → `handoff_task` → `copilot_task`

### Intent domains (triage)

| User domain | Triage `intent` | Example query |
|-------------|-----------------|---------------|
| UserManagement | `user_management` | "How do I reactivate a deactivated user?" |
| OCF_Submission | `ocf_submission` | "How do I submit an OCF-18?" |
| OCF_Adjudication | `ocf_adjudication` | "What does an adjudication reason code mean?" |

### API surface

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness check |
| `/chat` | POST | Run Flow + crew |
| `/docs` | GET | FastAPI Swagger UI (auto-generated) |
| `/chat/stream` | POST | SSE progress + result | Implemented |

---

## Audit Trail (F10 Minimal)

| Component | Path / command | Notes |
|-----------|----------------|-------|
| SQLite store | `data/chat_audit.db` | `CHAT_AUDIT_DB_PATH` |
| Init CLI | `init-access-audit-db` | Creates `chat_audit_log` with `created_datetime` |
| MCP server | `access-audit-mcp` | stdio; tools: `log_chat_audit`, `query_chat_audit`, `get_chat_audit_by_id`, `get_chat_audit_by_run_id`, `audit_summary` |
| API hook | `api/app.py` | `log_chat_exchange()` on `/chat` and `/chat/stream` |

**Table `chat_audit_log` columns:** `id`, `run_id`, `session_id`, `user_query`, `api_response`, `portal`, `intent`, `in_scope`, `scope_rejection_reason`, `guardrail_blocked`, `guardrail_rule_id`, `tone_check_passed`, `case_number`, `created_datetime`

---

## Validation Completed (2026-06-20)

| Test | Result |
|------|--------|
| Package install (`pip install -e .`) | ✅ Pass |
| Imports (`CAIChatFlow`, `CAISupportCrew`, `app`) | ✅ Pass |
| Crew init (9 agents, 9 tasks) | ✅ Pass |
| Scope classifier — out-of-scope weather query | ✅ `in_scope=false` |
| Scope classifier — user management query | ✅ `intent=user_management` |
| Flow scope refusal + session greeting | ✅ Pass |
| `GET /health` | ✅ `{"status":"ok","service":"multiagentchat"}` |
| `POST /chat` scope refusal (no LLM required) | ✅ HTTP 200, `in_scope=false` |
| `init-access-audit-db` | ✅ Creates SQLite schema with `created_datetime` |
| Audit insert + query round-trip | ✅ Pass |

---

## Known Gaps / Blockers

1. **No root route** — use `http://127.0.0.1:8000/health` or `/docs`, not `/`.
2. **PDF corpus** — add manuals to `knowledge/pdf_fac_data/` and `knowledge/pdf_ins_data/`, then run `python scripts/build_kb.py`.
3. **ServiceNow** — `servicenow_case_api` stub returns `case_number: null`.
4. **Windows console** — CrewAI emoji logging may show `charmap` encoding warnings; core behavior unaffected.
5. **Audit retention** — 90-day purge by `session_id` not yet automated (manual SQLite maintenance).

---

## Spec Sync Checklist

Update after each backend commit (full list in [`backend-funcional-spec.md`](backend-funcional-spec.md)):

- [ ] Request/response schemas match `schemas/chat.py`
- [ ] Flow steps match `flows/CAI_chat_flow.py`
- [ ] Agent IDs and task order match `config/agents.yaml` / `config/tasks.yaml`
- [ ] Guardrails match `guardrails/` + task bindings
- [ ] KB intent map matches `scripts/build_kb.py`
- [ ] Greeting templates match `flows/greeting.py`
- [ ] `.env.example` lists all required env vars
- [ ] `backend.md` Audit block updated
- [ ] **This file (`backend-plan.md`) execution checklist updated**

---

## Next Steps

1. Add AI PDF manuals and run `python scripts/build_kb.py`.
2. Set `OPENAI_API_KEY` in `multiagentchat/.env`.
3. Smoke-test in-scope queries via `POST /chat` or `/docs`.
4. Hand off to `@integration.eng` for frontend wiring.
5. Tick Spec Sync and execution checklist items after each commit.

---

## Sources

| # | Source | Use |
|---|--------|-----|
| 1 | `project-context/1.define/prd.md` | Agent catalog, guardrails F14 |
| 2 | `project-context/1.define/sad.md` | Crew spec §2, API §4.1 |
| 3 | MultiAgentChat Backend Plan (2026-06-20) | Original implementation contract |
| 4 | [`backend-funcional-spec.md`](backend-funcional-spec.md) | Functional contract |
| 5 | [`backend.md`](backend.md) | Build artifact |

---

## Assumptions

1. Bundled PDF corpus is the MVP knowledge source; CAIInfo.ca crawler is deferred.
2. Full nine-agent pipeline runs sequentially; ticket and copilot tasks use stubs until integration epic.
3. `OPENAI_API_KEY` required for LLM and embeddings on in-scope crew runs.

---

## Open Questions

| ID | Question | Owner |
|----|----------|-------|
| OQ-BE-1 | SSE `/chat/stream` required for P0 demo vs sync REST | @integration.eng | **Resolved** |
| OQ-BE-2 | When to replace PDF citations with CAIInfo.ca URLs | @backend.eng |
| OQ-BE-3 | Production OTLP backend selection | @backend.eng |

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02 |
| **Persona** | @backend.eng |
| **Action** | OTel-first observability epic — run_id, spans, SSE product events, audit run_id, Portkey optional |
| **Outputs** | `observability/`, `docs/observability.md`, `docker/`, updated API/audit/MCP |
| **Module status** | Observability shipped; PDF indexing + live LLM E2E pending |
