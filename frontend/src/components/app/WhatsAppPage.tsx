"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, whatsapp, type GraphCheck, type WhatsAppConnection } from "@/lib/api";
import { alertError, alertOk, btnPrimary, btnSecondary, card, input, label } from "./classes";
import { useMe } from "./SessionContext";
import DisplayNameStatus from "./DisplayNameStatus";

function describeCheck(check: GraphCheck | null | undefined): { ok: boolean; text: string } | null {
  if (!check) return null;
  if (check.ok) return { ok: true, text: `Token works for ${check.display_number ?? "this number"}${check.verified_name ? ` (${check.verified_name})` : ""}.` };
  return { ok: false, text: `Graph API check failed: ${check.error ?? "unknown error"}` };
}

const STATUS_TEXT: Record<string, string> = { active: "Active", pending: "Waiting for the first message", needs_attention: "Needs attention" };

function Copyable({ text, name }: { text: string; name: string }) {
  return (
    <input readOnly aria-label={name} className={`${input} font-mono text-xs`} value={text} onFocus={(e) => e.currentTarget.select()} />
  );
}

function ConnectionCard({ connection, editable, domainKeys, onChanged }: { connection: WhatsAppConnection; editable: boolean; domainKeys: string[]; onChanged: () => void }) {
  const [token, setToken] = useState("");
  const [secret, setSecret] = useState("");
  const [domain, setDomain] = useState(connection.domain_key);
  const [to, setTo] = useState("");
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);

  const run = async (action: () => Promise<{ ok: boolean; text: string } | null>) => {
    try {
      setNotice(await action());
      onChanged();
    } catch (err) {
      setNotice({ ok: false, text: err instanceof ApiError ? err.message : "That did not work. Please try again." });
    }
  };

  const replace = (e: React.FormEvent) => {
    e.preventDefault();
    const changes = { access_token: token || undefined, app_secret: secret || undefined, domain_key: domain !== connection.domain_key ? domain : undefined };
    void run(async () => {
      const { check } = await whatsapp.update(connection.id, changes);
      setToken("");
      setSecret("");
      return describeCheck(check) ?? { ok: true, text: "Saved." };
    });
  };

  return (
    <section className={`${card} space-y-4`} aria-labelledby={`wa-${connection.id}`}>
      <div>
        <h2 id={`wa-${connection.id}`} className="text-lg font-bold">
          {connection.display_number ?? `Number ${connection.phone_number_id}`} {connection.verified_name && <span className="font-normal text-muted">({connection.verified_name})</span>}
        </h2>
        <p className="text-sm">
          {connection.domain_key} · {STATUS_TEXT[connection.status] ?? connection.status}
        </p>
        {connection.last_error && <p className="mt-1 text-sm text-bad">Last error: {connection.last_error}</p>}
      </div>

      <div className="space-y-2">
        <p className="text-sm font-semibold">Paste these into the Meta app (WhatsApp &gt; Configuration)</p>
        <Copyable name="Webhook URL" text={connection.webhook_url} />
        <Copyable name="Verify token" text={connection.verify_token} />
        <p className="text-xs text-muted">Subscribe to <code>messages</code>. Customers write first; the agent replies.</p>
      </div>

      {editable && (
        <>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={btnSecondary} onClick={() => void run(async () => describeCheck((await whatsapp.check(connection.id)).check))}>
              Check token now
            </button>
          </div>
          <DisplayNameStatus nameStatus={connection.name_status} lastError={connection.last_error} />
          <form onSubmit={replace} className="space-y-3">
            <h3 className="text-sm font-bold">Replace credentials</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <label className={label} htmlFor={`token-${connection.id}`}>New access token</label>
                <input id={`token-${connection.id}`} type="password" autoComplete="off" className={input} value={token} onChange={(e) => setToken(e.target.value)} />
              </div>
              <div>
                <label className={label} htmlFor={`secret-${connection.id}`}>New app secret</label>
                <input id={`secret-${connection.id}`} type="password" autoComplete="off" className={input} value={secret} onChange={(e) => setSecret(e.target.value)} />
              </div>
              <div>
                <label className={label} htmlFor={`domain-${connection.id}`}>Website</label>
                <select id={`domain-${connection.id}`} className={input} value={domain} onChange={(e) => setDomain(e.target.value)}>
                  {domainKeys.map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              </div>
            </div>
            <button type="submit" className={btnSecondary} disabled={!token && !secret && domain === connection.domain_key}>
              Save
            </button>
          </form>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                const { result } = await whatsapp.test(connection.id, to, "");
                return result.ok ? { ok: true, text: `Sent to ${result.to}.` } : { ok: false, text: `Not sent: ${result.error ?? "unknown error"}. ${result.hint ?? ""}`.trim() };
              });
            }}
          >
            <div className="min-w-56 flex-1">
              <label className={label} htmlFor={`to-${connection.id}`}>Send a test message to</label>
              <input id={`to-${connection.id}`} className={input} placeholder="919876543210" inputMode="tel" value={to} onChange={(e) => setTo(e.target.value)} required />
            </div>
            <button type="submit" className={btnSecondary}>Send test</button>
          </form>
        </>
      )}
      {notice && (
        <p role={notice.ok ? "status" : "alert"} className={notice.ok ? alertOk : alertError}>
          {notice.text}
        </p>
      )}
    </section>
  );
}

function ConnectForm({ domainKeys, onCreated }: { domainKeys: string[]; onCreated: () => void }) {
  const [form, setForm] = useState({ phone_number_id: "", domain_key: domainKeys[0] ?? "", access_token: "", app_secret: "" });
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { check } = await whatsapp.create({ ...form, domain_key: form.domain_key || domainKeys[0] });
      setNotice(describeCheck(check));
      setForm({ ...form, phone_number_id: "", access_token: "", app_secret: "" });
      onCreated();
    } catch (err) {
      setNotice({ ok: false, text: err instanceof ApiError ? err.message : "Could not connect the number." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className={`${card} space-y-3`}>
      <h2 className="text-lg font-bold">Connect a WhatsApp number</h2>
      <p className="text-sm text-muted">From the Meta app: WhatsApp &gt; API Setup. The token and secret are stored encrypted and never shown again.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={label} htmlFor="wa-pnid">Phone number ID</label>
          <input id="wa-pnid" className={input} inputMode="numeric" value={form.phone_number_id} onChange={set("phone_number_id")} required />
        </div>
        <div>
          <label className={label} htmlFor="wa-domain">Website</label>
          <select id="wa-domain" className={input} value={form.domain_key || domainKeys[0]} onChange={set("domain_key")} required>
            {domainKeys.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={label} htmlFor="wa-token">Access token</label>
          <input id="wa-token" type="password" autoComplete="off" className={input} value={form.access_token} onChange={set("access_token")} required />
        </div>
        <div>
          <label className={label} htmlFor="wa-secret">App secret</label>
          <input id="wa-secret" type="password" autoComplete="off" className={input} value={form.app_secret} onChange={set("app_secret")} required />
        </div>
      </div>
      {notice && (
        <p role={notice.ok ? "status" : "alert"} className={notice.ok ? alertOk : alertError}>
          {notice.text}
        </p>
      )}
      <button type="submit" className={btnPrimary} disabled={busy || domainKeys.length === 0}>
        Connect
      </button>
    </form>
  );
}

/** The account's WhatsApp numbers. Read-only until the account is enabled. */
export default function WhatsAppPage() {
  const { me } = useMe();
  const [connections, setConnections] = useState<WhatsAppConnection[] | null>(null);
  const [domainKeys, setDomainKeys] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const editable = me.tenant.enabled || me.user.is_admin;

  const load = useCallback(async () => {
    try {
      const out = await whatsapp.list();
      setConnections(out.connections);
      setDomainKeys(out.domain_keys);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your WhatsApp numbers.");
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">WhatsApp</h1>
      {!editable && <p className="text-sm text-muted">WhatsApp can be connected once your account is enabled. We&apos;ll enable it shortly.</p>}
      {error && (
        <p role="alert" className={alertError}>
          {error}
        </p>
      )}
      {connections === null ? (
        <p className="text-muted">Loading…</p>
      ) : (
        connections.map((c) => <ConnectionCard key={c.id} connection={c} editable={editable} domainKeys={domainKeys} onChanged={load} />)
      )}
      {editable && connections !== null && <ConnectForm domainKeys={domainKeys} onCreated={load} />}
    </div>
  );
}
