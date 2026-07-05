# Multi-Agent CAI Application — QA Test Plan & Results

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @qa.eng  
**Branch:** `Phase2-QA_Testing`  
**Test Date:** 2026-07-02 (Playwright added 2026-07-02)  
**Status:** Complete

**Related artifacts:** [`prd.md`](../1.define/prd.md), [`sad.md`](../1.define/sad.md), [`backend-plan.md`](backend-plan.md), [`integration-plan.md`](integration-plan.md), [`frontend-funcional-spec.md`](frontend-funcional-spec.md)

> AAMAD epics index references [`qa.md`](qa.md) — this document is the authoritative QA plan and execution log.

---

## Document Control

| Field | Value |
|-------|-------|
| **Version** | 1.1 (Playwright UI automation) |
| **Runtime** | `AAMAD_TARGET_RUNTIME=crewai` |
| **Scope** | MVP P0 — chat flow, 6-task crew (default), 9-task crew (verified), API, frontend Critical Research Workflow, **Playwright UI** |
| **Test runners** | `multiagentchat/scripts/qa_run_tests.py` (API/agents); `frontend` → `npm run test:e2e:smoke` / `test:e2e:integration` (UI) |
| **Out of scope** | ServiceNow live API, copilot UI, F9 voice, golden-set SME sign-off, pytest backend automation |

---

## Test Environment

| Component | Value | Status |
|-----------|-------|--------|
| Backend | `http://127.0.0.1:8000` (uvicorn, Python 3.13) | Running |
| Frontend | `http://localhost:3000` (Next.js 14.2.35 dev) | Running |
| ChromaDB | `multiagentchat/.chroma` — collection `CAI_kb` | **482 chunks** indexed |
| PDF corpus | 30+ manuals in `knowledge/pdf_fac_data/`, `knowledge/pdf_ins_data/` | Present |
| `OPENAI_API_KEY` | Set in `multiagentchat/.env` | Yes |
| `CREW_SKIP_SUPPORT_TASKS` | `1` (API server default); `0` (direct flow test) | Verified both |
| Observability | Jaeger :16686, Prometheus :9090, Grafana :3001 | Docker compose running |
| `OTEL_ENABLED` | `0` on API server during main test pass | Optional E2E-05 skipped |
| Audit DB | `multiagentchat/data/chat_audit.db` | **21 rows** after QA pass |
| Playwright | `@playwright/test` — dev server on **port 3099** | **10/10 smoke + 1/1 integration pass** |

---

## Executive Summary

| Category | Pass | Partial | Fail | Skip/Deferred |
|----------|------|---------|------|---------------|
| API (13) | 11 | 1 | 1 | 0 |
| Agents (13) | 11 | 1 | 1 | 0 |
| Frontend manual (11) | 10 | 0 | 0 | 1 |
| **Playwright UI (10)** | **10** | 0 | 0 | 0 |
| E2E (6) | 5 | 0 | 0 | 1 |
| **Total** | **47** | **2** | **2** | **2** |

**Go/No-Go (MVP demo):** **Conditional Go** — core chat pipeline, scope guardrails, SSE progress, audit trail, and frontend wiring are functional. Blockers for production pilot: latency (KPI-7), French scope classification (KPI-6), intermittent citation loss on SSE path (ISS-001).

---

## Test Matrix (PRD Feature → Test Case)

| PRD Feature | TC-IDs | Layer | Result |
|-------------|--------|-------|--------|
| F1 Portal-aware Q&A | API-05–07, AGT-02–06, UI-04, E2E-02 | All | Partial (citations intermittent SSE) |
| F2 RAG / KB | API-05–07, AGT-03, AGT-13 | API, Agent | Pass (482 chunks; retrieval works) |
| F3 Bilingual | API-08, UI-05 | API, UI | **Fail** (FR-only queries scope-refused) |
| F4 ServiceNow Case | AGT-08 | Agent | Stub verified (null case_number expected) |
| F5 Sentiment / escalation | AGT-07, AGT-13 | Agent | Pass |
| F6 Human handoff | AGT-09 | Agent | Pass (9-task pipeline); UI deferred |
| F7 Copilot | AGT-10 | Agent | Pass (9-task pipeline); RBAC deferred |
| F8 Training steps | AGT-05 | Agent | Pass |
| F10 Audit trail | API-13, E2E-03 | API, E2E | Pass |
| F14 Scope & tone | API-03–04, AGT-01, AGT-11–12 | API, Agent | Pass |

---

## Results Table

| TC-ID | Scenario | Expected | Actual | Status | Evidence |
|-------|----------|----------|--------|--------|----------|
| API-01 | GET /health | 200, status=ok | `{"status":"ok","service":"multiagentchat"}` | **PASS** | — |
| API-02 | POST /chat empty message | 422 | HTTP 422 | **PASS** | — |
| API-03 | Scope refusal (weather) | in_scope=false, fast | in_scope=false, 0 citations, 5.0s | **PASS** | run `9f3d18f5-…` |
| API-04 | Political query | in_scope=false | in_scope=false, reason=off_topic_or_political | **PASS** | — |
| API-05 | User management query (SSE) | intent=user_management, citations | intent=user_management, **citations=0**, 125s | **FAIL** | run `9448e309-…` |
| API-06 | OCF-18 submission (SSE) | workflow_map present | workflow=true, intent=ocf_submission, 122s | **PASS** | run `a061ab62-…` |
| API-07 | Adjudication reason code (SSE) | portal=insurers | portal=insurers, intent=ocf_adjudication, 194s | **PASS** | run `6ffa2522-…` |
| API-08 | French query | FR answer or translated_from_en | **in_scope=false** in 5.1s (scope refused) | **PARTIAL** | run `80c3496e-…` |
| API-09 | portal_hint insurers | portal=insurers | Verified in API-07 | **PASS** | — |
| API-10 | Session greeting | greeting_included=true | greeting_included=true, 130.6s (sync /chat) | **PASS** | Re-test; script timeout caused false FAIL |
| API-11 | SSE in-scope | run_started→result | 23 events, 125s | **PASS** | run `9448e309-…` |
| API-12 | SSE out-of-scope | crew skipped | 0 agent_tasks, 4.2s | **PASS** | run `6af0f4f5-…` |
| API-13 | Audit by run_id | row exists | SQLite row with matching run_id, intent, portal | **PASS** | run `9448e309-…` |
| AGT-01 | scope_classifier | refusal before crew | in_scope=false | **PASS** | — |
| AGT-02 | triage_agent | intent+portal | intent=user_management, portal=facilities | **PASS** | — |
| AGT-03 | facility_CAI_knowledge_agent | citations | citations=0 in SSE final (sync /chat returns 5) | **FAIL** | ISS-001 |
| AGT-04 | insurer_validate_task | task in SSE | insurer_validate_task completed | **PASS** | — |
| AGT-05 | training_guide_agent | step content | steps_hint=true in answer | **PASS** | — |
| AGT-06 | response_agent | answer+citations+workflow | tone=true, workflow=true; citations missing SSE | **PARTIAL** | — |
| AGT-07 | sentiment_escalation_agent | escalate flag | escalate=true | **PASS** | — |
| AGT-08 | ticket_agent (9-task) | stub Case created | servicenow_case_api stub executed; case_number=null | **PASS** | `qa_full_crew_test.py` 214s |
| AGT-09 | handoff_agent (9-task) | handoff bundle | task completed in 9-task pipeline | **PASS** | crew logs |
| AGT-10 | copilot_agent (9-task) | stub suggestion | task completed; no auto-send | **PASS** | crew logs |
| AGT-11 | Political guardrail | no generative CAI | scope refusal only (307 char template) | **PASS** | — |
| AGT-12 | PII scrubber | no health card | pii_pattern_found=false | **PASS** | — |
| AGT-13 | Low retrieval safety | safe handling | citations=5, escalate=true on OCF-9999 query | **PASS** | — |
| UI-01 | Page + health proxy | 200 | GET /api/health → 200; dev server active | **PASS** | — |
| UI-02 | Empty submit blocked | client validation | RunForm trim check + error message | **PASS** | Code review |
| UI-03 | Out-of-scope Run | scope refusal UI | Frontend SSE proxy: in_scope=false | **PASS** | run `08923556-…` |
| UI-04 | In-scope Run | progress + results | SSE agent_task events + results (integration + QA) | **PASS** | — |
| UI-05 | Language EN/FR | payload correct | RunForm language select → API | **PASS** | Code review |
| UI-06 | Portal hint | payload correct | RunForm portal dropdown | **PASS** | Code review |
| UI-07 | Reset during run | abort stream | cancelRun() AbortController | **PASS** | Code review |
| UI-08 | Retry on error | re-submit | RunErrorAlert onRetry | **PASS** | Code review |
| UI-09 | History select | read-only hydrate | useRunWorkflow selectedRunId | **PASS** | Code review |
| UI-10 | Backend down | error state | Not executed manually; **Playwright PW-06 pass** | **SKIP** / **PW PASS** | Manual skip; mocked in Playwright |
| UI-11 | npm run build | pass | Next.js 14.2.35 build succeeded | **PASS** | 2026-07-02 |
| PW-01–09 | Playwright smoke suite | UI-01–UI-09, UI-10 | 9 passed in 7.3s | **PASS** | `npm run test:e2e:smoke` |
| PW-10 | Playwright live integration | E2E-01 | 1 passed in 7.4s | **PASS** | `npm run test:e2e:integration` |
| E2E-01 | Scope refusal path | UI→SSE→audit | Frontend proxy SSE + audit rows | **PASS** | — |
| E2E-02 | Happy path in-scope | crew→history | 6-agent crew ~122–194s | **PASS** | — |
| E2E-03 | run_id correlation | SSE=response=audit | Matching run_id in all three | **PASS** | — |
| E2E-04 | session persistence | same session_id | session_id stored in audit per request | **PASS** | Audit query |
| E2E-05 | Jaeger trace | trace visible | OTEL_ENABLED=0 on server | **SKIP** | Optional |
| E2E-06 | Prometheus metrics | counter increments | 4 `chat_request_duration_seconds_count` series | **PASS** | :9090 |
| KPI-7 | Time-to-answer | <15s median | **median=125s** (122, 125, 194s) | **FAIL** | ISS-003 |

---

## Agent Test Log (6-task SSE run — user management)

| Agent | SSE Status | Duration (s) | Notes |
|-------|------------|--------------|-------|
| triage_agent | started → completed | 3.6 | intent=user_management |
| facility_CAI_knowledge_agent | started → completed | 35.5 | vector_search invoked |
| insurer_CAI_knowledge_agent | started → completed | 3.0 | validation step |
| training_guide_agent | started → completed | 16.8 | step content in answer |
| response_agent | started → completed | 47.8 | tone_check_passed=true |
| sentiment_escalation_agent | started → completed | 10.1 | escalate=true |

**9-task pipeline (CREW_SKIP_SUPPORT_TASKS=0, direct flow):** All 9 tasks including `ticket_agent` (ServiceNow stub), `handoff_agent`, `copilot_agent` completed in **214.6s**.

---

## Issues Found

| ID | Severity | Summary | Repro | Owner | Status |
|----|----------|---------|-------|-------|--------|
| ISS-001 | **Medium** | SSE `/chat/stream` final payload sometimes returns **0 citations** while sync `POST /chat` returns 5 for the same query type. Logs show intermittent `citation_formatter` JSON parse error. | Run user-management query via SSE; compare to sync /chat | @backend.eng | Open |
| ISS-002 | **High** | **French-only queries** without English CAI keywords are scope-refused (`in_scope=false`). Example: "Comment réinitialiser le mot de passe utilisateur?" fails; "Comment reactivater un utilisateur desactive pour OCF CAI?" passes. Violates F3/KPI-6. | POST /chat with pure FR password question | @backend.eng | Open |
| ISS-003 | **Medium** | **KPI-7 latency:** median crew run **125s** vs PRD target **<15s**. Dominated by LLM agent steps (response_agent ~48s, retrieve ~35s). | Any in-scope crew run | @backend.eng | Open (demo acceptable) |
| ISS-004 | **Low** | Windows console `charmap` errors on CrewAI emoji logging | Run crew on Windows CP1252 console | @backend.eng | Known |
| ISS-005 | **Low** | PRD UI gaps: no **"Talk to a human"** button; `skip_rag` always false; no translation badge, confidence, or `last_crawled_at` in UI | Inspect frontend | @frontend.eng | Deferred |
| ISS-006 | **Low** | OTel warning: `Invalid type NoneType for attribute 'run_id'` on direct flow kickoff (no API context) | `qa_full_crew_test.py` | @backend.eng | Open |

---

## KPI Snapshot

| KPI | Target | Result | Status |
|-----|--------|--------|--------|
| KPI-1 Answer rate | ≥ 80% | In-scope queries return answers; citations intermittent on SSE | **Partial** |
| KPI-2 Citation accuracy | ≥ 90% | Not SME-validated; formatter errors observed | **Deferred** |
| KPI-3 Workflow accuracy | ≥ 85% | workflow_map present on OCF queries | **Partial** |
| KPI-4 Ticket validity | 100% | Stub only — assignment_group set, case_number null | **Deferred** |
| KPI-5 Escalation appropriateness | ≥ 80% | escalate=true on low-confidence user-mgmt answer | **Partial** |
| KPI-6 Bilingual rate | ≥ 80% FR subset | Pure FR query scope-refused (ISS-002) | **Fail** |
| KPI-7 Time-to-answer median | < 15 s | **125 s** median (122–194 s range) | **Fail** |

---

## Prior Integration Results (Re-verified)

| Test | Prior (integration-plan) | QA 2026-07-02 |
|------|--------------------------|---------------|
| GET /health | Pass | **Pass** |
| Scope refusal E2E | Pass | **Pass** |
| In-scope E2E (~106s) | Pass | **Pass** (~122–194s) |
| npm run build | Pass | **Pass** |
| Audit MCP by run_id | Pending | **Pass** (SQLite direct query) |
| PDF indexing | Pending | **Pass** (482 chunks) |

---

## Frontend PRD Gap Analysis (Limitations — Not Defects)

| PRD Requirement | Status |
|-----------------|--------|
| Language EN/FR selector | Implemented |
| Portal hint dropdown | Implemented |
| Citation links in results | Implemented (when backend returns citations) |
| Workflow/impact block | Partial (portal/role not mapped in UI) |
| Case number display | Implemented (when backend returns case_number) |
| Scope refusal display | Implemented |
| SSE agent progress | Implemented |
| Session history (tab) | Implemented |
| **"Talk to a human"** | **Missing** |
| Translation badge | Missing |
| Confidence / escalation UX | Missing |
| Multi-turn conversation_history | Missing (always `[]`) |
| Copilot UI | Missing |
| Voice (F9) | Deferred |

---

## Playwright UI Automation

### Setup

```bash
cd frontend
npm install
npx playwright install chromium   # first time only
npm run test:e2e:smoke            # mocked SSE — fast (~8s)
npm run test:e2e:integration      # live backend scope refusal (~7s; requires :8000)
npm run test:e2e                  # all projects
npm run test:e2e:ui               # interactive UI mode
```

Playwright starts its own Next.js dev server on **port 3099** (configurable via `PLAYWRIGHT_PORT`) to avoid conflicts with a manual `npm run dev` on :3000.

### Architecture

| Tier | Project | Backend | Tests |
|------|---------|---------|-------|
| Smoke | `smoke` | Mocked `/api/health` + `/api/chat/stream` | UI-01–UI-10 (except UI-11 build) |
| Integration | `integration` | Live FastAPI :8000 | E2E-01 live scope refusal |

**Mock fixtures:** [`frontend/e2e/fixtures/mock-sse.ts`](../../frontend/e2e/fixtures/mock-sse.ts)

### Playwright spec map

| Spec file | TC-IDs | Status |
|-----------|--------|--------|
| `e2e/smoke/page-load.spec.ts` | UI-01 | **PASS** |
| `e2e/smoke/form-validation.spec.ts` | UI-02 | **PASS** |
| `e2e/smoke/scope-refusal.spec.ts` | UI-03 | **PASS** |
| `e2e/smoke/in-scope-mocked.spec.ts` | UI-04 | **PASS** |
| `e2e/smoke/form-payload.spec.ts` | UI-05, UI-06 | **PASS** |
| `e2e/smoke/reset-during-run.spec.ts` | UI-07 | **PASS** |
| `e2e/smoke/error-retry.spec.ts` | UI-08 | **PASS** |
| `e2e/smoke/history.spec.ts` | UI-09 | **PASS** |
| `e2e/smoke/backend-unavailable.spec.ts` | UI-10 | **PASS** |
| `e2e/integration/live-scope-refusal.spec.ts` | E2E-01 | **PASS** |

### Execution results (2026-07-02)

```
npm run test:e2e:smoke       → 9 passed (7.3s)
npm run test:e2e:integration → 1 passed (7.4s)
```

---

## Deferred / Future Work

- ServiceNow live Case API and `/chat/escalate` route
- Copilot RBAC endpoints and internal UI
- CAIInfo.ca crawler (PDF corpus used for MVP)
- Azure Speech (F9)
- Full golden-set (30–40) with Support Team SME validation
- Backend pytest automation
- Playwright **live in-scope** crew test (`@slow`, ~2 min; tag for nightly CI)
- WCAG 2.1 AA full audit
- OTel E2E with `OTEL_ENABLED=1` on API server

---

## Test Artifacts

| Artifact | Path |
|----------|------|
| Automated API/agent runner | `multiagentchat/scripts/qa_run_tests.py` |
| JSON results | `multiagentchat/scripts/qa_results.json` |
| 9-task crew test | `multiagentchat/scripts/qa_full_crew_test.py` |
| Playwright config | `frontend/playwright.config.ts` |
| Playwright smoke specs | `frontend/e2e/smoke/*.spec.ts` |
| Playwright integration specs | `frontend/e2e/integration/*.spec.ts` |
| SSE mock fixtures | `frontend/e2e/fixtures/mock-sse.ts` |

---

## Sources

| # | Source | Use |
|---|--------|-----|
| 1 | `project-context/1.define/prd.md` | Acceptance criteria, KPIs |
| 2 | `project-context/1.define/sad.md` | Agent catalog, API contract |
| 3 | `project-context/2.build/backend-plan.md` | Backend validation baseline |
| 4 | `project-context/2.build/integration-plan.md` | Prior E2E results |
| 5 | `project-context/2.build/frontend-funcional-spec.md` | UI contract |

---

## Assumptions

1. Backend and frontend dev servers were running locally during QA execution.
2. `OPENAI_API_KEY` valid for in-scope crew runs.
3. Chroma index built from bundled PDF manuals (not CAIInfo.ca crawl).
4. ServiceNow stub returning null `case_number` is expected MVP behavior, not a defect.
5. API-10 initial script failure was due to 30s timeout, not application bug.

---

## Open Questions

| ID | Question | Owner |
|----|----------|-------|
| OQ-QA-1 | Accept KPI-7 latency for capstone demo? | Pilot sponsor |
| OQ-QA-2 | Add French allow-list patterns to scope_classifier before pilot? | @backend.eng |
| OQ-QA-3 | Fix citation_formatter JSON errors before frontend SSE demo? | @backend.eng |

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02T11:15:00Z |
| **Persona** | @qa.eng |
| **Action** | Added Playwright UI automation — 9 smoke + 1 integration spec; updated qa-plan v1.1 |
| **Branch** | Phase2-QA_Testing |
| **Outputs** | `frontend/playwright.config.ts`, `frontend/e2e/**`, `project-context/2.build/qa-plan.md` |
| **Prompt Trace** | Omitted — operational test execution per AAMAD lean artifact policy |
