"use client";

import type { RunRecord } from "@/types/run";

interface RunHistoryProps {
  history: RunRecord[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-CA", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function RunHistory({ history, selectedRunId, onSelect }: RunHistoryProps) {
  return (
    <section
      aria-labelledby="history-heading"
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2 id="history-heading" className="text-lg font-semibold text-slate-900">
        History
      </h2>
      <p className="mt-1 text-xs text-slate-500">Session history (this browser tab)</p>

      {history.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No completed runs yet.</p>
      ) : (
        <ul className="mt-4 max-h-80 space-y-2 overflow-y-auto" aria-label="Past research runs">
          {history.map((record) => {
            const snippet =
              record.input.message.length > 60
                ? `${record.input.message.slice(0, 60)}…`
                : record.input.message;
            const isSelected = record.runId === selectedRunId;

            return (
              <li key={record.runId}>
                <button
                  type="button"
                  onClick={() => onSelect(record.runId)}
                  aria-current={isSelected ? "true" : undefined}
                  aria-label={`View run: ${snippet}`}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                    isSelected
                      ? "border-blue-600 bg-blue-50"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <span className="block font-medium text-slate-800">{snippet}</span>
                  <span className="mt-1 block text-xs text-slate-500">
                    {formatTime(record.completedAt ?? record.startedAt)} ·{" "}
                    {record.input.language.toUpperCase()}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
