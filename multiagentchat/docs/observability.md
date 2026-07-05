# Observability — MultiAgentChat

Three-layer observability unified by **`run_id`** (generated in FastAPI, Option B):

| Layer | Audience | Mechanism |
|-------|----------|-----------|
| Operational traces | Developers / ops | OpenTelemetry spans → Collector → Jaeger |
| Operational metrics | Developers / ops | OTel Metrics → Collector → Prometheus → Grafana |
| Product | End users | SSE events on `POST /chat/stream` with safe summaries |
| Per-run rollup | Agents / MCP | SQLite `run_metrics` + `run_step_metrics` tables |

## Correlation IDs

| ID | Owner | Scope |
|----|-------|-------|
| `run_id` | FastAPI (`uuid.uuid4()`) | One per `/chat` or `/chat/stream` request |
| `session_id` | Frontend (`sessionStorage`) | Multi-turn conversation |
| OTel `trace_id` | Derived from `run_id` | 32 hex chars (`run_id.replace("-", "")`) |

## Local dev stack

From `multiagentchat/docker/`:

```bash
docker compose -f docker-compose.observability.yml up -d
```

Set in `multiagentchat/.env`:

```env
OTEL_ENABLED=1
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=multiagentchat
RUN_METRICS_ENABLED=1
```

Start the API:

```bash
serve
```

| UI | URL | Credentials |
|----|-----|-------------|
| Jaeger | http://localhost:16686 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / admin |

## Metrics catalog

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `chat.request.duration` | Histogram (s) | `route`, `status` | FastAPI `/chat`, `/chat/stream` |
| `chat.step.duration` | Histogram (s) | `step_type`, `step_name` | Flow, crew, tools, OpenAI |
| `chat.tokens.input` | Counter | `scope`, `step_name`, `model` | Crew kickoff + embeddings |
| `chat.tokens.output` | Counter | same | same |
| `chat.token.usage` | Counter | `scope`, `step_name`, `model` | Aggregate token counter |
| `chat.cost.usd` | Counter | `scope`, `step_name`, `model` | `observability/pricing.py` |
| `chat.runs.total` | Counter | `status` | success / error / scope_refusal |

**Run status rules:**

- `success` — `ChatResponse` returned, `in_scope=true`
- `scope_refusal` — `ChatResponse` returned, `in_scope=false`
- `error` — unhandled exception or API error path

### Prometheus metric names (OTel export)

OTel uses dotted instrument names; the collector Prometheus exporter rewrites them:

| OTel instrument | Prometheus query name |
|-----------------|----------------------|
| `chat.runs.total` | `chat_runs_total` |
| `chat.request.duration` | `chat_request_duration_seconds_bucket` / `_count` / `_sum` |
| `chat.step.duration` | `chat_step_duration_seconds_bucket` / `_count` / `_sum` |
| `chat.tokens.input` | `chat_tokens_input_total` |
| `chat.tokens.output` | `chat_tokens_output_total` |
| `chat.token.usage` | `chat_token_usage_total` |
| `chat.cost.usd` | `chat_cost_usd_total` |

### Example PromQL

```promql
# Success rate (instant — works even with 1 run)
sum(chat_runs_total{status="success"}) / sum(chat_runs_total)

# Success rate (5m rate — needs multiple scrapes)
sum(rate(chat_runs_total{status="success"}[5m])) / sum(rate(chat_runs_total[5m]))

# E2E latency p95
histogram_quantile(0.95, sum(rate(chat_request_duration_seconds_bucket[5m])) by (le))

# Token rate
sum(rate(chat_tokens_input_total[5m])) by (scope)

# Estimated cost rate (USD/s)
sum(rate(chat_cost_usd_total[5m]))
```

Prometheus scrapes the OTel Collector at `otel-collector:8889` (exposed as `:8889` on localhost).

## SQLite per-run rollup

When `RUN_METRICS_ENABLED=1`, every chat run persists to the audit DB:

**`run_metrics`** — one row per `run_id`: E2E duration, tokens, estimated cost, status, model.

**`run_step_metrics`** — N rows per run: flow/crew/tool step durations and optional token/cost.

MCP tools: `get_run_metrics(run_id)`, `query_run_metrics(...)`, `run_metrics_summary()`.

## Jaeger UI — what to expect

Jaeger shows **distributed traces (spans)**, not application stdout logs. Console lines like `run_id=...` in uvicorn output stay in the terminal; Jaeger visualizes the span tree.

In Jaeger:

1. Open http://localhost:16686
2. **Service** dropdown → select **`multiagentchat`** (not `jaeger-all-in-one`)
3. Click **Find Traces**
4. Optional: search by tag `run_id` or paste trace ID (32 hex, no hyphens)

## Troubleshooting empty Prometheus / Grafana

| Check | Fix |
|-------|-----|
| Wrong metric name in PromQL | Use `chat_runs_total` not `chat_runs_run_total`; use `chat_request_duration_seconds_count` not `chat_request_duration_count` |
| `rate()` returns no data | With only 1–2 runs, use instant queries: `sum(chat_runs_total)` or widen range to `[1h]` |
| Grafana panels empty | Restart Grafana after dashboard/datasource changes: `docker compose -f docker-compose.observability.yml restart grafana` |
| Collector has metrics but Prom doesn't | Check http://localhost:9090/targets — `otel-collector:8889` should be **UP** |
| No metrics at collector | Confirm `OTEL_ENABLED=1` in `.env` and **restart uvicorn** after chat request + wait 5s for export flush |
| Verify collector directly | `curl http://localhost:8889/metrics` — search for `chat_` |

## Troubleshooting empty Jaeger

| Check | Fix |
|-------|-----|
| Docker stack running | `docker compose -f docker-compose.observability.yml up -d` from `multiagentchat/docker/` |
| `OTEL_ENABLED=1` | In `multiagentchat/.env` — **restart uvicorn** after changing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` (Collector HTTP port) |
| Startup log | On boot you should see: `OpenTelemetry enabled — exporting traces to http://localhost:4318` |
| Wrong service in UI | Select **`multiagentchat`**, not `jaeger-all-in-one` |
| `.env` not loaded | Start backend from any cwd — app loads `multiagentchat/.env` automatically |

Quick pipeline test:

```bash
curl http://localhost:8000/health
```

Then refresh Jaeger → Service `multiagentchat` → Find Traces.

Verify Collector receives data:

```bash
curl http://localhost:16686/api/services
# Should list "multiagentchat" after at least one traced request
```

Verify Prometheus metrics after a chat request:

```bash
curl -s "http://localhost:9090/api/v1/query?query=chat_runs_total"
curl -s "http://localhost:9090/api/v1/query?query=chat_request_duration_seconds_count"
```

If those return empty, check the collector directly:

```bash
curl -s http://localhost:8889/metrics | findstr chat_
```

## Verify

1. `POST /chat/stream` — first SSE event is `run_started` with `run_id` and `session_id`.
2. Response header `X-Run-Id` on `/chat` and `/chat/stream`.
3. Audit row includes `run_id` (`CHAT_AUDIT_ENABLED=1`).
4. MCP: `query_chat_audit(run_id="...")` or `get_chat_audit_by_run_id`.
5. Prometheus: `chat_request_duration_seconds_count` increments after a chat request.
6. Grafana success-rate panel > 0% after a successful in-scope run.
7. SQLite: `run_metrics` row exists with `duration_ms`, tokens, `cost_usd`.
8. MCP: `get_run_metrics(run_id)` returns rollup matching Prometheus totals for that run.

## Span hierarchy

```
chat.request
├── flow.greet_and_intake
├── flow.classify_scope
├── flow.scope_refusal | flow.run_CAI_crew
│   └── crew.task.*
└── flow.assemble_chat_response
    └── tool.vector_search (during RAG)
```

## Pricing / cost assumptions

Cost metrics use an estimated pricing table in `observability/pricing.py` (override via `METRICS_PRICING_JSON` env). Portkey actual billing can replace estimates in production.

## Optional Portkey

When `PORTKEY_API_KEY` and `PORTKEY_BASE_URL` are set, CrewAI and embedding calls route through Portkey with `x-portkey-trace-id` derived from `run_id`.
