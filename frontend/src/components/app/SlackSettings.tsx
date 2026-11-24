"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, slack, type SlackStatus } from "@/lib/api";
import { isSlackWebhookUrl, SLACK_WEBHOOK_PREFIX } from "@/lib/slack";
import { alertError, alertOk, btnPrimary, btnSecondary, card, input, label } from "./classes";

type Notice = { ok: boolean; text: string } | null;

const failure = (err: unknown, fallback: string) => (err instanceof ApiError ? err.message : fallback);

/** The settings page body: connect a Slack channel so this account's own lead summaries are posted there. */
export default function SlackSettings() {
  const [status, setStatus] = useState<SlackStatus | null>(null);
  const [url, setUrl] = useState("");
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

  const run = async (action: () => Promise<unknown>, done: string, errorText: string) => {
    setBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice({ ok: true, text: done });
    } catch (err) {
      setNotice({ ok: false, text: failure(err, errorText) });
    } finally {
      setBusy(false);
    }
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSlackWebhookUrl(url)) {
      setNotice({ ok: false, text: `Paste a Slack incoming webhook URL. It starts with ${SLACK_WEBHOOK_PREFIX}` });
      return;
    }
    await run(() => slack.save(url.trim()), "Saved. Use “Send a test message” to check it.", "Could not save the webhook.");
    setUrl("");
    await load();
  };

  const remove = async () => {
    await run(() => slack.clear(), "Removed. Summaries are no longer posted to your Slack.", "Could not remove the webhook.");
    await load();
  };

  if (!status) return <p className="text-sm text-muted">{notice ? notice.text : "Loading…"}</p>;
  const editable = status.enabled;

  return (
    <section className={`${card} max-w-2xl space-y-4`} aria-labelledby="slack-heading">
      <div>
        <h2 id="slack-heading" className="text-lg font-semibold">
          Slack notifications
        </h2>
        <p className="mt-1 text-sm text-muted">
          Get the summary of each new lead from your websites in your own Slack channel, in the same format we use. Create an
          incoming webhook in Slack and paste its URL here.
        </p>
      </div>
      <p className="text-sm" data-testid="slack-state">
        Status: <strong>{status.configured ? "set" : "not set"}</strong>. For your security the URL is never shown again.
      </p>
      {!editable && <p className="text-sm text-muted">Slack notifications are available once your account is enabled.</p>}
      <form onSubmit={save} className="space-y-3">
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
            Save
          </button>
          <button
            type="button"
            className={btnSecondary}
            disabled={!editable || busy || !status.configured}
            onClick={() => run(() => slack.test(), "Test message sent. Check your Slack channel.", "Could not send the test message.")}
          >
            Send a test message
          </button>
          <button type="button" className={btnSecondary} disabled={!editable || busy || !status.configured} onClick={remove}>
            Remove
          </button>
        </div>
      </form>
      {notice && (
        <p role={notice.ok ? "status" : "alert"} className={notice.ok ? alertOk : alertError}>
          {notice.text}
        </p>
      )}
    </section>
  );
}
