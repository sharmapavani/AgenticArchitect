const SESSION_ID_KEY = "caiSessionId";
const MESSAGE_SENT_KEY = "caiMessageSent";

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") {
    return crypto.randomUUID();
  }

  const existing = sessionStorage.getItem(SESSION_ID_KEY);
  if (existing) return existing;

  const sessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_ID_KEY, sessionId);
  return sessionId;
}

export function isFirstMessageInSession(): boolean {
  if (typeof window === "undefined") return true;
  return sessionStorage.getItem(MESSAGE_SENT_KEY) !== "true";
}

export function markMessageSent(): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(MESSAGE_SENT_KEY, "true");
}
