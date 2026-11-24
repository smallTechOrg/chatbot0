"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, ApiError, whatsapp, type AdminDomain, type AdminTenant, type WhatsAppConnection } from "@/lib/api";
import { PLANS } from "@/content/plans";
import { alertError, alertOk, btnPrimary, btnSecondary, card, input, label } from "./classes";

// The plan keys are the pricing plans' keys: the server validates them against the same list.
const PLAN_OPTIONS = PLANS.map((p) => ({ key: p.key, name: p.name }));

/** The websites an account owns: address, key, parent website and whether the row is a www alias. */
function WebsiteList({ domains }: { domains: AdminDomain[] }) {
  if (domains.length === 0) return <p className="text-sm text-muted">No websites yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Websites of this account</caption>
        <thead className="text-xs text-muted">
          <tr>
            <th scope="col" className="py-1 pr-4 font-semibold">Address</th>
            <th scope="col" className="py-1 pr-4 font-semibold">Key</th>
            <th scope="col" className="py-1 pr-4 font-semibold">Parent</th>
            <th scope="col" className="py-1 font-semibold">Type</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {domains.map((d) => (
            <tr key={d.id}>
              <td className="py-1 pr-4">{d.address}</td>
              <td className="py-1 pr-4 font-mono text-xs">{d.key}</td>
              <td className="py-1 pr-4">{d.parent_key ? `${d.parent_key} (${d.parent_address})` : "none"}</td>
              <td className="py-1">{d.is_www_alias ? "www alias" : "website"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A link the admin copies and sends by hand (no email service yet). */
function LinkBox({ link, onClose }: { link: string; onClose: () => void }) {
  return (
    <div role="status" className={`${alertOk} space-y-2`}>
      <p>Send this link to the person. It works once, and expires.</p>
      <input readOnly aria-label="Link" className={`${input} font-mono text-xs`} value={link} onFocus={(e) => e.currentTarget.select()} />
      <button type="button" className={btnSecondary} onClick={onClose}>
        Done
      </button>
    </div>
  );
}

function TenantCard({ tenant, others, onChanged }: { tenant: AdminTenant; others: AdminTenant[]; onChanged: () => void }) {
  const [limit, setLimit] = useState(String(tenant.trial_conversation_limit));
  const [email, setEmail] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [moveKey, setMoveKey] = useState("");
  const [moveTo, setMoveTo] = useState("");

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That did not work. Please try again.");
    }
  };

  return (
    <section className={`${card} space-y-4`} aria-labelledby={`tenant-${tenant.id}`}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 id={`tenant-${tenant.id}`} className="text-lg font-bold">
          {tenant.name}
        </h2>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${tenant.enabled ? "border-ok text-ok" : "border-gold text-gold-60"}`}>
          {tenant.enabled ? "Enabled" : "Trial"}
        </span>
        <span className="text-sm text-muted">
          {tenant.site_count} {tenant.site_count === 1 ? "website" : "websites"}
          {tenant.domain_count !== tenant.site_count ? ` (${tenant.domain_count} rows)` : ""}, {tenant.conversations} conversations, {tenant.month_conversations} this month
          {tenant.monthly_limit === null ? " (no limit)" : ` of ${tenant.monthly_limit}`}
        </span>
        <button type="button" className={`${tenant.enabled ? btnSecondary : btnPrimary} ml-auto`} onClick={() => void run(() => admin.updateTenant(tenant.id, { enabled: !tenant.enabled }))}>
          {tenant.enabled ? "Disable" : "Enable account"}
        </button>
      </div>

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void run(() => admin.updateTenant(tenant.id, { trial_conversation_limit: Number(limit) }));
        }}
      >
        <div>
          <label className={label} htmlFor={`limit-${tenant.id}`}>Trial limit (conversations)</label>
          <input id={`limit-${tenant.id}`} type="number" min={0} className={`${input} w-32`} value={limit} onChange={(e) => setLimit(e.target.value)} />
        </div>
        <button type="submit" className={btnSecondary}>Save limit</button>
      </form>

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className={label} htmlFor={`plan-${tenant.id}`}>Plan</label>
          <select
            id={`plan-${tenant.id}`}
            className={`${input} w-40`}
            value={tenant.plan}
            onChange={(e) => void run(() => admin.updateTenant(tenant.id, { plan: e.target.value }))}
          >
            {PLAN_OPTIONS.map((p) => (
              <option key={p.key} value={p.key}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <p className="text-xs text-muted">Sets the monthly conversation cap once the account is enabled.</p>
      </div>

      <details>
        <summary className="cursor-pointer text-sm font-bold">
          Websites ({tenant.site_count})
        </summary>
        <div className="mt-2">
          <WebsiteList domains={tenant.domains} />
        </div>
      </details>

      <div>
        <h3 className="text-sm font-bold">Users</h3>
        <ul className="divide-y divide-line text-sm">
          {tenant.users.map((u) => (
            <li key={u.id} className="flex flex-wrap items-center gap-3 py-2">
              <span>{u.email}</span>
              {u.is_admin && <span className="rounded-full border border-ink px-2 text-xs font-bold">admin</span>}
              {u.invited && <span className="text-xs text-muted">invited, no password yet</span>}
              <button
                type="button"
                className={`${btnSecondary} ml-auto`}
                onClick={() => void run(async () => setLink(await admin.resetLink(u.id)))}
              >
                {u.invited ? "New invite link" : "Reset link"}
              </button>
            </li>
          ))}
        </ul>
        <form
          className="mt-2 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              setLink(await admin.invite(tenant.id, email));
              setEmail("");
            });
          }}
        >
          <div className="min-w-56 flex-1">
            <label className={label} htmlFor={`invite-${tenant.id}`}>Add a user</label>
            <input id={`invite-${tenant.id}`} type="email" className={input} placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <button type="submit" className={btnSecondary}>Create invite link</button>
        </form>
      </div>

      {tenant.domain_keys.length > 0 && others.length > 0 && (
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              await admin.moveDomain(moveKey || tenant.domain_keys[0], Number(moveTo || others[0].id));
            });
          }}
        >
          <div>
            <label className={label} htmlFor={`move-key-${tenant.id}`}>Move website</label>
            <select id={`move-key-${tenant.id}`} className={input} value={moveKey || tenant.domain_keys[0]} onChange={(e) => setMoveKey(e.target.value)}>
              {tenant.domain_keys.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={label} htmlFor={`move-to-${tenant.id}`}>to account</label>
            <select id={`move-to-${tenant.id}`} className={input} value={moveTo || others[0].id} onChange={(e) => setMoveTo(e.target.value)}>
              {others.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </div>
          <button type="submit" className={btnSecondary}>Move</button>
        </form>
      )}

      {link && <LinkBox link={link} onClose={() => setLink(null)} />}
      {error && (
        <p role="alert" className={alertError}>
          {error}
        </p>
      )}
    </section>
  );
}

/** For chatbot0 admins: every account, its usage and users; enable, set the trial limit, invite, reset, move websites. */
export default function AdminPage() {
  const [tenants, setTenants] = useState<AdminTenant[] | null>(null);
  const [connections, setConnections] = useState<WhatsAppConnection[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setTenants(await admin.tenants());
      setConnections((await whatsapp.list()).connections);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load the accounts.");
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Admin</h1>
      {error && (
        <p role="alert" className={alertError}>
          {error}
        </p>
      )}
      {tenants === null ? (
        <p className="text-muted">Loading…</p>
      ) : (
        tenants.map((t) => <TenantCard key={t.id} tenant={t} others={tenants.filter((o) => o.id !== t.id)} onChanged={load} />)
      )}
      <section className={card} aria-labelledby="all-wa">
        <h2 id="all-wa" className="mb-2 text-lg font-bold">All WhatsApp connections</h2>
        {connections.length === 0 ? (
          <p className="text-sm text-muted">None yet.</p>
        ) : (
          <ul className="divide-y divide-line text-sm">
            {connections.map((c) => (
              <li key={c.id} className="py-2">
                {c.display_number ?? c.phone_number_id} · {c.domain_key} · {c.status}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
