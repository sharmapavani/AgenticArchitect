import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

/** Crew runs can take several minutes — use Route Handler, not next.config rewrites (dev proxy timeout). */
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 600;

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const text = await response.text();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const runId = response.headers.get("X-Run-Id");
    if (runId) headers["X-Run-Id"] = runId;
    return new NextResponse(text, {
      status: response.status,
      headers,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unavailable";
    return NextResponse.json(
      {
        detail: `Failed to reach CAI backend (${message}). Is uvicorn running on port 8000?`,
      },
      { status: 502 }
    );
  }
}
