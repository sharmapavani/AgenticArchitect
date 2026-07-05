# Frontend Build Artifact — Critical Research Workflow

**Project:** Multi-Agent Customer Support Crew (CAI Pilot)  
**Persona:** @frontend.eng  
**Epic:** Frontend (`*develop-fe`)  
**Status:** API-integrated — `POST /chat/stream` SSE for live agent progress; sync `/chat` fallback; long-run polling + cancel on Reset

---

## Summary

Minimal Next.js 14 single-route app implementing the **Critical Research Workflow**: **Inputs**, **Run**, **Agent Progress**, **Results**, and **History**. Calls the FastAPI backend through Next.js `/api` Route Handlers. While the backend Flow runs (potentially minutes), the UI shows **live per-agent progress** via `POST /chat/stream` SSE and stays in **Crew: running** via non-blocking `fetch` + 500 ms poll until the `result` event arrives.

Functional specification: [`frontend-funcional-spec.md`](frontend-funcional-spec.md)

---

## Backend integration (async API)

| Topic | Frontend behavior |
|-------|-------------------|
| Protocol | Primary: `POST /chat/stream` SSE (`pipeline`, `flow_step`, `agent_task`, `result`, `error` events) |
| Fallback | `POST /chat` blocking JSON if stream endpoint returns 404 |
| Long runs | `startRun` consumes SSE in background; FSM polls until settled (max 10 min) |
| Cancel | **Reset** during running calls `cancelRun()` → `AbortController` aborts stream |
| Proxy | Same-origin `/api/chat/stream` Route Handler → FastAPI (no rewrite timeout on long runs) |
| Health | `useApiHealth` probes `GET /health` every 30 s; shown in page header |

**Implementation:** `frontend/src/services/runService.ts`, `frontend/src/hooks/useApiHealth.ts`

---

## Technology Stack

| Layer | Choice | Version / Notes |
|-------|--------|-----------------|
| Framework | Next.js App Router | 14.2.35 |
| Language | TypeScript (strict) | ^5 |
| UI | React | ^18 |
| Styling | Tailwind CSS | ^3.4.1 |
| State | `runFsm.ts` + `useRunWorkflow` | Three-state FSM + `agentProgress` |
| Services | `runService.ts` | SSE stream + `/chat` fallback via `/api` proxy |

**Deferred:** assistant-ui, shadcn/ui, copilot route, voice (F9)

---

## Application Structure

```
frontend/src/
  app/
    layout.tsx             # Geist fonts, page metadata
    page.tsx               # Page shell: header, banner, grid layout
    globals.css            # Tailwind base
  lib/
    runFsm.ts              # idle → running → done transitions
    crewStatus.ts          # Banner labels, pill styles, shared messages
    agentPipeline.ts       # Agent catalog, SSE event reducer
  hooks/
    useRunWorkflow.ts      # FSM orchestration, SSE progress, polling, history, retry
  services/
    runService.ts          # POST /chat/stream, POST /chat fallback, GET /health, cancelRun
  hooks/
    useApiHealth.ts        # Backend connectivity probe
  types/
    run.ts                 # RunInput, RunResult, RunRecord, RunState, ProgressEvent
  components/
    CrewStatusBanner.tsx
    AgentProgressPanel.tsx # Live per-agent step list during runs
    RunForm.tsx            # Run + Reset controls; PHI / AI disclosure copy
    RunErrorAlert.tsx      # Inline error + Retry
    RunResults.tsx         # Answer, citations, workflow map, scope refusal
    RunHistory.tsx         # Session history sidebar
```

---

## Page Layout

- **Header:** Title “Critical Research Workflow” + CAI subtitle
- **CrewStatusBanner:** Full-width status strip below header
- **Main grid (lg+):** Left column — Inputs + Agent Progress + Results; right column — History (280px)
- **History view:** Selecting a history entry hydrates Results in read-only mode (`selectedRunId`); banner shows **Crew: done**
- **Skip link:** “Skip to main content” for keyboard users

---

## Inputs (`RunInput`)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `message` | string | Yes (trim, min 1) | — |
| `language` | `'en' \| 'fr'` | Yes | `'en'` |
| `portalHint` | `'facilities' \| 'insurers' \| 'pms_vendors' \| null` | No | `null` (Auto-detect) |

Form includes PHI guidance (no names/health card numbers) and AI disclosure. Submit disabled while FSM is `running`.

**Implementation:** `frontend/src/types/run.ts`, `frontend/src/components/RunForm.tsx`

---

## Agent Progress

Live per-agent status during crew execution (SAD §2.1–2.2). Shown between Inputs and Results.

| Element | Specification |
|---------|---------------|
| Component | `AgentProgressPanel` — flow step pills + vertical agent step list |
| Data source | SSE events from `POST /chat/stream`; server `run_id` from `run_started` |
| Flow steps | Session intake, scope classification, crew pipeline, assemble response (or scope refusal) |
| Agent steps | 6 default (`CREW_SKIP_SUPPORT_TASKS=1`) or 9 full pipeline — driven by `pipeline` event |
| States | `pending`, `active` (blue pulse), `completed` (green + duration), `skipped` (scope refusal) |
| Current activity | `currentSummary` from SSE `summary` fields (safe text only) |
| History | Stores server `run_id` when resolved; progress not replayed from history |

**SSE event types:** `run_started`, `pipeline`, `flow_step`, `agent_task`, `result`, `error` (all include `run_id`, `session_id`)

**Implementation:** `frontend/src/components/AgentProgressPanel.tsx`, `frontend/src/lib/agentPipeline.ts`, `frontend/src/hooks/useRunWorkflow.ts`

---

## Controls and FSM

| Control | Behavior |
|---------|----------|
| **Run** | Submit → stub `startRun` → poll `getRunStatus` until done |
| **Reset** | Clear result/error → `idle`; **cancels in-flight fetch** if running |
| **Retry** | Error recovery only — re-submits last `RunInput` via `lastInputRef` |

| FSM phase | Banner | Allowed controls |
|-----------|--------|------------------|
| `idle` | Crew: idle (or Crew: error if `error` set) | Run, Reset |
| `running` | Crew: running | Reset (cancels request), poll only |
| `done` | Crew: done | Run, Reset |

Error display uses `resolveCrewDisplayStatus(phase, error)` — **error is not a fourth FSM state**.

**Implementation:** `frontend/src/lib/runFsm.ts`, `frontend/src/hooks/useRunWorkflow.ts`

---

## API Service Behavior

| Parameter | Value |
|-----------|-------|
| API base (default) | `/api` via Route Handlers (`app/api/chat`, `app/api/health`) |
| Backend target | `BACKEND_URL` env (default `http://127.0.0.1:8000`) |
| Poll interval | 500 ms |
| Max wait | 600 000 ms (10 min), env override |
| History key | `criticalResearchHistory` (`sessionStorage`, max 20 FIFO) |
| Health probe | Every 30 s via `useApiHealth` |

`startRun` returns client key immediately; adopts server `run_id` from `run_started` SSE or `X-Run-Id` header on sync fallback.

---

## Results

Renders `RunResult`: answer, citations, workflow map, optional `caseNumber`, scope refusal (`scopeRefusal` / `scopeRefusalMessage`). States: idle placeholder, running spinner, done success/refusal, read-only history banner.

**Implementation:** `frontend/src/components/RunResults.tsx`

---

## Accessibility (MVP)

- Semantic heading hierarchy (`h1`–`h3`)
- Skip link; `aria-labelledby` on sections
- Focus-visible rings on buttons, links, history items
- Banner: `role="status"`, `aria-live="polite"`; errors: `role="alert"`
- Workflow controls: `role="group"`, `aria-label="Workflow controls"`
- Run button: `aria-describedby="crew-status-label"`

---

## Local Development

```bash
cd frontend
npm install
npm run dev
```

Build verification: `npm run build`

---

## Smoke Test Checklist

- [x] **Run** → Crew: running → Crew: done with stub results
- [x] **Reset** returns to idle without clearing history
- [x] `[stub-error]` → inline error + **Retry** with same inputs
- [x] History entry click → read-only Results view
- [x] No pause, cancel, or retry-diff controls present
- [x] `npm run build` passes

---

## Handoff Notes (@integration.eng)

1. Swap `runService.ts` stubs for API gateway calls; keep `RunInput` / `RunResult` types aligned with SAD §4.1.
2. Preserve FSM and polling hook surface (`submit`, `reset`, `retry`) where possible.
3. SSE vs REST polling: see OQ-FE-1 in functional spec.

---

## Sources

| # | Source | Use |
|---|--------|-----|
| 1 | `project-context/1.define/prd.md` | UI requirements §6.1, F14 scope refusal |
| 2 | `project-context/1.define/sad.md` | Frontend stack §3, `/chat` schemas §4.1 |
| 3 | `.cursor/agents/frontend-eng.md` | Persona scope; no backend wiring in this epic |
| 4 | `project-context/2.build/frontend-funcional-spec.md` | Detailed UX/service contracts |
| 5 | `frontend/` implementation | Authoritative for file paths and behavior |

---

## Assumptions

1. Stub services simulate async crew execution; no real API calls in the frontend epic.
2. assistant-ui and shadcn/ui deferred; native form controls used for MVP.
3. History is session-scoped; cross-tab/device persistence is post-pilot.
4. Single route (`/`) only; copilot UI is a future route per SAD §3.2.

---

## Open Questions

| ID | Question | Owner |
|----|----------|-------|
| OQ-FE-1 | SSE streaming vs sync REST for P0 demo | **Resolved** — SSE `/chat/stream` adopted for agent progress; sync `/chat` retained as fallback |
| OQ-FE-2 | When to adopt assistant-ui for production chat UX | @frontend.eng |

---

## Audit

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-02 |
| **Persona** | @frontend.eng |
| **Action** | Observability alignment — server run_id adoption, run_started SSE, currentSummary in progress state |
| **Build** | `npm run build` — verify after changes |
| **Prompt Trace** | Product observability via SSE; correlates with backend OTel run_id |
