"use client";

import { AgentProgressPanel } from "@/components/AgentProgressPanel";
import { CrewStatusBanner } from "@/components/CrewStatusBanner";
import { RunForm } from "@/components/RunForm";
import { RunHistory } from "@/components/RunHistory";
import { RunResults } from "@/components/RunResults";
import { resolveCrewDisplayStatus } from "@/lib/crewStatus";
import { useApiHealth } from "@/hooks/useApiHealth";
import { useRunWorkflow } from "@/hooks/useRunWorkflow";

export default function Home() {
  const {
    phase,
    result,
    error,
    lastUpdatedAt,
    agentProgress,
    history,
    selectedRunId,
    submit,
    reset,
    retry,
    selectHistoryEntry,
  } = useRunWorkflow();

  const apiOnline = useApiHealth();

  const isRunning = phase === "running";
  const isHistoryView = selectedRunId !== null && phase === "done";
  const canResetForm = !isHistoryView;
  const crewStatus = resolveCrewDisplayStatus(phase, error);

  return (
    <div className="min-h-screen bg-slate-100">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-blue-700 focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
          <h1 className="text-2xl font-bold text-slate-900">
            Critical Research Workflow
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            CAI multi-agent support — ask, research, review results
          </p>
          {apiOnline !== null && (
            <p
              className={`mt-2 text-xs font-medium ${
                apiOnline ? "text-green-700" : "text-amber-700"
              }`}
              role="status"
            >
              Backend API: {apiOnline ? "connected" : "unavailable — start uvicorn on port 8000"}
            </p>
          )}
        </div>
      </header>

      <CrewStatusBanner status={crewStatus} lastUpdatedAt={lastUpdatedAt} />

      <main id="main-content" className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="space-y-6">
            <RunForm
              disabled={isRunning}
              canReset={canResetForm}
              error={error}
              onSubmit={submit}
              onReset={reset}
              onRetry={retry}
            />
            <AgentProgressPanel
              phase={phase}
              progress={agentProgress}
              readOnly={isHistoryView}
            />
            <RunResults
              phase={phase}
              result={result}
              readOnly={isHistoryView}
            />
          </div>
          <RunHistory
            history={history}
            selectedRunId={selectedRunId}
            onSelect={selectHistoryEntry}
          />
        </div>
      </main>
    </div>
  );
}
