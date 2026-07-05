# Backend Build Artifact — CAI Chat Workflow

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @backend.eng  
**Epic:** Backend (`*develop-be`)  
**Status:** Module 1 complete — MVP Flow + Crew ready for integration handoff; SQLite audit MCP (F10 minimal) implemented

---

## Summary

CrewAI **Flow** (`CAIChatFlow`) orchestrates session greeting, scope gating, and the full **SAD nine-agent sequential crew** (`CAISupportCrew`). Knowledge retrieval uses bundled PDF manuals indexed into **ChromaDB**. Guardrails enforce CAI-only scope, citation grounding, professional tone, and PII scrubbing. FastAPI exposes `GET /health` and `POST /chat`.

Functional specification: [`backend-funcional-spec.md`](backend-funcional-spec.md)  
Progress tracker: [`backend-plan.md`](backend-plan.md)

---

## Progress (2026-06-20)

**Module 1 — Core Configuration:** complete  
**Module 2 — API:** `/health` and `/chat` implemented; scope-refusal path validated  
**Pending:** PDF corpus indexing, in-scope crew E2E with live LLM

| # | Task | Status |
|---|------|--------|
| 1 | `backend-funcional-spec.md` | ✅ Done |
| 2 | Scaffold `multiagentchat/` | ✅ Done |
| 3 | PDF KB + ChromaDB indexer | ✅ Done (code); ⬜ corpus not indexed |
| 4 | Tools (scope, RAG, PII, tone, SN stub) | ✅ Done |
| 5 | Guardrails (triage + respond) | ✅ Done |
| 6 | Nine-agent crew (YAML + `crew.py`) | ✅ Done |
| 7 | `CAIChatFlow` | ✅ Done |
| 8 | FastAPI `/health`, `/chat` | ✅ Done |
| 9 | `backend.md` + `backend-plan.md` | ✅ Done |
| 10 | SQLite audit log + MCP server (F10 minimal) | ✅ Done |
| 11 | Index PDFs + `build_kb.py` run | ⬜ Pending |
| 12 | In-scope E2E crew run (live LLM) | ⬜ Pending |
| 13 | ServiceNow / copilot / crawler | ⬜ Deferred |

Full checklist: [`backend-plan.md`](backend-plan.md)

### Intent domains (triage)

| Domain | `intent` | Example |
|--------|----------|---------|
| UserManagement | `user_management` | Reactivate a deactivated user |
| OCF_Submission | `ocf_submission` | Submit an OCF-18 |
| OCF_Adjudication | `ocf_adjudication` | Adjudication reason codes |

### Validation completed

| Test | Result |
|------|--------|
| `pip install -e .` | ✅ Pass |
| Imports (`CAIChatFlow`, `CAISupportCrew`, `app`) | ✅ Pass |
| Crew init (9 agents, 9 tasks) | ✅ Pass |
| Scope classifier (out-of-scope / user_management) | ✅ Pass |
| Flow scope refusal + session greeting | ✅ Pass |
| `GET /health` | ✅ Pass |
| `POST /chat` scope refusal (no LLM) | ✅ Pass |

### Next steps

1. Add PDF manuals to `knowledge/pdf_fac_data/` and `knowledge/pdf_ins_data/`; run `python scripts/build_kb.py`.
2. Set `OPENAI_API_KEY` in `multiagentchat/.env`.
3. Smoke-test in-scope queries via `POST /chat` or `/docs`.
4. Hand off to `@integration.eng` for frontend wiring.

---

## API Endpoints

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | ✅ Implemented (async) | Liveness check |
| `/chat` | POST | ✅ Implemented (async) | Flow + crew via `kickoff_async`; scope refusal validated |
| `/docs` | GET | ✅ Auto | FastAPI Swagger UI |
| `/` | — | N/A | Returns 404 — use `/health` or `/docs` |

---

## Technology Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Runtime | CrewAI Flow + Crew | `AAMAD_TARGET_RUNTIME=crewai` |
| Orchestration | `CAIChatFlow` | Greeting, scope router, crew kickoff |
| Agents | 9 sequential agents | SAD §2.1; YAML externalized |
| Knowledge | ChromaDB + OpenAI embeddings | Bundled PDF corpus |
| API | FastAPI + Uvicorn | SAD §4.1 `/chat` schema; async handlers + `kickoff_async` |
| Audit | SQLite + MCP (stdio) | F10 minimal + `run_id` per exchange |
| Observability | OpenTelemetry SDK + OTLP | Collector → Jaeger (traces) + Prometheus (metrics); optional Portkey gateway |
| LLM | OpenAI `gpt-4o-mini` | Temperature 0.2; optional Portkey routing |

**Deferred:** CAIInfo.ca crawler, ServiceNow live API, copilot RBAC routes, WebSocket progress, Azure Canada deploy

---

## Application Structure

```
multiagentchat/
  scripts/build_kb.py
  src/multiagentchat/
    main.py                    # Flow CLI entry
    crew.py                    # CAISupportCrew (9 agents)
    config/agents.yaml
    config/tasks.yaml
    flows/
      CAI_chat_flow.py        # CAIChatFlow
      greeting.py
      response_parser.py
    schemas/chat.py            # ChatRequest, ChatResponse
    tools/                     # vector_search, scope_classifier, etc.
    guardrails/                # triage + respond guardrails
    kb/                        # Chroma client, intent mapping
    audit/                     # SQLite audit store (F10 minimal)
      sqlite_db.py
      logger.py
      models.py
      cli.py
    mcp/
      access_audit_server.py   # MCP tools for audit query/log
    observability/             # OTel traces + metrics, pricing, run_metrics store
    api/app.py                 # FastAPI gateway; run_id, SSE, X-Run-Id
  docker/
    otel-collector-config.yaml
    docker-compose.observability.yml
  docs/observability.md
  knowledge/
    pdf_fac_data/
    pdf_ins_data/
```

---

## Flow Pipeline

| Step | Action |
|------|--------|
| `greet_and_intake` | Warm professional greeting when `is_session_start=true` |
| `classify_scope` | `scope_classifier` tool — CAI-only gate |
| `route_scope` | Out-of-scope → refusal; in-scope → crew |
| `run_CAI_crew` | Full 9-agent sequential pipeline |
| `assemble_chat_response` | Merge greeting + crew output → `ChatResponse` |

---

## Crew Pipeline (9 Agents)

| Order | Task | Agent |
|-------|------|-------|
| 1 | `triage_task` | `triage_agent` |
| 2 | `retrieve_task` | `facility_CAI_knowledge_agent` |
| 3 | `insurer_validate_task` | `insurer_CAI_knowledge_agent` |
| 4 | `training_task` | `training_guide_agent` |
| 5 | `respond_task` | `response_agent` |
| 6 | `sentiment_task` | `sentiment_escalation_agent` |
| 7 | `ticket_task` | `ticket_agent` (stub) |
| 8 | `handoff_task` | `handoff_agent` |
| 9 | `copilot_task` | `copilot_agent` (stub) |

---

## Observability

OTel-first stack with backend-generated **`run_id`** (Option B) as the single correlation id:

| Layer | Mechanism |
|-------|-----------|
| Operational | OTel spans (`chat.request` → flow → crew tasks → tools); OTLP export when `OTEL_ENABLED=1` |
| Metrics | OTel histograms/counters → Prometheus/Grafana; SQLite `run_metrics` per run |
| Product | SSE `run_started` + progress events with safe summaries on `/chat/stream` |

- Response header: `X-Run-Id` on `/chat` and `/chat/stream`
- `ChatResponse.run_id` echoed in JSON
- Audit column: `run_id` (unique index)
- Dev stack: `docker compose -f docker/docker-compose.observability.yml up` — Jaeger `:16686`, Prometheus `:9090`, Grafana `:3001` — see `multiagentchat/docs/observability.md`

---

## Audit Trail (F10 Minimal)

SQLite-backed audit logging ships with the MVP backend. Each `/chat` and `/chat/stream` interaction persists:

| Column | Description |
|--------|-------------|
| `run_id` | Server-generated UUID per request (unique business key) |
| `session_id` | Client session identifier |
| `user_query` | Raw user message |
| `api_response` | JSON-serialized `ChatResponse` |
| `portal`, `intent` | Triage classification |
| `in_scope`, `scope_rejection_reason` | Scope guardrail outcome |
| `guardrail_blocked`, `guardrail_rule_id`, `tone_check_passed` | Respond guardrails |
| `case_number` | ServiceNow Case linkage (stub until integration) |
| `created_datetime` | UTC ISO-8601 timestamp (auto-set on insert) |

**Database:** `multiagentchat/data/chat_audit.db` (override via `CHAT_AUDIT_DB_PATH`)

**Init:**

```bash
init-access-audit-db
# or: python -m multiagentchat.audit.cli
```

**MCP server** (`access-audit-mcp` — stdio transport for Cursor / Claude Desktop):

| Tool | Purpose |
|------|---------|
| `log_chat_audit` | Manually log query + response |
| `query_chat_audit` | Filter by `session_id`, `run_id`, `since`, `limit` |
| `get_chat_audit_by_id` | Fetch one record by auto-increment id |
| `get_chat_audit_by_run_id` | Fetch one record by `run_id` |
| `audit_summary` | Human-readable compliance summary |

| Resource | Purpose |
|----------|---------|
| `audit://schema` | SQLite DDL for `chat_audit_log` |

**Env vars:** `CHAT_AUDIT_ENABLED`, `CHAT_AUDIT_DB_PATH`, `CHAT_AUDIT_AUTO_INIT` (see `.env.example`)

**FastAPI:** `app.py` calls `log_chat_exchange()` after each successful chat response when audit is enabled.

---

| Guardrail | Location |
|-----------|----------|
| CAI scope | Flow `classify_scope` + `triage_task` guardrail |
| Grounding / citations | `respond_task` guardrail |
| Professional tone | `tone_validator` tool + greeting templates |
| PII scrub | `pii_scrubber` tool on respond |

---

## Knowledge Base

- Indexer: `python scripts/build_kb.py`
- Collections: `CAI_kb` in `.chroma/`
- Intent tags: `user_management`, `ocf_submission`, `ocf_adjudication`, `general`
- Portal tags: `facilities`, `insurers`

---

## Local Development

```bash
cd multiagentchat
python -m venv .venv
.venv\Scripts\activate
pip install -e .
copy .env.example .env   # set OPENAI_API_KEY + CHAT_AUDIT_* vars
init-access-audit-db     # create SQLite audit DB (optional; API auto-inits)
python scripts/build_kb.py
python -m multiagentchat.main
uvicorn multiagentchat.api.app:app --reload --port 8000
# MCP audit server (separate process for Cursor):
access-audit-mcp
```

---

## Known Gaps

1. **No root route** — `/` returns 404; use `/health` or `/docs`.
2. **PDF corpus** — Place manuals in `knowledge/pdf_*_data/`; indexer skips if empty.
3. **ServiceNow** — `servicenow_case_api` returns stub `{ case_number: null, stub: true }`.
4. **Copilot** — Internal `/internal/copilot/*` routes not implemented.
5. **CAIInfo.ca URLs** — Citations use `file://` paths until crawler epic.
6. **Session tracker** — In-memory first-message detection; audit rows persisted in SQLite (F10 minimal).
7. **Windows console** — CrewAI emoji logging may show `charmap` warnings; behavior unaffected.

---

## Sources

| # | Source |
|---|--------|
| 1 | `project-context/1.define/prd.md` |
| 2 | `project-context/1.define/sad.md` |
| 3 | `project-context/2.build/backend-funcional-spec.md` |
| 4 | `project-context/2.build/backend-plan.md` |
| 5 | `.cursor/rules/adapter-crewai.mdc` |

---

## Assumptions

1. `OPENAI_API_KEY` available for LLM and embeddings.
2. Bundled PDFs are MVP knowledge source per plan confirmation.
3. Full nine-agent pipeline runs sequentially including stub ticket/copilot tasks.

---

## Open Questions

| ID | Question | Owner |
|----|----------|-------|
| OQ-BE-1 | SSE `/chat/stream` for P0 demo | @integration.eng | **Resolved** |
| OQ-BE-2 | CAIInfo.ca crawler replacement timeline | @backend.eng |
| OQ-BE-3 | Production OTLP backend | @backend.eng |

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02 |
| **Persona** | @backend.eng |
| **Action** | OTel-first observability — run_id, spans, SSE product events, audit run_id |
| **Runtime** | `AAMAD_TARGET_RUNTIME=crewai` |
| **Outputs** | `observability/`, `docs/observability.md`, `docker/`, updated API/audit/MCP/frontend integration |
| **Module status** | Observability epic complete; PDF indexing + live LLM E2E pending |
| **Model** | `gpt-4o-mini`, temperature 0.2 |
| **Prompt Trace** | Operational tracing via OTel; product progress via SSE |
