import type { RunState } from "@/types/run";

export type CrewDisplayStatus = RunState | "error";

export const CREW_STATUS_LABEL: Record<CrewDisplayStatus, string> = {
  idle: "idle",
  running: "running",
  done: "done",
  error: "error",
};

export function crewBannerText(status: CrewDisplayStatus): string {
  return `Crew: ${CREW_STATUS_LABEL[status]}`;
}

export function resolveCrewDisplayStatus(
  phase: RunState,
  error?: string
): CrewDisplayStatus {
  if (error) return "error";
  return phase;
}

export const CREW_STATUS_PILL: Record<
  CrewDisplayStatus,
  { dot: string; banner: string; text: string }
> = {
  idle: {
    dot: "bg-slate-400",
    banner: "border-slate-200 bg-slate-50",
    text: "text-slate-800",
  },
  running: {
    dot: "bg-blue-500",
    banner: "border-blue-200 bg-blue-50",
    text: "text-blue-900",
  },
  done: {
    dot: "bg-green-500",
    banner: "border-green-200 bg-green-50",
    text: "text-green-900",
  },
  error: {
    dot: "bg-red-500",
    banner: "border-red-200 bg-red-50",
    text: "text-red-900",
  },
};

export const CREW_MESSAGES = {
  resultsIdle:
    "Crew is idle. Enter a question and press Run.",
  resultsRunning: "Crew is running…",
  resultsDone: "Crew is done. Results are ready below.",
  runButton: "Run",
  resetButton: "Reset",
  retryButton: "Retry",
} as const;

export function formatLastUpdated(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-CA", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}
