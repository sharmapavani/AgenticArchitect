"use client";

import { CREW_MESSAGES } from "@/lib/crewStatus";

interface RunErrorAlertProps {
  message: string;
  onRetry: () => void;
}

export function RunErrorAlert({ message, onRetry }: RunErrorAlertProps) {
  return (
    <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-4">
      <p className="text-sm text-red-800">
        <span className="font-medium">Crew: error</span> — {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
      >
        {CREW_MESSAGES.retryButton}
      </button>
    </div>
  );
}
