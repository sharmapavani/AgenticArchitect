import type {
  AgentProgressState,
  AgentStep,
  AgentStepStatus,
  FlowStepName,
  FlowStepStatus,
  ProgressEvent,
} from "@/types/run";

export interface PipelineTaskMeta {
  taskId: string;
  agentId: string;
  label: string;
  description: string;
}

/** Full SAD pipeline — UI shows subset when backend reports fewer tasks. */
export const PIPELINE_TASKS: PipelineTaskMeta[] = [
  {
    taskId: "triage_task",
    agentId: "triage_agent",
    label: "CAI Intake Enrichment Agent",
    description: "Enrich portal, language, and urgency",
  },
  {
    taskId: "retrieve_task",
    agentId: "facility_CAI_knowledge_agent",
    label: "Facilities Portal RAG Specialist",
    description: "Retrieve CAI knowledge chunks",
  },
  {
    taskId: "insurer_validate_task",
    agentId: "insurer_CAI_knowledge_agent",
    label: "Insurers Portal RAG Specialist",
    description: "Validate insurer portal retrieval",
  },
  {
    taskId: "training_task",
    agentId: "training_guide_agent",
    label: "Procedural Step Extractor",
    description: "Extract numbered steps and deep links",
  },
  {
    taskId: "respond_task",
    agentId: "response_agent",
    label: "User-Facing Answer Composer",
    description: "Compose cited answer with guardrails",
  },
  {
    taskId: "sentiment_task",
    agentId: "sentiment_escalation_agent",
    label: "Quality and Escalation Gate",
    description: "Evaluate sentiment and confidence",
  },
  {
    taskId: "ticket_task",
    agentId: "ticket_agent",
    label: "ServiceNow Case Creator",
    description: "Create Case when escalation required",
  },
  {
    taskId: "handoff_task",
    agentId: "handoff_agent",
    label: "Human Context Packager",
    description: "Package handoff bundle for Support Team",
  },
  {
    taskId: "copilot_task",
    agentId: "copilot_agent",
    label: "Internal Support Copilot",
    description: "Suggest internal reply (stub)",
  },
];

const FLOW_STEP_LABELS: Record<FlowStepName, string> = {
  greet_and_intake: "Session intake",
  classify_scope: "Scope classification",
  run_CAI_crew: "Multi-agent crew",
  assemble_chat_response: "Assemble response",
  scope_refusal: "Scope refusal",
};

export function flowStepLabel(step: FlowStepName): string {
  return FLOW_STEP_LABELS[step];
}

export function buildInitialAgentProgress(): AgentProgressState {
  return {
    flowSteps: [],
    agentSteps: [],
    crewSkipped: false,
    currentSummary: undefined,
    serverRunId: undefined,
  };
}

function metaForTask(taskId: string): PipelineTaskMeta | undefined {
  return PIPELINE_TASKS.find((t) => t.taskId === taskId);
}

function buildAgentStepsFromPipeline(
  tasks: Array<{ task_id: string; agent_id: string; label: string }>
): AgentStep[] {
  return tasks.map((task) => {
    const meta = metaForTask(task.task_id);
    return {
      taskId: task.task_id,
      agentId: task.agent_id,
      label: task.label,
      description: meta?.description ?? "",
      status: "pending" as AgentStepStatus,
    };
  });
}

function setFlowStep(
  flowSteps: FlowStepStatus[],
  step: FlowStepName,
  status: "started" | "completed"
): FlowStepStatus[] {
  const existing = flowSteps.find((s) => s.step === step);
  if (existing) {
    return flowSteps.map((s) =>
      s.step === step
        ? {
            ...s,
            status: status === "completed" ? "completed" : s.status === "completed" ? "completed" : "active",
          }
        : s
    );
  }
  return [
    ...flowSteps,
    {
      step,
      label: flowStepLabel(step),
      status: status === "started" ? "active" : "completed",
    },
  ];
}

export function finalizeAgentProgress(
  state: AgentProgressState
): AgentProgressState {
  return {
    ...state,
    flowSteps: state.flowSteps.map((step) => ({
      ...step,
      status:
        step.status === "pending" || step.status === "active"
          ? "completed"
          : step.status,
    })),
    agentSteps: state.agentSteps.map((step) => ({
      ...step,
      status:
        step.status === "pending" || step.status === "active"
          ? "completed"
          : step.status,
    })),
  };
}

export function applyProgressEvent(
  state: AgentProgressState,
  event: ProgressEvent
): AgentProgressState {
  switch (event.type) {
    case "run_started": {
      return {
        ...state,
        serverRunId: event.run_id,
        currentSummary: event.message,
      };
    }
    case "pipeline": {
      if (event.total_tasks === 0) {
        return {
          ...state,
          crewSkipped: true,
          agentSteps: [],
        };
      }
      return {
        ...state,
        crewSkipped: false,
        agentSteps: buildAgentStepsFromPipeline(event.tasks),
      };
    }
    case "flow_step": {
      return {
        ...state,
        currentSummary: event.summary ?? flowStepLabel(event.step),
        flowSteps: setFlowStep(state.flowSteps, event.step, event.status),
      };
    }
    case "agent_task": {
      const agentSteps = state.agentSteps.length
        ? [...state.agentSteps]
        : buildAgentStepsFromPipeline(
            PIPELINE_TASKS.slice(0, event.total).map((t) => ({
              task_id: t.taskId,
              agent_id: t.agentId,
              label: t.label,
            }))
          );

      const updated = agentSteps.map((step, idx) => {
        if (idx !== event.index) {
          if (idx < event.index && step.status !== "completed") {
            return { ...step, status: "completed" as AgentStepStatus };
          }
          return step;
        }
        if (event.status === "started") {
          return { ...step, status: "active" as AgentStepStatus };
        }
        return {
          ...step,
          status: "completed" as AgentStepStatus,
          durationS: event.duration_s,
          cumulativeS: event.cumulative_s,
        };
      });

      return { ...state, agentSteps: updated, currentSummary: event.summary ?? event.label };
    }
    default:
      return state;
  }
}
