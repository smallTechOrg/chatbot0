"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect } from "react";
import { track } from "@/lib/analytics";
import { useChat } from "@/hooks/useChat";
import { applyColorPalette, generateColorPalette, getThemeColor } from "./colorTheme";
import FormattedMessage from "./FormattedMessage";
import styles from "./widget.module.css";

/**
 * The chat widget, shown in an iframe by embed.js. Query: `host` is the origin of the page it sits on (sent to
 * the API as `origin`), `color` the theme colour. The parent can send {type: "SEND_MESSAGE", text} to pre-fill.
 */
export default function Widget() {
  const searchParams = useSearchParams();
  const hostWebsite = searchParams.get("host") || "";

  useEffect(() => {
    applyColorPalette(generateColorPalette(getThemeColor(searchParams)));
  }, [searchParams]);

  const { chatBoxText, inputRef, messages, input, isClient, isBotProcessing, sendMessage, sendMessageDirect, setInput } =
    useChat(hostWebsite);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const data: unknown = event.data;
      if (typeof data === "object" && data !== null && "type" in data && data.type === "SEND_MESSAGE") {
        const text = "text" in data && typeof data.text === "string" ? data.text : "";
        if (!text) return;
        track("embed_widget_parent_message", { message_length: text.length });
        void sendMessageDirect(text);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [sendMessageDirect]);

  const handleClose = useCallback(() => {
    track("embed_widget_close", { session_id: "", message_count: messages.length });
    if (window.parent !== window) window.parent.postMessage({ type: "CLOSE_CHAT" }, "*");
  }, [messages.length]);

  return (
    <div className={styles.chatContainer}>
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerIcon}>💬</div>
          <div className={styles.headerText}>
            <h1 className={styles.headerTitle}>Chat with us</h1>
            <p className={styles.headerSubtitle}>We are here to help you</p>
          </div>
        </div>
        <button className={styles.closeButton} onClick={handleClose} aria-label="Close chat" type="button">
          ✕
        </button>
      </div>

      <div ref={chatBoxText} className={styles.messagesContainer} role="log" aria-live="polite">
        {messages.length === 0 && !isBotProcessing && (
          <div className={styles.emptyState}>
            <div className={styles.emptyStateIcon}>👋</div>
            <h2 className={styles.emptyStateTitle}>Welcome!</h2>
            <p className={styles.emptyStateText}>How can we help you today?</p>
          </div>
        )}

        {messages.map((msg, i) => {
          const isUser = msg.sender === "You";
          return (
            <div key={i} className={`${styles.message} ${isUser ? styles.messageUser : styles.messageBot}`}>
              <div className={`${styles.messageAvatar} ${isUser ? styles.messageAvatarUser : styles.messageAvatarBot}`}>
                {isUser ? "👤" : "🤖"}
              </div>
              <div className={`${styles.messageBubble} ${isUser ? styles.messageBubbleUser : styles.messageBubbleBot}`}>
                {isUser ? (
                  <p className={styles.messageText}>{msg.text}</p>
                ) : (
                  <FormattedMessage text={msg.text} className={styles.messageText} />
                )}
              </div>
            </div>
          );
        })}

        {isBotProcessing && (
          <div className={styles.typingIndicator}>
            <div className={`${styles.messageAvatar} ${styles.messageAvatarBot}`}>🤖</div>
            <div className={styles.typingBubble}>
              <span className={styles.typingDot}></span>
              <span className={styles.typingDot}></span>
              <span className={styles.typingDot}></span>
            </div>
          </div>
        )}
      </div>

      {isClient && (
        <div className={styles.inputContainer}>
          <form onSubmit={sendMessage} className={styles.inputForm}>
            <div className={styles.inputWrapper}>
              <input
                ref={inputRef}
                type="text"
                className={styles.input}
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isBotProcessing}
                aria-label="Message input"
                autoFocus
              />
            </div>
            <button type="submit" className={styles.sendButton} disabled={isBotProcessing || !input.trim()} aria-label="Send message">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
