import type { Page, Route } from "@playwright/test";

export const MOCK_RUN_ID = "playwright-run-001";
export const MOCK_SESSION_ID = "playwright-session-001";

function sseBlock(data: Record<string, unknown>): string {
  return `data: ${JSON.stringify(data)}\n\n`;
}

const correlation = {
  run_id: MOCK_RUN_ID,
  session_id: MOCK_SESSION_ID,
};

export function buildScopeRefusalSseBody(): string {
  return [
    sseBlock({ type: "run_started", message: "Run started", ...correlation }),
    sseBlock({
      type: "flow_step",
      step: "classify_scope",
      status: "completed",
      ...correlation,
    }),
    sseBlock({
      type: "pipeline",
      total_tasks: 0,
      tasks: [],
      ...correlation,
    }),
    sseBlock({
      type: "result",
      payload: {
        answer:
          "I can only assist with CAI and NYC auto insurance health claims topics. For other questions, please contact Support Team support.",
        citations: [],
        in_scope: false,
        scope_refusal_reason: "off_topic_or_political",
        session_id: MOCK_SESSION_ID,
        run_id: MOCK_RUN_ID,
        tone_check_passed: true,
      },
      ...correlation,
    }),
  ].join("");
}

export function buildInScopeSseBody(options?: { delayMs?: number }): string {
  const delayMs = options?.delayMs ?? 0;
  const events = [
    sseBlock({ type: "run_started", message: "Run started", ...correlation }),
    sseBlock({
      type: "pipeline",
      total_tasks: 2,
      tasks: [
        { task_id: "triage_task", agent_id: "triage_agent", label: "Triage" },
        {
          task_id: "respond_task",
          agent_id: "response_agent",
          label: "Compose response",
        },
      ],
      ...correlation,
    }),
    sseBlock({
      type: "agent_task",
      task_id: "triage_task",
      agent_id: "triage_agent",
      label: "Triage",
      index: 1,
      total: 2,
      status: "started",
      ...correlation,
    }),
    sseBlock({
      type: "agent_task",
      task_id: "triage_task",
      agent_id: "triage_agent",
      label: "Triage",
      index: 1,
      total: 2,
      status: "completed",
      duration_s: 1.2,
      ...correlation,
    }),
    sseBlock({
      type: "agent_task",
      task_id: "respond_task",
      agent_id: "response_agent",
      label: "Compose response",
      index: 2,
      total: 2,
      status: "started",
      ...correlation,
    }),
    sseBlock({
      type: "agent_task",
      task_id: "respond_task",
      agent_id: "response_agent",
      label: "Compose response",
      index: 2,
      total: 2,
      status: "completed",
      duration_s: 2.5,
      ...correlation,
    }),
    sseBlock({
      type: "result",
      payload: {
        answer: "To reactivate a deactivated user, follow the facility user management procedure in AI.",
        citations: [
          {
            url: "file://knowledge/Managing-Users.pdf#page=1",
            title: "Managing-Users.pdf p.1",
          },
        ],
        workflow_map: {
          workflow: "User reactivation",
          impacted_ocf: null,
          suggested_next_action: "Contact facility admin if access remains blocked.",
        },
        in_scope: true,
        intent: "user_management",
        portal: "facilities",
        session_id: MOCK_SESSION_ID,
        run_id: MOCK_RUN_ID,
        tone_check_passed: true,
        escalate: false,
      },
      ...correlation,
    }),
  ].join("");

  if (delayMs <= 0) return events;

  // For reset-during-run: caller handles delayed fulfillment separately.
  return events;
}

export async function mockApiHealthOk(page: Page): Promise<void> {
  await page.route("**/api/health", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", service: "multiagentchat" }),
    });
  });
}

export async function mockApiHealthUnavailable(page: Page): Promise<void> {
  await page.route("**/api/health", async (route: Route) => {
    await route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ status: "error", detail: "Backend unavailable" }),
    });
  });
}

export async function mockChatStream(
  page: Page,
  body: string,
  options?: { status?: number; headers?: Record<string, string> }
): Promise<void> {
  await page.route("**/api/chat/stream", async (route: Route) => {
    await route.fulfill({
      status: options?.status ?? 200,
      headers: {
        "Content-Type": "text/event-stream",
        "X-Run-Id": MOCK_RUN_ID,
        ...(options?.headers ?? {}),
      },
      body,
    });
  });
}

export async function mockChatStreamDelayed(
  page: Page,
  body: string,
  delayMs: number
): Promise<void> {
  await page.route("**/api/chat/stream", async (route: Route) => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "X-Run-Id": MOCK_RUN_ID,
      },
      body,
    });
  });
}

export async function mockChatStreamError(page: Page, status = 502): Promise<void> {
  await page.route("**/api/chat/stream", async (route: Route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Backend unavailable" }),
    });
  });
}

/** Capture POST body from /api/chat/stream for payload assertions. */
export async function captureChatStreamPayload(page: Page, sseBody: string) {
  let captured: Record<string, unknown> | null = null;
  await page.route("**/api/chat/stream", async (route: Route) => {
    captured = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "X-Run-Id": MOCK_RUN_ID,
      },
      body: sseBody,
    });
  });
  return () => captured;
}
