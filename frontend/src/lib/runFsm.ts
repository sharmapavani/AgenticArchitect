import type { RunState } from "@/types/run";

/**
 * Tiny workflow FSM — three states only: idle → running → done.
 * Errors do not add a fourth state; failed runs return to idle with an error flag.
 */
export type RunFsmEvent = "RUN" | "COMPLETE" | "FAIL" | "RESET";

const TRANSITIONS: Record<
  RunState,
  Partial<Record<RunFsmEvent, RunState>>
> = {
  idle: { RUN: "running", RESET: "idle" },
  running: { COMPLETE: "done", FAIL: "idle", RESET: "idle" },
  done: { RUN: "running", RESET: "idle" },
};

export function nextRunPhase(
  current: RunState,
  event: RunFsmEvent
): RunState | null {
  return TRANSITIONS[current][event] ?? null;
}

export function canRun(phase: RunState): boolean {
  return phase !== "running";
}

export function canReset(phase: RunState): boolean {
  return phase === "idle" || phase === "running" || phase === "done";
}

/** MVP workflow controls — pause, cancel, retry-diff deferred. */
export const WORKFLOW_CONTROLS = ["Run", "Reset"] as const;

export type WorkflowControl = (typeof WORKFLOW_CONTROLS)[number];
