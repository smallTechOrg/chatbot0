"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, slack, type SlackChanges, type SlackStatus } from "@/lib/api";
import { isHttpsUrl, isSlackWebhookUrl, SLACK_WEBHOOK_PREFIX } from "@/lib/slack";
import { alertError, alertOk, btnPrimary, btnSecondary, card, input, label } from "./classes";

type Notice = { ok: boolean; text: string } | null;

const failure = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback);

/** The settings page body: connect a Slack channel, switch it on or off, choose the dashboard link, send a test. */
export default function SlackSettings() {
  const [status, setStatus] = useState<SlackStatus | null>(null);
  const [url, setUrl] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const load = useCallback(async () => {
    try {
      setStatus(await slack.status());
    } catch (err) {
      setNotice({ ok: false, text: failure(err, "Could not load the Slack settings.") });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<unknown>, done: string, errorText: string): Promise<boolean> => {
    setBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ ok: true, text: done });
      await load();
      return true;
    } catch (err) {
      setNotice({ ok: false, text: failure(err, errorText) });
      return false;
    } finally {
      setBusy(false);
    }
  };

  const change = async (changes: SlackChanges, done: string) => run(() => slack.save(changes), done, "Could not save.");

  const saveWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSlackWebhookUrl(url)) {
      setNotice({ ok: false, text: `Paste a Slack incoming webhook URL. It starts with ${SLACK_WEBHOOK_PREFIX}` });
      return;
    }
    if (await change({ webhook_url: url.trim() }, "Saved. Use “Send a test message” to check it.")) setUrl("");
  };

  const saveLink = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = (link ?? "").trim();
    if (value !== "" && !isHttpsUrl(value)) {
      setNotice({ ok: false, text: "Enter the dashboard link as a full https:// address." });
      return;
    }
    if (await change({ dashboard_url: value }, value === "" ? "The link is back to the default." : "Dashboard link saved.")) setLink(null);
  };

  if (!status) return <p className="text-sm text-muted">{notice ? notice.text : "Loading…"}</p>;
  const editable = status.enabled;
  const linkValue = link ?? (status.dashboard_url_is_default ? "" : status.dashboard_url);

  return (
    <section className={`${card} max-w-2xl space-y-6`} aria-labelledby="slack-heading">
      <div>
        <h2 id="slack-heading" className="text-lg font-semibold">
          Slack notifications
        </h2>
        <p className="mt-1 text-sm text-muted">
          Get the summary of each new lead from your websites in your own Slack channel. Create an incoming webhook in Slack and paste its
          URL here.
        </p>
      </div>
      {!editable && <p className="text-sm text-muted">Slack notifications are available once your account is enabled.</p>}

      <form onSubmit={saveWebhook} className="space-y-3">
        <p className="text-sm" data-testid="slack-state">
          Webhook: <strong>{status.configured ? "set" : "not set"}</strong>. For your security the URL is never shown again.
        </p>
        <div>
          <label className={label} htmlFor="slack-webhook">
            {status.configured ? "Replace the webhook URL" : "Webhook URL"}
          </label>
          <input
            id="slack-webhook"
            type="password"
            autoComplete="off"
            spellCheck={false}
            className={input}
            placeholder={`${SLACK_WEBHOOK_PREFIX}…`}
            value={url}
            disabled={!editable || busy}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="submit" className={btnPrimary} disabled={!editable || busy || url.trim() === ""}>
            Save webhook
          </button>
          <button
            type="button"
            className={btnSecondary}
            disabled={!editable || busy || !status.configured}
            onClick={() => run(() => slack.test(), "Test message sent. Check your Slack channel.", "Could not send the test message.")}
          >
            Send a test message
          </button>
          <button
            type="button"
            className={btnSecondary}
            disabled={!editable || busy || !status.configured}
            onClick={() => run(() => slack.clear(), "Removed. Summaries are no longer posted to your Slack.", "Could not remove the webhook.")}
          >
            Remove webhook
          </button>
        </div>
      </form>

      <div className="flex items-center gap-3">
        <input
          id="slack-on"
          type="checkbox"
          className="h-5 w-5 accent-gold"
          checked={status.notifications_on}
          disabled={!editable || busy || !status.configured}
          onChange={(e) => void change({ notifications_on: e.target.checked }, e.target.checked ? "Slack notifications are on." : "Slack notifications are off.")}
        />
        <label htmlFor="slack-on" className="text-sm font-semibold">
          Send lead summaries to Slack
        </label>
      </div>

      <form onSubmit={saveLink} className="space-y-3">
        <div>
          <label className={label} htmlFor="slack-link">
            Dashboard link
          </label>
          <input
            id="slack-link"
            type="url"
            className={input}
            placeholder={status.default_dashboard_url}
            value={linkValue}
            disabled={!editable || busy}
            onChange={(e) => setLink(e.target.value)}
          />
          <p className="mt-1 text-xs text-muted">
            The title of each Slack summary links here, for example to your own CRM. Leave it empty to use {status.default_dashboard_url}
          </p>
        </div>
        <button type="submit" className={btnSecondary} disabled={!editable || busy || link === null}>
          Save link
        </button>
      </form>

      {notice && (
        <p role={notice.ok ? "status" : "alert"} className={notice.ok ? alertOk : alertError}>
          {notice.text}
        </p>
      )}
    </section>
  );
}
