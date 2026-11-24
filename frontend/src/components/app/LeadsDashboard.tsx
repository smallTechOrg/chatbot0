"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, leads as leadsApi, type Lead } from "@/lib/api";
import { PAGE_SIZE, domainsOf, filterLeads, paginate, planUsageMessage, planUsagePercent, statusCounts, type StatusFilter } from "@/lib/leads";
import { alertError, btnSecondary, card, input } from "./classes";
import LeadRow from "./LeadRow";
import { useMe } from "./SessionContext";

const FILTERS: StatusFilter[] = ["ALL", "OPEN", "QUALIFYING", "CLOSED"];

/** The leads of the signed-in account: search, status and website filters, pages, and each lead's chat. */
export default function LeadsDashboard() {
  const { me } = useMe();
  const usage = planUsageMessage({ ...me.tenant });
  const percent = planUsagePercent(me.tenant);
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StatusFilter>("ALL");
  const [domain, setDomain] = useState("");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    try {
      setLeads(await leadsApi.list());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your leads.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => statusCounts(leads ?? []), [leads]);
  const domains = useMemo(() => domainsOf(leads ?? []), [leads]);
  const filtered = useMemo(() => filterLeads(leads ?? [], { query, status, domain }), [leads, query, status, domain]);
  const shown = paginate(filtered, page);

  if (error) {
    return (
      <p role="alert" className={alertError}>
        {error}
      </p>
    );
  }
  if (leads === null) return <p className="text-muted">Loading your leads…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Leads</h1>
        <p className="text-sm text-muted">
          {counts.ALL} in total: {counts.OPEN} open, {counts.QUALIFYING} qualifying, {counts.CLOSED} closed.
        </p>
      </div>

      {usage && (
        <section className={`${card} space-y-2`} aria-label="Plan usage">
          <p className="text-sm font-semibold" data-testid="plan-usage">
            {usage}
          </p>
          {percent !== null && (
            <progress className="h-2 w-full accent-gold" max={100} value={percent} aria-label="Share of this month's conversations used" />
          )}
        </section>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-56 flex-1">
          <label htmlFor="search" className="mb-1 block text-sm font-semibold">
            Search
          </label>
          <input id="search" type="search" className={input} placeholder="Name, email, summary…" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
        </div>
        {domains.length > 1 && (
          <div>
            <label htmlFor="website" className="mb-1 block text-sm font-semibold">
              Website
            </label>
            <select id="website" className={input} value={domain} onChange={(e) => { setDomain(e.target.value); setPage(1); }}>
              <option value="">All websites</option>
              {domains.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        )}
        <div role="group" aria-label="Filter by status" className="flex gap-2">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={status === f}
              onClick={() => { setStatus(f); setPage(1); }}
              className={`min-h-10 rounded-full border px-3 text-xs font-bold ${status === f ? "border-ink bg-ink text-readme" : "border-line bg-surface"}`}
            >
              {f === "ALL" ? "All" : f} ({counts[f]})
            </button>
          ))}
        </div>
      </div>

      <div className={`${card} overflow-x-auto p-0`}>
        {filtered.length === 0 ? (
          <p className="p-6 text-sm text-muted">{leads.length === 0 ? "No leads yet. They appear here as visitors chat with your agent." : "No leads match these filters."}</p>
        ) : (
          <table className="w-full min-w-[40rem] text-left">
            <caption className="sr-only">Leads</caption>
            <thead className="text-xs uppercase tracking-wider text-muted">
              <tr>
                <th scope="col" className="px-3 py-3">Visitor</th>
                <th scope="col" className="px-3 py-3">Where</th>
                <th scope="col" className="px-3 py-3">Status</th>
                <th scope="col" className="px-3 py-3">When</th>
              </tr>
            </thead>
            <tbody>
              {shown.rows.map((lead) => (
                <LeadRow key={lead.session_id} lead={lead} onChanged={load} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {shown.pages > 1 && (
        <nav aria-label="Pages" className="flex items-center justify-center gap-3 text-sm">
          <button type="button" className={btnSecondary} disabled={shown.page <= 1} onClick={() => setPage(shown.page - 1)}>
            Previous
          </button>
          <span>
            Page {shown.page} of {shown.pages} ({filtered.length} leads, {PAGE_SIZE} a page)
          </span>
          <button type="button" className={btnSecondary} disabled={shown.page >= shown.pages} onClick={() => setPage(shown.page + 1)}>
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
