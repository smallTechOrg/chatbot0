"use client";

import { useCallback, useEffect, useState } from "react";
import { aiProvider, ApiError, type AiProviderStatus, type AiTestResult } from "@/lib/api";
import { isHttpsUrl } from "@/lib/slack";
import { alertError, alertOk, btnPrimary, btnSecondary, card, input, label } from "./classes";

type Notice = { ok: boolean; text: string } | null;

interface Form {
  baseUrl: string;
  apiKey: string;
  model: string;
  backupModel: string;
  timeout: string;
}

function toForm(s: AiProviderStatus): Form {
  return {
    baseUrl: s.base_url ?? "",
    apiKey: "",
    model: s.source === "database" ? s.model : "",
    backupModel: s.source === "database" ? (s.backup_model ?? "") : "",
    timeout: String(s.timeout_seconds ?? 60),
  };
}

/** Admin: the platform's AI provider (an OpenAI-compatible endpoint), with a connection test. The key is write-only. */
export default function AiProviderSettings() {
  const [status, setStatus] = useState<AiProviderStatus | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [results, setResults] = useState<AiTestResult[] | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await aiProvider.status();
      setStatus(s);
      setForm(toForm(s));
    } catch (err) {
      setNotice({ ok: false, text: err instanceof ApiError ? err.message : "Could not load the AI provider." });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    setNotice(null);
    setResults(null);
    try {
      await action();
      setNotice({ ok: true, text: done });
      await load();
    } catch (err) {
      setNotice({ ok: false, text: err instanceof ApiError ? err.message : "That did not work. Please try again." });
    } finally {
      setBusy(false);
    }
  };

  if (!status || !form) return <p className="text-sm text-muted">{notice ? notice.text : "Loading…"}</p>;
  const set = (key: keyof Form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isHttpsUrl(form.baseUrl) && !/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/.test(form.baseUrl.trim())) {
      setNotice({ ok: false, text: "The base URL must be a full https:// address." });
      return;
    }
    const timeout = Number(form.timeout);
    void run(
      () =>
        aiProvider.save({
          base_url: form.baseUrl.trim(),
          ...(form.apiKey.trim() ? { api_key: form.apiKey.trim() } : {}),
          model: form.model.trim(),
          backup_model: form.backupModel.trim(),
          timeout_seconds: Number.isInteger(timeout) ? timeout : 60,
        }),
      "Saved. It takes effect on every instance within a minute.",
    );
  };

  const test = async () => {
    setBusy(true);
    setNotice(null);
    setResults(null);
    try {
      const out = await aiProvider.test();
      setResults(out.results);
      setNotice({ ok: out.ok, text: out.ok ? "OK: the provider answered." : "The provider did not accept the request." });
    } catch (err) {
      setNotice({ ok: false, text: err instanceof ApiError ? err.message : "Could not run the test." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={`${card} space-y-4`} aria-labelledby="ai-provider">
      <div>
        <h2 id="ai-provider" className="text-lg font-bold">AI provider</h2>
        <p className="mt-1 text-sm text-muted" data-testid="ai-source">
          {status.source === "database"
            ? `In use: ${status.base_url} (model ${status.model}${status.backup_model ? `, backup ${status.backup_model}` : ""}).`
            : `Not set here yet: the deployment's Groq settings are in use (model ${status.model}${status.backup_model ? `, backup ${status.backup_model}` : ""}).`}{" "}
          Any OpenAI-compatible endpoint works. The API key is stored encrypted and is never shown again.
        </p>
      </div>
      <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className={label} htmlFor="ai-url">Base URL</label>
          <input id="ai-url" className={input} placeholder="https://api.example.com/v1" value={form.baseUrl} onChange={set("baseUrl")} required />
        </div>
        <div className="sm:col-span-2">
          <label className={label} htmlFor="ai-key">API key</label>
          <input
            id="ai-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            className={input}
            placeholder={status.source === "database" && status.key_set ? "Stored. Type a new key to replace it." : "Paste the key"}
            value={form.apiKey}
            onChange={set("apiKey")}
          />
        </div>
        <div>
          <label className={label} htmlFor="ai-model">Primary model</label>
          <input id="ai-model" className={input} value={form.model} onChange={set("model")} required />
        </div>
        <div>
          <label className={label} htmlFor="ai-backup">Backup model (optional)</label>
          <input id="ai-backup" className={input} value={form.backupModel} onChange={set("backupModel")} />
        </div>
        <div>
          <label className={label} htmlFor="ai-timeout">Timeout (seconds)</label>
          <input id="ai-timeout" type="number" min={1} max={300} className={`${input} w-32`} value={form.timeout} onChange={set("timeout")} />
        </div>
        <div className="flex flex-wrap items-end gap-3 sm:col-span-2">
          <button type="submit" className={btnPrimary} disabled={busy}>Save</button>
          <button type="button" className={btnSecondary} disabled={busy} onClick={() => void test()}>Test connection</button>
          <button
            type="button"
            className={btnSecondary}
            disabled={busy || status.source !== "database"}
            onClick={() => void run(() => aiProvider.remove(), "Removed. The deployment's Groq settings are used again.")}
          >
            Use the deployment&apos;s Groq settings
          </button>
        </div>
      </form>
      {results && (
        <ul className="text-sm" aria-label="Test results">
          {results.map((r) => (
            <li key={r.role}>
              {r.role} ({r.model}): {r.ok ? "OK" : `failed, ${r.error ?? "error"}`}
            </li>
          ))}
        </ul>
      )}
      {notice && (
        <p role={notice.ok ? "status" : "alert"} className={notice.ok ? alertOk : alertError}>
          {notice.text}
        </p>
      )}
    </section>
  );
}
