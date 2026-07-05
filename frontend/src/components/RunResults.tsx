"use client";

import { CREW_MESSAGES } from "@/lib/crewStatus";
import type { RunResult, RunState } from "@/types/run";

interface RunResultsProps {
  phase: RunState;
  result?: RunResult;
  readOnly?: boolean;
}

export function RunResults({ phase, result, readOnly }: RunResultsProps) {
  return (
    <section
      aria-labelledby="results-heading"
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2 id="results-heading" className="text-lg font-semibold text-slate-900">
        Results
      </h2>

      {phase === "idle" && (
        <p className="mt-4 text-sm text-slate-500">{CREW_MESSAGES.resultsIdle}</p>
      )}

      {phase === "running" && (
        <div className="mt-6 flex items-center gap-3" aria-busy="true">
          <span
            className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-blue-700 border-t-transparent"
            aria-hidden="true"
          />
          <p className="text-sm text-slate-700">{CREW_MESSAGES.resultsRunning}</p>
        </div>
      )}

      {phase === "done" && result && (
        <div className="mt-4 space-y-4">
          <p className="text-sm font-medium text-green-800">{CREW_MESSAGES.resultsDone}</p>

          {result.scopeRefusal ? (
            <p className="rounded-md bg-amber-50 p-4 text-sm text-amber-900">
              {result.scopeRefusalMessage ??
                "I can only assist with CAI and NYC auto insurance health claims topics."}
            </p>
          ) : (
            <>
              <div className="rounded-md bg-slate-50 p-4">
                <h3 className="sr-only">Answer</h3>
                <p className="text-sm text-slate-800">{result.answer}</p>
              </div>

              {result.citations.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-800">Citations</h3>
                  <ul className="mt-2 space-y-1">
                    {result.citations.map((citation) => (
                      <li key={citation.url}>
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-700 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                        >
                          {citation.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.workflowMap && (
                <div className="rounded-md border border-slate-200 p-4">
                  <h3 className="text-sm font-medium text-slate-800">
                    Workflow / impact
                  </h3>
                  <dl className="mt-2 space-y-1 text-sm text-slate-700">
                    <div>
                      <dt className="inline font-medium">Workflow: </dt>
                      <dd className="inline">{result.workflowMap.workflow}</dd>
                    </div>
                    {result.workflowMap.impactedOcf && (
                      <div>
                        <dt className="inline font-medium">Impacted OCF: </dt>
                        <dd className="inline">{result.workflowMap.impactedOcf}</dd>
                      </div>
                    )}
                    {result.workflowMap.suggestedNextAction && (
                      <div>
                        <dt className="inline font-medium">Suggested next action: </dt>
                        <dd className="inline">
                          {result.workflowMap.suggestedNextAction}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>
              )}

              {result.caseNumber && (
                <p className="rounded-md bg-green-50 p-3 text-sm text-green-900">
                  Support Case created: <strong>{result.caseNumber}</strong>
                </p>
              )}
            </>
          )}

          {readOnly && (
            <p className="text-xs text-slate-500">Viewing a past run from history.</p>
          )}
        </div>
      )}
    </section>
  );
}
