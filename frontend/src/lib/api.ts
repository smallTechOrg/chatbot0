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

// ---------------------------------------------------------------------------------------------------------------
// Accounts, leads, websites, WhatsApp and admin: JSON APIs under session auth (see api/*.py).
// Every state-changing call carries the X-CSRF-Token header; a 401 sends the browser to /login/.
// ---------------------------------------------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let csrfToken = "";

/** Remember the CSRF token the server issued (login, sign-up, accept and /api/auth/me return it). */
export function setCsrfToken(token: string): void {
  csrfToken = token;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  /** Public calls (sign-in, probes) must not bounce a 401 to the login page. */
  public?: boolean;
}

async function request<T>(path: string, { method = "GET", body, public: isPublic = false }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRF-Token"] = csrfToken;
  const res = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* no JSON body */
  }
  if (res.status === 401 && !isPublic && typeof window !== "undefined") {
    window.location.assign("/login/");
  }
  if (!res.ok) {
    const message = (data as { error?: string } | null)?.error ?? "Something went wrong. Please try again.";
    throw new ApiError(res.status, message);
  }
  return data as T;
}

export interface User {
  id: number;
  email: string;
  is_admin: boolean;
  tenant_id: number;
}

export interface Tenant {
  id: number;
  name: string;
  enabled: boolean;
  trial_conversation_limit: number;
  trial_conversations_used: number;
  /** Plan key: "free", "basic" or "pro". */
  plan: string;
  plan_name: string;
  /** Conversations per month the plan allows; null when unlimited. */
  monthly_limit: number | null;
  /** Distinct chat sessions started this calendar month (Asia/Kolkata). */
  monthly_conversations_used: number;
}

export interface Site {
  id: number;
  key: string;
  address: string;
}

export interface Me {
  user: User;
  tenant: Tenant;
  domains: Site[];
  csrf: string;
}

interface Signed {
  user: User;
  csrf: string;
}

export const auth = {
  status: () => request<{ needs_bootstrap: boolean }>("/api/auth/status", { public: true }),
  /** The signed-in user, or null when there is no session. */
  async me(): Promise<Me | null> {
    try {
      const me = await request<Me>("/api/auth/me", { public: true });
      setCsrfToken(me.csrf);
      return me;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return null;
      throw err;
    }
  },
  async login(email: string, password: string): Promise<User> {
    const out = await request<Signed>("/api/auth/login", { method: "POST", body: { email, password }, public: true });
    setCsrfToken(out.csrf);
    return out.user;
  },
  async bootstrap(password: string, email: string, newPassword: string): Promise<User> {
    const out = await request<Signed>("/api/auth/bootstrap", {
      method: "POST",
      body: { password, email, new_password: newPassword },
      public: true,
    });
    setCsrfToken(out.csrf);
    return out.user;
  },
  async accept(token: string, newPassword: string): Promise<User> {
    const out = await request<Signed>("/api/auth/accept", {
      method: "POST",
      body: { token, new_password: newPassword },
      public: true,
    });
    setCsrfToken(out.csrf);
    return out.user;
  },
  logout: (everywhere = false) => request<unknown>("/api/auth/logout", { method: "POST", body: { everywhere } }),
};

export interface SignupInput {
  name: string;
  website: string;
  email: string;
  password: string;
  phone?: string;
  description?: string;
}

/** Create an account (a not-yet-enabled tenant, its user and website). The visitor is signed in afterwards. */
export async function signUp(input: SignupInput): Promise<{ user: User; domain: { key: string; address: string } }> {
  const out = await request<Signed & { domain: { key: string; address: string } }>("/api/signup", {
    method: "POST",
    body: input,
    public: true,
  });
  setCsrfToken(out.csrf);
  return { user: out.user, domain: out.domain };
}

export type LeadStatus = "OPEN" | "QUALIFYING" | "CLOSED";

export interface Lead {
  session_id: string;
  name: string;
  email: string;
  mobile_number: string;
  country: string;
  status: LeadStatus;
  remarks: string;
  summary: string;
  domain: string;
  channel: "web" | "whatsapp";
  time: string;
  tenant_id: number | null;
  tenant: string | null;
}

export const leads = {
  list: async (tenantId?: number) =>
    (await request<{ leads: Lead[] }>(`/api/leads${tenantId ? `?tenant_id=${tenantId}` : ""}`)).leads,
  update: (sessionId: string, changes: { status?: LeadStatus; remarks?: string; is_active?: boolean }) =>
    request<unknown>(`/api/leads/${encodeURIComponent(sessionId)}`, { method: "PATCH", body: changes }),
  history: async (sessionId: string) =>
    (await request<{ history: HistoryItem[] }>(`/api/leads/${encodeURIComponent(sessionId)}/history`)).history,
};

export type PromptKind = "company" | "base-prompt" | "intro-message";
export type Prompts = Record<PromptKind, { text: string; own: boolean }>;

export const sites = {
  list: async () => (await request<{ domains: Site[] }>("/api/domains")).domains,
  add: (website: string) =>
    request<{ domain: { key: string; address: string } }>("/api/domains", { method: "POST", body: { website } }),
  prompts: async (key: string) => (await request<{ prompts: Prompts }>(`/api/domains/${encodeURIComponent(key)}/prompts`)).prompts,
  savePrompts: (key: string, prompts: Partial<Record<PromptKind, string>>) =>
    request<unknown>(`/api/domains/${encodeURIComponent(key)}/prompts`, { method: "PUT", body: prompts }),
};

export interface WhatsAppConnection {
  id: string;
  phone_number_id: string;
  domain_key: string;
  display_number: string | null;
  verified_name: string | null;
  verify_token: string;
  status: string;
  last_message_at: string | null;
  last_error: string | null;
  webhook_url: string;
}

export interface GraphCheck {
  ok: boolean;
  error?: string;
  display_number?: string;
  verified_name?: string;
}

export interface NewConnection {
  phone_number_id: string;
  domain_key: string;
  access_token: string;
  app_secret: string;
}

export const whatsapp = {
  list: () => request<{ connections: WhatsAppConnection[]; domain_keys: string[] }>("/api/whatsapp/connections"),
  get: (id: string) => request<{ connection: WhatsAppConnection; domain_keys: string[] }>(`/api/whatsapp/connections/${id}`),
  create: (input: NewConnection) =>
    request<{ connection: WhatsAppConnection; check: GraphCheck }>("/api/whatsapp/connections", { method: "POST", body: input }),
  update: (id: string, changes: Partial<Omit<NewConnection, "phone_number_id">>) =>
    request<{ check: GraphCheck | null }>(`/api/whatsapp/connections/${id}`, { method: "PATCH", body: changes }),
  check: (id: string) => request<{ check: GraphCheck }>(`/api/whatsapp/connections/${id}/check`, { method: "POST", body: {} }),
  test: (id: string, to: string, body: string) =>
    request<{ result: { ok: boolean; to?: string; error?: string; hint?: string } }>(
      `/api/whatsapp/connections/${id}/test`,
      { method: "POST", body: { to, body } },
    ),
};

export interface SlackStatus {
  configured: boolean;
  enabled: boolean;
}

/** The account's own Slack webhook. The server never returns the URL, only whether one is set. */
export const slack = {
  status: () => request<SlackStatus>("/api/slack"),
  save: (webhookUrl: string) => request<unknown>("/api/slack", { method: "PUT", body: { webhook_url: webhookUrl } }),
  clear: () => request<unknown>("/api/slack", { method: "DELETE" }),
  test: () => request<unknown>("/api/slack/test", { method: "POST", body: {} }),
};

export interface AdminUser {
  id: number;
  email: string;
  is_admin: boolean;
  invited: boolean;
  last_login_at: string | null;
}

export interface AdminDomain {
  id: number;
  key: string;
  address: string;
  parent_id: number | null;
  parent_key: string | null;
  parent_address: string | null;
  /** A "www." row that shares its main website's key. */
  is_www_alias: boolean;
}

export interface AdminTenant {
  id: number;
  name: string;
  enabled: boolean;
  trial_conversation_limit: number;
  plan: string;
  monthly_limit: number | null;
  month_conversations: number;
  conversations: number;
  users: AdminUser[];
  domain_keys: string[];
  domains: AdminDomain[];
  /** All domain rows, www aliases included. */
  domain_count: number;
  /** Websites, without the www aliases. */
  site_count: number;
}

export const admin = {
  tenants: async () => (await request<{ tenants: AdminTenant[] }>("/api/admin/tenants")).tenants,
  updateTenant: (id: number, changes: { enabled?: boolean; trial_conversation_limit?: number; name?: string; plan?: string }) =>
    request<unknown>(`/api/admin/tenants/${id}`, { method: "PATCH", body: changes }),
  invite: async (tenantId: number, email: string) =>
    (await request<{ invite_link: string }>(`/api/admin/tenants/${tenantId}/users`, { method: "POST", body: { email } })).invite_link,
  resetLink: async (userId: number) =>
    (await request<{ link: string }>(`/api/admin/users/${userId}/reset-link`, { method: "POST", body: {} })).link,
  moveDomain: (key: string, tenantId: number) =>
    request<unknown>(`/api/admin/domains/${encodeURIComponent(key)}`, { method: "PATCH", body: { tenant_id: tenantId } }),
};
