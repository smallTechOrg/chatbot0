// The only place the frontend talks to the Flask API. Every path is root-absolute and
// same-origin: Flask serves this app, and `next dev` forwards the same paths (see
// next.config.ts). Components and hooks call these functions, never fetch().

export interface HistoryItem {
  type: "human" | "ai";
  content: string;
}

export interface HistoryResult {
  ok: boolean;
  status: number;
  history: HistoryItem[];
}

export interface ChatReply {
  success: boolean;
  response?: string;
  error?: string;
  /** HTTP status of the answer. */
  status: number;
}

export interface SignupDomain {
  website_url: string;
  contact_name: string;
  email?: string;
  mobile?: string;
}

export type RegisterDomainResult =
  | { kind: "created"; key: string }
  | { kind: "duplicate" }
  | { kind: "invalid" }
  | { kind: "failed" };

const JSON_HEADERS = { accept: "application/json", "Content-Type": "application/json" } as const;

function withOrigin(path: string, origin: string, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams(extra);
  if (origin) params.set("origin", origin);
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

/** The conversation so far for a session. `origin` is the host website the widget sits on ("" outside the widget). */
export async function fetchHistory(sessionId: string, origin: string): Promise<HistoryResult> {
  const res = await fetch(withOrigin("/history", origin, { session_id: sessionId }), { method: "GET" });
  const data = (await res.json()) as { history?: HistoryItem[] };
  return { ok: res.status === 200 || res.status === 201, status: res.status, history: data.history ?? [] };
}

/** One visitor message. Throws on a network failure or when `signal` aborts. */
export async function sendChat(
  input: string,
  sessionId: string,
  origin: string,
  signal?: AbortSignal,
): Promise<ChatReply> {
  const res = await fetch(withOrigin("/chat", origin), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input, session_id: sessionId, request_type: "sales" }),
    signal,
  });
  const data = (await res.json()) as Omit<ChatReply, "status">;
  return { ...data, status: res.status };
}

/** Sign-up step 1: register the website, with who is signing up. */
export async function registerDomain(body: SignupDomain): Promise<RegisterDomainResult> {
  const res = await fetch("/domains/", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });
  if (res.status === 409) return { kind: "duplicate" };
  if (res.status === 422) return { kind: "invalid" };
  if (!res.ok) return { kind: "failed" };
  const data = (await res.json()) as { key: string };
  return { kind: "created", key: data.key };
}

/** Sign-up step 2: save the company description as the sales agent's company prompt. */
export async function saveCompanyPrompt(domain: string, text: string): Promise<boolean> {
  const res = await fetch("/prompt", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ domain, agent_type: "sales", type: "company", text }),
  });
  return res.ok;
}
