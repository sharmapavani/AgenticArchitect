import type { RunInput, RunResult } from "@/types/run";

export interface ChatRequestPayload {
  session_id: string;
  message: string;
  language: "en" | "fr";
  portal_hint: "facilities" | "insurers" | "pms_vendors" | null;
  channel: "chat";
  skip_rag: boolean;
  is_session_start: boolean;
  conversation_history: Array<{ role: string; content: string }>;
}

export interface ChatResponsePayload {
  answer: string;
  citations: Array<{ url: string; title: string }>;
  workflow_map?: {
    workflow: string;
    impacted_ocf?: string | null;
    portal?: string | null;
    role?: string | null;
    suggested_next_action?: string | null;
  } | null;
  confidence?: number;
  translated_from_en?: boolean;
  escalate?: boolean;
  case_number?: string | null;
  session_id: string;
  in_scope: boolean;
  scope_refusal_reason?: string | null;
  guardrail_blocked?: boolean;
  guardrail_rule_id?: string | null;
  tone_check_passed?: boolean;
  greeting_included?: boolean;
  intent?: string | null;
  portal?: string | null;
}

export function mapRunInputToChatRequest(
  input: RunInput,
  sessionId: string,
  isSessionStart: boolean
): ChatRequestPayload {
  return {
    session_id: sessionId,
    message: input.message.trim(),
    language: input.language,
    portal_hint: input.portalHint,
    channel: "chat",
    skip_rag: false,
    is_session_start: isSessionStart,
    conversation_history: [],
  };
}

export function mapChatResponseToRunResult(response: ChatResponsePayload): RunResult {
  if (!response.in_scope) {
    return {
      answer: response.answer,
      citations: [],
      scopeRefusal: true,
      scopeRefusalMessage: response.answer,
    };
  }

  const workflowMap = response.workflow_map
    ? {
        workflow: response.workflow_map.workflow,
        impactedOcf: response.workflow_map.impacted_ocf ?? undefined,
        suggestedNextAction:
          response.workflow_map.suggested_next_action ?? undefined,
      }
    : undefined;

  return {
    answer: response.answer,
    citations: response.citations ?? [],
    workflowMap,
    caseNumber: response.case_number ?? undefined,
  };
}
