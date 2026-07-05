"use client";

import { useEffect, useState } from "react";
import { checkApiHealth } from "@/services/runService";

export function useApiHealth(pollMs = 30_000) {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;

    const probe = async () => {
      const ok = await checkApiHealth();
      if (!cancelled) setOnline(ok);
    };

    void probe();
    const id = setInterval(() => void probe(), pollMs);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollMs]);

  return online;
}
