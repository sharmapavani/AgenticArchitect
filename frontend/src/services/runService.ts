import {
  mapChatResponseToRunResult,
  mapRunInputToChatRequest,
  type ChatResponsePayload,
} from "@/lib/apiMapper";
import {
  getOrCreateSessionId,
  isFirstMessageInSession,
  markMessageSent,
} from "@/lib/session";
import type { ProgressEvent, RunInput, RunResult, RunStatusResponse } from "@/types/run";

/**
 * Browser calls same-origin `/api/*` Route Handlers (see src/app/api/).
 * Handlers forward to FastAPI without Next.js rewrite proxy timeouts on long crew runs.
 */
function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    return "/api";
  }
  const backend =
    process.env.BACKEND_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
  return backend;
}

const API_BASE = resolveApiBase();

interface PendingRun {
  clientKey: string;
  serverRunId?: string;
  input: RunInput;
  startedAt: number;
  settled: boolean;
  result?: RunResult;
  error?: Error;
  abortController: AbortController;
}

const pendingRuns = new Map<string, PendingRun>();

function resolvePending(runId: string): PendingRun | undefined {
  const direct = pendingRuns.get(runId);
  if (direct) return direct;
  for (const pending of Array.from(pendingRuns.values())) {
    if (pending.clientKey === runId || pending.serverRunId === runId) {
      return pending;
    }
  }
  return undefined;
}

function registerServerRunId(pending: PendingRun, serverRunId: string): void {
  if (pending.serverRunId === serverRunId) return;
  pending.serverRunId = serverRunId;
  pendingRuns.set(serverRunId, pending);
}

function parseApiError(status: number, body: unknown): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) =>
          typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d)
        )
        .join("; ");
    }
  }
  return `Request failed (${status})`;
}

function parseSseDataLine(line: string): ProgressEvent | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data:")) return null;
  const payload = trimmed.slice(5).trim();
  if (!payload) return null;
  try {
    return JSON.parse(payload) as ProgressEvent;
  } catch {
    return null;
  }
}

function processSseEvent(
  event: ProgressEvent,
  pending: PendingRun,
  onProgress: (event: ProgressEvent) => void
): RunResult | undefined {
  if (event.type === "run_started") {
    registerServerRunId(pending, event.run_id);
  }
  onProgress(event);
  if (event.type === "result") {
    markMessageSent();
    return mapChatResponseToRunResult(event.payload as ChatResponsePayload);
  }
  if (event.type === "error") {
    throw new Error(event.message);
  }
  return undefined;
}

function processSseChunk(
  chunk: string,
  pending: PendingRun,
  onProgress: (event: ProgressEvent) => void,
  currentResult: RunResult | undefined
): RunResult | undefined {
  let result = currentResult;
  const blocks = chunk.split("\n\n");
  for (const block of blocks) {
    for (const line of block.split("\n")) {
      const event = parseSseDataLine(line);
      if (!event) continue;
      const next = processSseEvent(event, pending, onProgress);
      if (next) result = next;
    }
  }
  return result;
}

async function consumeChatStream(
  input: RunInput,
  pending: PendingRun,
  onProgress: (event: ProgressEvent) => void,
  signal?: AbortSignal
): Promise<RunResult> {
  const sessionId = getOrCreateSessionId();
  const isSessionStart = isFirstMessageInSession();
  const payload = mapRunInputToChatRequest(input, sessionId, isSessionStart);

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (response.status === 404) {
    return fetchChatBlocking(input, pending, signal);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(parseApiError(response.status, body));
  }

  const headerRunId = response.headers.get("X-Run-Id");
  if (headerRunId) {
    registerServerRunId(pending, headerRunId);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Stream response has no body");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let result: RunResult | undefined;

  while (true) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: true });
      const completeBlocks = buffer.split("\n\n");
      buffer = completeBlocks.pop() ?? "";
      for (const block of completeBlocks) {
        result = processSseChunk(`${block}\n\n`, pending, onProgress, result);
      }
    }
    if (done) break;
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    result = processSseChunk(buffer, pending, onProgress, result);
  }

  if (!result) {
    throw new Error("Stream ended without a result");
  }
  return result;
}

async function fetchChatBlocking(
  input: RunInput,
  pending: PendingRun,
  signal?: AbortSignal
): Promise<RunResult> {
  const sessionId = getOrCreateSessionId();
  const isSessionStart = isFirstMessageInSession();
  const payload = mapRunInputToChatRequest(input, sessionId, isSessionStart);

  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(parseApiError(response.status, body));
  }

  const headerRunId = response.headers.get("X-Run-Id");
  if (headerRunId) {
    registerServerRunId(pending, headerRunId);
  } else if (body && typeof body === "object" && "run_id" in body) {
    registerServerRunId(pending, String((body as { run_id: string }).run_id));
  }

  markMessageSent();
  return mapChatResponseToRunResult(body as ChatResponsePayload);
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!response.ok) return false;
    const data = (await response.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}

export async function startRun(
  input: RunInput,
  onProgress?: (event: ProgressEvent) => void
): Promise<{ runId: string }> {
  const clientKey = crypto.randomUUID();
  const abortController = new AbortController();
  const pending: PendingRun = {
    clientKey,
    input,
    startedAt: Date.now(),
    settled: false,
    abortController,
  };

  const progressHandler = onProgress ?? (() => {});

  pendingRuns.set(clientKey, pending);

  consumeChatStream(input, pending, progressHandler, abortController.signal)
    .then((result) => {
      if (abortController.signal.aborted) return;
      pending.result = result;
      pending.settled = true;
    })
    .catch((err) => {
      if (abortController.signal.aborted) {
        pending.error = new Error("Run cancelled");
      } else {
        pending.error =
          err instanceof Error ? err : new Error("Run failed");
      }
      pending.settled = true;
    });

  return { runId: clientKey };
}

/** Returns the server-assigned run_id when available (Option B). */
export function getServerRunId(runId: string): string | undefined {
  return resolvePending(runId)?.serverRunId;
}

/** Abort an in-flight POST /chat/stream when the user resets during a long crew run. */
export function cancelRun(runId: string): void {
  const pending = resolvePending(runId);
  if (!pending || pending.settled) return;
  pending.abortController.abort();
  pending.settled = true;
  pending.error = new Error("Run cancelled");
}

export async function getRunStatus(
  runId: string
): Promise<RunStatusResponse> {
  const pending = resolvePending(runId);
  if (!pending) {
    throw new Error(`Unknown run: ${runId}`);
  }

  const elapsed = Date.now() - pending.startedAt;
  if (elapsed > RUN_SERVICE_CONFIG.maxPollDurationMs) {
    pending.abortController.abort();
    pendingRuns.delete(pending.clientKey);
    if (pending.serverRunId) pendingRuns.delete(pending.serverRunId);
    throw new Error("Run timed out. The crew took too long to respond.");
  }

  if (!pending.settled) {
    return { status: "running" };
  }

  pendingRuns.delete(pending.clientKey);
  if (pending.serverRunId) pendingRuns.delete(pending.serverRunId);

  if (pending.error) {
    throw pending.error;
  }

  return { status: "done", result: pending.result };
}

/** Max wait for async backend Flow to finish (default 10 minutes). */
export const RUN_SERVICE_CONFIG = {
  pollIntervalMs: 500,
  maxPollDurationMs:
    Number(process.env.NEXT_PUBLIC_MAX_POLL_DURATION_MS) || 600_000,
};
