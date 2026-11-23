"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchHistory, sendChat } from "@/lib/api";
import { notifyParentFirstInteraction, track } from "@/lib/analytics";
import { loadSession } from "@/lib/session";

export type Sender = "You" | "Bot" | "Error";

export interface Message {
  sender: Sender;
  text: string;
}

export const REQUEST_TIMEOUT_MS = 20 * 1000;

/**
 * The chat state of the widget. `hostWebsite` is the origin of the page the widget sits on; it goes to
 * /chat and /history as `?origin=` so the backend picks that site's prompts ("" outside the widget).
 */
export function useChat(hostWebsite: string = "") {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isClient, setIsClient] = useState(false);
  const [isBotProcessing, setBotProcessing] = useState(true); // true until the history has loaded
  const chatBoxText = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sessionId = useRef("");
  const messageCount = useRef(0);
  const page = hostWebsite ? ("embed" as const) : ("chat" as const);

  useEffect(() => {
    setIsClient(true);
    const init = async () => {
      try {
        sessionId.current = loadSession();
        const result = await fetchHistory(sessionId.current, hostWebsite);
        if (result.ok) {
          const loaded = result.history.map((h): Message => ({ sender: h.type === "human" ? "You" : "Bot", text: h.content }));
          setMessages(loaded);
          messageCount.current = loaded.length;
          track("chat_history_loaded", { message_count: loaded.length, session_id: sessionId.current, page });
        } else {
          console.error("Unexpected status from /history", result.status);
        }
      } catch (err) {
        console.error("Failed to initialize chat history", err);
      } finally {
        setBotProcessing(false);
      }
    };
    void init();
  }, [hostWebsite, page]);

  // Keep the newest message in view, and the cursor in the input once the bot has answered.
  useEffect(() => {
    if (chatBoxText.current) chatBoxText.current.scrollTop = chatBoxText.current.scrollHeight;
    if (!isBotProcessing) inputRef.current?.focus();
  }, [messages, isBotProcessing]);

  /** One visitor message, from the form or from the host page (embed.js). */
  const sendText = useCallback(
    async (text: string) => {
      const userMsg = text.trim();
      if (!userMsg || isBotProcessing) return;

      track("chat_message_sent", {
        message_length: userMsg.length,
        session_id: sessionId.current,
        is_first_message: messageCount.current === 0,
        page,
      });
      messageCount.current++;
      notifyParentFirstInteraction(sessionId.current);
      setMessages((prev) => [...prev, { sender: "You", text: userMsg }]);
      setInput("");
      setBotProcessing(true);
      const started = performance.now();
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
      try {
        const reply = await sendChat(userMsg, sessionId.current, hostWebsite, controller.signal);
        track("chat_message_received", {
          response_length: (reply.success ? reply.response : reply.error)?.length ?? 0,
          session_id: sessionId.current,
          success: !!reply.success,
          page,
        });
        track("api_latency", {
          endpoint: "/chat",
          duration_ms: Math.round(performance.now() - started),
          status: reply.status,
          method: "POST",
        });
        setMessages((prev) => [
          ...prev,
          reply.success
            ? { sender: "Bot", text: reply.response ?? "" }
            : { sender: "Error", text: reply.error || "Something went wrong." },
        ]);
      } catch (err) {
        const timedOut = (err as Error).name === "AbortError";
        track("chat_error", { error_type: timedOut ? "timeout" : "network", session_id: sessionId.current, page });
        setMessages((prev) => [
          ...prev,
          { sender: "Error", text: timedOut ? "Request timed out. Please try again." : "Network or server issue." },
        ]);
      } finally {
        clearTimeout(timeout);
        setBotProcessing(false);
      }
    },
    [hostWebsite, isBotProcessing, page],
  );

  const sendMessage = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      return sendText(input);
    },
    [input, sendText],
  );

  return { chatBoxText, inputRef, messages, input, isClient, isBotProcessing, sendMessage, sendMessageDirect: sendText, setInput };
}
