import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 600;

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const response = await fetch(`${BACKEND_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    if (!response.ok) {
      const text = await response.text();
      return new NextResponse(text, {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        ...(response.headers.get("X-Run-Id")
          ? { "X-Run-Id": response.headers.get("X-Run-Id")! }
          : {}),
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unavailable";
    return NextResponse.json(
      {
        detail: `Failed to reach CAI backend stream (${message}). Is uvicorn running on port 8000?`,
      },
      { status: 502 }
    );
  }
}
