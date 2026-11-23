// The visitor's chat session id, kept in localStorage for 30 minutes so a reload continues the conversation.

const SESSION_KEY = "chat_session";
export const SESSION_TTL_MS = 1000 * 60 * 30;

interface StoredSession {
  id: string;
  expiry: number;
}

/** The current session id: the stored one while it is fresh, else a new one (which is stored). */
export function loadSession(now: number = Date.now()): string {
  try {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) {
      const { id, expiry } = JSON.parse(stored) as StoredSession;
      if (typeof id === "string" && now < expiry) return id;
    }
  } catch (e) {
    console.warn("Failed to read the stored session:", e);
  }
  const id = crypto.randomUUID();
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify({ id, expiry: now + SESSION_TTL_MS } satisfies StoredSession));
  } catch {
    /* storage blocked (private mode, third-party iframe): the session lasts until reload */
  }
  return id;
}
