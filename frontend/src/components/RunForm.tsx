"use client";

import { FormEvent, useState } from "react";
import { RunErrorAlert } from "@/components/RunErrorAlert";
import { CREW_MESSAGES } from "@/lib/crewStatus";
import type { RunInput } from "@/types/run";

interface RunFormProps {
  disabled: boolean;
  canReset: boolean;
  error?: string;
  onSubmit: (input: RunInput) => void;
  onReset: () => void;
  onRetry: () => void;
}

const defaultInput: RunInput = {
  message: "",
  language: "en",
  portalHint: null,
};

export function RunForm({
  disabled,
  canReset,
  error,
  onSubmit,
  onReset,
  onRetry,
}: RunFormProps) {
  const [input, setInput] = useState<RunInput>(defaultInput);
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const message = input.message.trim();
    if (!message) {
      setValidationError("Please enter your CAI question.");
      return;
    }
    setValidationError(null);
    onSubmit({ ...input, message });
  }

  return (
    <section
      aria-labelledby="inputs-heading"
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2 id="inputs-heading" className="text-lg font-semibold text-slate-900">
        Inputs
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        AI-assisted information only — not adjudication or eligibility decisions.
      </p>
      <p className="mt-2 text-xs text-amber-700">
        Do not enter names, health card numbers, or other personal health
        information.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4" noValidate>
        <div>
          <label htmlFor="message" className="block text-sm font-medium text-slate-700">
            Your question
          </label>
          <textarea
            id="message"
            name="message"
            rows={4}
            disabled={disabled}
            value={input.message}
            onChange={(e) => setInput((prev) => ({ ...prev, message: e.target.value }))}
            placeholder="e.g. How do I submit an OCF-18 for a new treatment plan?"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          {validationError && (
            <p id="message-error" role="alert" className="mt-1 text-sm text-red-600">
              {validationError}
            </p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="language" className="block text-sm font-medium text-slate-700">
              Language
            </label>
            <select
              id="language"
              name="language"
              disabled={disabled}
              value={input.language}
              onChange={(e) =>
                setInput((prev) => ({
                  ...prev,
                  language: e.target.value as RunInput["language"],
                }))
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </div>

          <div>
            <label htmlFor="portalHint" className="block text-sm font-medium text-slate-700">
              Portal hint (optional)
            </label>
            <select
              id="portalHint"
              name="portalHint"
              disabled={disabled}
              value={input.portalHint ?? ""}
              onChange={(e) =>
                setInput((prev) => ({
                  ...prev,
                  portalHint: e.target.value
                    ? (e.target.value as RunInput["portalHint"])
                    : null,
                }))
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="">Auto-detect</option>
              <option value="facilities">Health Care Facilities</option>
              <option value="insurers">Insurers</option>
              <option value="pms_vendors">PMS Vendors</option>
            </select>
          </div>
        </div>

        <div
          className="flex flex-wrap gap-3"
          role="group"
          aria-label="Workflow controls"
        >
          <button
            type="submit"
            disabled={disabled}
            aria-describedby="crew-status-label"
            className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {CREW_MESSAGES.runButton}
          </button>
          <button
            type="button"
            disabled={!canReset}
            onClick={onReset}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {CREW_MESSAGES.resetButton}
          </button>
        </div>

        {error && <RunErrorAlert message={error} onRetry={onRetry} />}
      </form>
    </section>
  );
}
