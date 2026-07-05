"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { applyProgressEvent, buildInitialAgentProgress, finalizeAgentProgress } from "@/lib/agentPipeline";
import { canReset, canRun, nextRunPhase } from "@/lib/runFsm";
import {
  RUN_SERVICE_CONFIG,
  cancelRun,
  getRunStatus,
  getServerRunId,
  startRun,
} from "@/services/runService";
import type {
  AgentProgressState,
  ProgressEvent,
  RunInput,
  RunRecord,
  RunResult,
  RunState,
} from "@/types/run";

const HISTORY_KEY = "criticalResearchHistory";
const MAX_HISTORY = 20;

interface WorkflowState {
  phase: RunState;
  runId?: string;
  result?: RunResult;
  error?: string;
  lastUpdatedAt: string;
  agentProgress: AgentProgressState;
}

function nowIso(): string {
  return new Date().toISOString();
}

function loadHistory(): RunRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as RunRecord[];
  } catch {
    return [];
  }
}

function saveHistory(records: RunRecord[]): void {
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(records.slice(0, MAX_HISTORY)));
}

export function useRunWorkflow() {
  const [state, setState] = useState<WorkflowState>({
    phase: "idle",
    lastUpdatedAt: "",
    agentProgress: buildInitialAgentProgress(),
  });
  const [history, setHistory] = useState<RunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastInputRef = useRef<RunInput | null>(null);
  const phaseRef = useRef<RunState>("idle");

  useEffect(() => {
    phaseRef.current = state.phase;
  }, [state.phase]);

  useEffect(() => {
    setHistory(loadHistory());
    setState((prev) => ({ ...prev, lastUpdatedAt: nowIso() }));
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const applyPhase = useCallback(
    (event: Parameters<typeof nextRunPhase>[1], patch: Partial<WorkflowState> = {}) => {
      const next = nextRunPhase(phaseRef.current, event);
      if (!next) return false;
      setState((prev) => ({
        ...prev,
        ...patch,
        phase: next,
        lastUpdatedAt: nowIso(),
      }));
      return true;
    },
    []
  );

  const touchUpdated = useCallback((patch: Partial<WorkflowState>) => {
    setState((prev) => ({ ...prev, ...patch, lastUpdatedAt: nowIso() }));
  }, []);

  const handleProgress = useCallback((event: ProgressEvent) => {
    if (event.type === "result" || event.type === "error") return;
    setState((prev) => {
      const agentProgress = applyProgressEvent(prev.agentProgress, event);
      const serverRunId =
        event.type === "run_started"
          ? event.run_id
          : agentProgress.serverRunId ?? prev.runId;
      return {
        ...prev,
        runId: serverRunId ?? prev.runId,
        agentProgress,
        lastUpdatedAt: nowIso(),
      };
    });
  }, []);

  const appendHistory = useCallback((record: RunRecord) => {
    setHistory((prev) => {
      const next = [record, ...prev.filter((r) => r.runId !== record.runId)].slice(
        0,
        MAX_HISTORY
      );
      saveHistory(next);
      return next;
    });
  }, []);

  const beginPoll = useCallback(
    (runId: string, input: RunInput, startedAt: string) => {
      stopPolling();
      const pollStartedAt = Date.now();
      pollRef.current = setInterval(async () => {
        try {
          if (Date.now() - pollStartedAt > RUN_SERVICE_CONFIG.maxPollDurationMs) {
            stopPolling();
            applyPhase("FAIL", {
              error: "Run timed out. The crew took too long to respond.",
              result: undefined,
              runId: undefined,
              agentProgress: buildInitialAgentProgress(),
            });
            return;
          }

          const status = await getRunStatus(runId);
          if (status.status === "running") {
            touchUpdated({
              phase: "running",
              runId: getServerRunId(runId) ?? runId,
            });
            return;
          }

          stopPolling();
          const completedAt = new Date().toISOString();
          const resolvedRunId = getServerRunId(runId) ?? runId;
          const record: RunRecord = {
            runId: resolvedRunId,
            input,
            status: "done",
            startedAt,
            completedAt,
            result: status.result,
          };
          appendHistory(record);
          setState((prev) => ({
            ...prev,
            phase: "done",
            runId: resolvedRunId,
            result: status.result,
            error: undefined,
            agentProgress: finalizeAgentProgress(prev.agentProgress),
            lastUpdatedAt: nowIso(),
          }));
        } catch (err) {
          stopPolling();
          applyPhase("FAIL", {
            error: err instanceof Error ? err.message : "Run failed",
            result: undefined,
            runId: undefined,
            agentProgress: buildInitialAgentProgress(),
          });
        }
      }, RUN_SERVICE_CONFIG.pollIntervalMs);
    },
    [appendHistory, applyPhase, stopPolling, touchUpdated]
  );

  const submit = useCallback(
    async (input: RunInput) => {
      if (!canRun(phaseRef.current)) return;

      lastInputRef.current = input;
      setSelectedRunId(null);
      applyPhase("RUN", {
        error: undefined,
        result: undefined,
        runId: undefined,
        agentProgress: buildInitialAgentProgress(),
      });

      try {
        const { runId } = await startRun(input, handleProgress);
        const startedAt = new Date().toISOString();
        touchUpdated({ phase: "running", runId });
        beginPoll(runId, input, startedAt);
      } catch (err) {
        applyPhase("FAIL", {
          error: err instanceof Error ? err.message : "Failed to start run",
          result: undefined,
          runId: undefined,
          agentProgress: buildInitialAgentProgress(),
        });
      }
    },
    [applyPhase, beginPoll, handleProgress, touchUpdated]
  );

  const reset = useCallback(() => {
    if (!canReset(phaseRef.current)) return;

    stopPolling();
    if (state.runId) {
      cancelRun(state.runId);
    }
    setSelectedRunId(null);
    applyPhase("RESET", {
      error: undefined,
      result: undefined,
      runId: undefined,
      agentProgress: buildInitialAgentProgress(),
    });
  }, [applyPhase, state.runId, stopPolling]);

  const retry = useCallback(() => {
    const input = lastInputRef.current;
    if (!input || !canRun(phaseRef.current)) return;
    void submit(input);
  }, [submit]);

  const selectHistoryEntry = useCallback(
    (runId: string) => {
      const record = history.find((r) => r.runId === runId);
      if (!record?.result) return;
      setSelectedRunId(runId);
      touchUpdated({
        phase: "done",
        runId: record.runId,
        result: record.result,
        error: undefined,
        agentProgress: buildInitialAgentProgress(),
      });
    },
    [history, touchUpdated]
  );

  return {
    phase: state.phase,
    runId: state.runId,
    result: state.result,
    error: state.error,
    lastUpdatedAt: state.lastUpdatedAt,
    agentProgress: state.agentProgress,
    history,
    selectedRunId,
    submit,
    reset,
    retry,
    selectHistoryEntry,
  };
}
