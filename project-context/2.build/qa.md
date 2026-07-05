# QA Build Artifact — CAI Pilot

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @qa.eng  
**Epic:** QA (`*qa`)  
**Status:** Module 4 validation complete + Playwright UI (2026-07-02)

**Full test plan and results:** [`qa-plan.md`](qa-plan.md)

---

## Summary

MVP chat pipeline validated end-to-end: scope guardrails, 6-task crew (default), 9-task crew (full pipeline), FastAPI endpoints, SSE progress, frontend Critical Research Workflow, SQLite audit, Prometheus metrics, and **Playwright UI automation**.

**Conditional Go** for capstone demo. Open issues: French scope classification (ISS-002), SSE citation intermittency (ISS-001), latency vs KPI-7 (ISS-003).

---

## Test Results Overview

| Layer | Pass | Partial | Fail | Skip |
|-------|------|---------|------|------|
| API | 11 | 1 | 1 | 0 |
| Agents | 11 | 1 | 1 | 0 |
| Frontend (manual) | 10 | 0 | 0 | 1 |
| **Playwright UI** | **10** | 0 | 0 | 0 |
| E2E | 5 | 0 | 0 | 1 |

---

## Run Tests

```bash
# API + agents
cd multiagentchat && py -3.13 scripts/qa_run_tests.py

# Playwright UI (mocked SSE, ~8s)
cd frontend && npm run test:e2e:smoke

# Playwright live integration (backend :8000 required)
cd frontend && npm run test:e2e:integration
```

---

## Critical Issues

| ID | Summary |
|----|---------|
| ISS-002 | French-only queries fail scope without English CAI keywords (F3) |
| ISS-001 | SSE path sometimes returns 0 citations (citation_formatter JSON errors) |
| ISS-003 | Crew latency ~125s median vs 15s KPI target |

---

## Deferred Testing

- ServiceNow live API, copilot RBAC, `/chat/escalate`
- Golden-set SME citation accuracy (KPI-2)
- Backend pytest suite
- Playwright live in-scope crew (`@slow` nightly)
- OTel Jaeger E2E (server had OTEL_ENABLED=0)

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02 |
| **Persona** | @qa.eng |
| **Action** | MVP QA + Playwright UI automation |
| **Outputs** | `qa.md`, `qa-plan.md`, `frontend/e2e/` |
