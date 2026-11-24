"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, sites as sitesApi, type PromptKind, type Prompts, type Site } from "@/lib/api";
import { WIDGET_ORIGIN } from "@/content/site";
import { buildEmbedScript } from "@/lib/signup";
import { alertError, alertOk, btnPrimary, btnSecondary, card, input, label } from "./classes";
import PromptChain from "./PromptChain";
import { useMe } from "./SessionContext";

const PROMPT_LABELS: Record<PromptKind, { title: string; help: string; rows: number }> = {
  company: { title: "About your business", help: "What you offer, who it's for, prices, policies and FAQs.", rows: 6 },
  "base-prompt": { title: "Instructions for the agent", help: "How the agent should behave. Leave it to use the standard instructions.", rows: 6 },
  "intro-message": { title: "First message", help: "What visitors see when they open the chat.", rows: 2 },
};
const KINDS = Object.keys(PROMPT_LABELS) as PromptKind[];

function PromptEditor({ siteKey, editable }: { siteKey: string; editable: boolean }) {
  const [prompts, setPrompts] = useState<Prompts | null>(null);
  const [drafts, setDrafts] = useState<Partial<Record<PromptKind, string>>>({});
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    sitesApi.prompts(siteKey).then(setPrompts, (err) => setMessage({ ok: false, text: err instanceof ApiError ? err.message : "Could not load the prompts." }));
  }, [siteKey]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await sitesApi.savePrompts(siteKey, drafts);
      setPrompts(await sitesApi.prompts(siteKey));
      setDrafts({});
      setMessage({ ok: true, text: "Saved." });
    } catch (err) {
      setMessage({ ok: false, text: err instanceof ApiError ? err.message : "Could not save." });
    }
  };

  if (!prompts) return <p className="text-sm text-muted">{message ? message.text : "Loading…"}</p>;
  return (
    <form onSubmit={save} className="space-y-4">
      {!editable && <p className="text-sm text-muted">Your account is not enabled yet, so these are read-only. We&apos;ll enable it shortly.</p>}
      {KINDS.map((kind) => {
        const { title, help, rows } = PROMPT_LABELS[kind];
        const current = prompts[kind];
        return (
          <div key={kind}>
            <label className={label} htmlFor={`${siteKey}-${kind}`}>
              {title}
            </label>
            <textarea
              id={`${siteKey}-${kind}`}
              rows={rows}
              className={input}
              readOnly={!editable}
              value={drafts[kind] ?? current.text}
              onChange={(e) => setDrafts({ ...drafts, [kind]: e.target.value })}
            />
            <p className="mt-1 text-xs text-muted">
              {help} {current.own ? "" : "Currently the standard text, shared with other websites."}
            </p>
          </div>
        );
      })}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? alertOk : alertError}>
          {message.text}
        </p>
      )}
      {editable && (
        <button type="submit" className={btnPrimary} disabled={Object.keys(drafts).length === 0}>
          Save changes
        </button>
      )}
    </form>
  );
}

function SiteCard({ site, editable }: { site: Site; editable: boolean }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const snippet = buildEmbedScript("#219EBC");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: the snippet is selectable below */
    }
  };

  return (
    <section className={card} aria-labelledby={`site-${site.id}`}>
      <h2 id={`site-${site.id}`} className="text-lg font-bold">
        {site.address}
      </h2>
      <p className="mb-3 text-xs text-muted">Key {site.key}</p>
      <details>
        <summary className="cursor-pointer text-sm font-semibold">Embed snippet</summary>
        <p className="my-2 text-sm">
          Paste this before the closing <code>&lt;/body&gt;</code> tag of {site.address}. Change <code>data-colour</code> to match your brand.
        </p>
        <pre className="overflow-x-auto rounded-md bg-ink p-3 text-xs text-readme">{snippet}</pre>
        <button type="button" className={`${btnSecondary} mt-2`} onClick={copy}>
          {copied ? "Copied!" : "Copy"}
        </button>
        <span className="sr-only">The widget loads from {WIDGET_ORIGIN}.</span>
      </details>
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-semibold">Where the agent&apos;s prompts come from</summary>
        <div className="mt-2">
          <PromptChain siteKey={site.key} />
        </div>
      </details>
      <div className="mt-3">
        <button type="button" className={btnSecondary} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide the agent's prompts" : "Edit the agent's prompts"}
        </button>
        {open && (
          <div className="mt-4">
            <PromptEditor siteKey={site.key} editable={editable} />
          </div>
        )}
      </div>
    </section>
  );
}

/** The account's websites: embed snippet, prompts, and adding a website (enabled accounts). */
export default function SitesPage() {
  const { me } = useMe();
  const [list, setList] = useState<Site[] | null>(null);
  const [website, setWebsite] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const enabled = me.tenant.enabled || me.user.is_admin;

  const load = useCallback(async () => {
    try {
      setList(await sitesApi.list());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your websites.");
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await sitesApi.add(website);
      setWebsite("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add the website.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Websites</h1>
      {error && (
        <p role="alert" className={alertError}>
          {error}
        </p>
      )}
      {list === null ? <p className="text-muted">Loading…</p> : list.map((site) => <SiteCard key={site.id} site={site} editable={enabled} />)}
      <form onSubmit={add} className={`${card} space-y-3`}>
        <h2 className="text-lg font-bold">Add a website</h2>
        {!enabled && <p className="text-sm text-muted">Adding websites needs an enabled account. We&apos;ll enable yours shortly.</p>}
        <div>
          <label className={label} htmlFor="new-website">
            Website address
          </label>
          <input id="new-website" className={input} placeholder="https://www.example.com" value={website} onChange={(e) => setWebsite(e.target.value)} disabled={!enabled} required />
        </div>
        <button type="submit" className={btnPrimary} disabled={!enabled || busy}>
          Add website
        </button>
      </form>
    </div>
  );
}
