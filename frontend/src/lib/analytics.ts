// Typed analytics events. The tag itself is loaded by public/st-analytics.js (one GA4 property
// for every smallTech site, production hostnames only, private paths such as /embed skipped).
// This module only sends events through the globals that script defines, and does nothing
// when they are absent, so callers never need to guard.

export interface AnalyticsEventMap {
  chat_message_sent: { message_length: number; session_id: string; is_first_message: boolean; page: "chat" | "embed" };
  chat_message_received: { response_length: number; session_id: string; success: boolean; page: "chat" | "embed" };
  chat_error: { error_type: "timeout" | "network"; session_id: string; page: "chat" | "embed" };
  chat_history_loaded: { message_count: number; session_id: string; page: "chat" | "embed" };
  embed_widget_close: { session_id: string; message_count: number };
  embed_widget_parent_message: { message_length: number };
  api_latency: { endpoint: string; duration_ms: number; status: number; method: string };
}

/** Sign-up funnel events, sent through stTrack (which adds the site name). */
export type SiteEvent = "sign_up" | "signup_error" | "embed_code_copy" | "signup_form_start";

interface AnalyticsWindow extends Window {
  gtag?: (command: "event", name: string, params: Record<string, unknown>) => void;
  stTrack?: (name: string, params?: Record<string, unknown>) => void;
}

export function track<E extends keyof AnalyticsEventMap>(event: E, params: AnalyticsEventMap[E]): void {
  if (typeof window === "undefined") return;
  const w = window as AnalyticsWindow;
  w.gtag?.("event", event, { ...params, event_timestamp: new Date().toISOString() });
}

export function trackSite(event: SiteEvent, params: Record<string, unknown> = { method: "chatbot0" }): void {
  if (typeof window === "undefined") return;
  (window as AnalyticsWindow).stTrack?.(event, params);
}

/**
 * Tell the host page (embed.js forwards it to the host's own GA4) that this visitor sent a first message.
 * Once per session. `*` is the target origin because any site may embed the widget.
 */
export function notifyParentFirstInteraction(sessionId: string): void {
  const key = `chat_first_sent_${sessionId}`;
  try {
    if (localStorage.getItem(key)) return;
    if (window.parent !== window) {
      window.parent.postMessage(
        {
          type: "ANALYTICS_EVENT",
          eventName: "chatbot_first_interaction",
          eventParams: { session_id: sessionId, page_path: window.location.pathname },
        },
        "*",
      );
    }
    localStorage.setItem(key, "true");
  } catch (err) {
    console.warn("Failed to send GA event", err);
  }
}
