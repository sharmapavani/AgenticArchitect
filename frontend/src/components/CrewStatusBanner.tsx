"use client";

import { useEffect, useState } from "react";
import {
  CREW_STATUS_PILL,
  type CrewDisplayStatus,
  crewBannerText,
  formatLastUpdated,
} from "@/lib/crewStatus";

interface CrewStatusBannerProps {
  status: CrewDisplayStatus;
  lastUpdatedAt: string;
}

export function CrewStatusBanner({ status, lastUpdatedAt }: CrewStatusBannerProps) {
  const [lastUpdatedLabel, setLastUpdatedLabel] = useState("—");
  const styles = CREW_STATUS_PILL[status];
  const label = crewBannerText(status);

  useEffect(() => {
    if (!lastUpdatedAt) return;
    setLastUpdatedLabel(formatLastUpdated(lastUpdatedAt));
  }, [lastUpdatedAt]);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={`border-b px-4 py-3 sm:px-6 ${styles.banner}`}
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2">
        <div className={`flex items-center gap-2 ${styles.text}`}>
          <span
            className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${styles.dot} ${
              status === "running" ? "animate-pulse" : ""
            }`}
            aria-hidden="true"
          />
          <span id="crew-status-label" className="text-sm font-semibold">
            {label}
          </span>
        </div>
        <p className={`text-xs ${styles.text} opacity-80`} suppressHydrationWarning>
          Last updated: {lastUpdatedLabel}
        </p>
      </div>
    </div>
  );
}
