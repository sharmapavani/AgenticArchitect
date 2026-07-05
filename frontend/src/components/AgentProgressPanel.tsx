"use client";

import type { AgentProgressState, AgentStepStatus, RunState } from "@/types/run";

interface AgentProgressPanelProps {
  phase: RunState;
  progress: AgentProgressState;
  readOnly?: boolean;
}

function stepIndicator(status: AgentStepStatus): {
  dotClass: string;
  label: string;
} {
  switch (status) {
    case "active":
      return {
        dotClass: "bg-blue-500 animate-pulse",
        label: "In progress",
      };
    case "completed":
      return {
        dotClass: "bg-green-500",
        label: "Completed",
      };
    case "skipped":
      return {
        dotClass: "bg-slate-300",
        label: "Skipped",
      };
    default:
      return {
        dotClass: "bg-slate-300",
        label: "Pending",
      };
  }
}

function formatDuration(seconds?: number): string | null {
  if (seconds === undefined) return null;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

export function AgentProgressPanel({
  phase,
  progress,
  readOnly = false,
}: AgentProgressPanelProps) {
  const hasFlowSteps = progress.flowSteps.length > 0;
  const hasAgentSteps = progress.agentSteps.length > 0;
  const showPanel =
    phase === "running" ||
    (phase === "done" && (hasFlowSteps || hasAgentSteps || progress.crewSkipped));

  if (!showPanel) {
    if (readOnly && phase === "done") {
      return (
        <section
          aria-labelledby="agent-progress-heading"
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <h2
            id="agent-progress-heading"
            className="text-base font-semibold text-slate-900"
          >
            Agent progress
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Progress not recorded for this run.
          </p>
        </section>
      );
    }
    return null;
  }

  const activeAgent = progress.agentSteps.find((s) => s.status === "active");

  return (
    <section
      aria-labelledby="agent-progress-heading"
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <h2
        id="agent-progress-heading"
        className="text-base font-semibold text-slate-900"
      >
        Agent progress
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Live status for each agent in the CAI crew pipeline
      </p>

      {hasFlowSteps && (
        <div className="mt-4">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Flow
          </h3>
          <ol
            className="mt-2 flex flex-wrap gap-2"
            role="list"
            aria-label="Workflow flow steps"
          >
            {progress.flowSteps.map((step) => (
              <li
                key={step.step}
                role="listitem"
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                  step.status === "completed"
                    ? "bg-green-50 text-green-800"
                    : step.status === "active"
                      ? "bg-blue-50 text-blue-800"
                      : "bg-slate-100 text-slate-600"
                }`}
              >
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    step.status === "completed"
                      ? "bg-green-500"
                      : step.status === "active"
                        ? "bg-blue-500 animate-pulse"
                        : "bg-slate-400"
                  }`}
                  aria-hidden="true"
                />
                {step.label}
              </li>
            ))}
          </ol>
        </div>
      )}

      {progress.crewSkipped && (
        <p
          className="mt-4 text-sm text-slate-600"
          role="status"
          aria-live="polite"
        >
          Crew pipeline skipped — query was out of CAI scope.
        </p>
      )}

      {hasAgentSteps && (
        <div className="mt-4">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Crew agents
          </h3>
          <ol
            className="mt-2 space-y-2"
            role="list"
            aria-label="Crew agent progress"
            aria-live="polite"
          >
            {progress.agentSteps.map((step) => {
              const indicator = stepIndicator(step.status);
              const duration = formatDuration(step.durationS);
              return (
                <li
                  key={step.taskId}
                  role="listitem"
                  className={`flex items-start gap-3 rounded-md border px-3 py-2 ${
                    step.status === "active"
                      ? "border-blue-200 bg-blue-50"
                      : step.status === "completed"
                        ? "border-green-200 bg-green-50/50"
                        : "border-slate-200 bg-slate-50"
                  }`}
                  aria-current={step.status === "active" ? "step" : undefined}
                >
                  <span
                    className={`mt-1.5 inline-block h-2.5 w-2.5 shrink-0 rounded-full ${indicator.dotClass}`}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-900">
                      {step.label}
                    </p>
                    <p className="text-xs text-slate-500">
                      {step.taskId} · {step.agentId}
                    </p>
                    {step.description && (
                      <p className="mt-0.5 text-xs text-slate-600">
                        {step.description}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <span className="sr-only">{indicator.label}</span>
                    {duration && (
                      <span className="text-xs font-medium text-slate-600">
                        {duration}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {phase === "running" && activeAgent && (
        <p className="mt-3 text-xs text-blue-700" role="status">
          Currently running: {activeAgent.label}
        </p>
      )}
    </section>
  );
}
