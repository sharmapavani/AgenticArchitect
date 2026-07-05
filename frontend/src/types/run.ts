export type RunState = "idle" | "running" | "done";

export interface RunInput {
  message: string;
  language: "en" | "fr";
  portalHint: "facilities" | "insurers" | "pms_vendors" | null;
}

export interface RunResult {
  answer: string;
  citations: { url: string; title: string }[];
  workflowMap?: {
    workflow: string;
    impactedOcf?: string;
    suggestedNextAction?: string;
  };
  caseNumber?: string;
  scopeRefusal?: boolean;
  scopeRefusalMessage?: string;
}

export interface RunRecord {
  runId: string;
  input: RunInput;
  status: RunState;
  startedAt: string;
  completedAt?: string;
  result?: RunResult;
}

export interface RunStatusResponse {
  status: "running" | "done";
  result?: RunResult;
}

export type FlowStepName =
  | "greet_and_intake"
  | "classify_scope"
  | "run_CAI_crew"
  | "assemble_chat_response"
  | "scope_refusal";

export type AgentStepStatus = "pending" | "active" | "completed" | "skipped";

export interface FlowStepStatus {
  step: FlowStepName;
  label: string;
  status: "pending" | "active" | "completed";
}

export interface AgentStep {
  taskId: string;
  agentId: string;
  label: string;
  description: string;
  status: AgentStepStatus;
  durationS?: number;
  cumulativeS?: number;
}

export interface AgentProgressState {
  flowSteps: FlowStepStatus[];
  agentSteps: AgentStep[];
  crewSkipped: boolean;
  currentSummary?: string;
  serverRunId?: string;
}

export interface CorrelationFields {
  run_id: string;
  session_id: string;
}

export type ProgressEvent =
  | ({
      type: "run_started";
      message: string;
    } & CorrelationFields)
  | ({
      type: "pipeline";
      total_tasks: number;
      tasks: Array<{ task_id: string; agent_id: string; label: string }>;
    } & CorrelationFields)
  | ({
      type: "flow_step";
      step: FlowStepName;
      status: "started" | "completed";
      summary?: string;
    } & CorrelationFields)
  | ({
      type: "agent_task";
      task_id: string;
      agent_id: string;
      label: string;
      index: number;
      total: number;
      status: "started" | "completed";
      summary?: string;
      duration_s?: number;
      cumulative_s?: number;
    } & CorrelationFields)
  | ({ type: "result"; payload: unknown } & CorrelationFields)
  | ({ type: "error"; message: string } & CorrelationFields);
