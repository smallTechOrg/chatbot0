"use client";

import { useState } from "react";
import { ApiError, leads as leadsApi, type HistoryItem, type Lead, type LeadStatus } from "@/lib/api";
import { alertError, btnSecondary, input } from "./classes";

const STATUSES: LeadStatus[] = ["OPEN", "QUALIFYING", "CLOSED"];

const STATUS_STYLE: Record<LeadStatus, string> = {
  OPEN: "border-gold text-gold-60",
  QUALIFYING: "border-ink text-ink",
  CLOSED: "border-ok text-ok",
};

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

interface Props {
  lead: Lead;
  /** Called after a change that should refresh the list (a lead was hidden). */
  onChanged: () => void;
}

/** One lead: a table row, and when opened its summary, remarks and chat history. */
export default function LeadRow({ lead, onChanged }: Props) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<LeadStatus>(lead.status);
  const [remarks, setRemarks] = useState(lead.remarks);
  const [history, setHistory] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save. Please try again.");
      return false;
    }
  };

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && history === null) {
      await run(async () => setHistory(await leadsApi.history(lead.session_id)));
    }
  };

  const changeStatus = async (value: LeadStatus) => {
    const previous = status;
    setStatus(value);
    if (!(await run(() => leadsApi.update(lead.session_id, { status: value })))) setStatus(previous);
  };

  const saveRemarks = async () => {
    if (await run(() => leadsApi.update(lead.session_id, { remarks }))) {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  const hide = async () => {
    if (window.confirm("Hide this lead from the dashboard?") && (await run(() => leadsApi.update(lead.session_id, { is_active: false })))) {
      onChanged();
    }
  };

  const contact = [lead.email, lead.mobile_number].filter(Boolean).join(" · ");
  return (
    <>
      <tr className="border-t border-line align-top">
        <td className="px-3 py-3">
          <button
            type="button"
            onClick={toggle}
            aria-expanded={open}
            aria-controls={`lead-${lead.session_id}`}
            className="text-left font-semibold underline decoration-gold decoration-2 underline-offset-2"
          >
            {lead.name || "Unknown visitor"}
          </button>
          <div className="text-xs text-muted">{contact || "No contact details yet"}</div>
        </td>
        <td className="px-3 py-3 text-sm">
          <span className="mr-2 rounded-full border border-line px-2 py-0.5 text-xs font-semibold">
            {lead.channel === "whatsapp" ? "WhatsApp" : "Web"}
          </span>
          {lead.domain}
        </td>
        <td className="px-3 py-3">
          <label className="sr-only" htmlFor={`status-${lead.session_id}`}>
            Status of {lead.name || "this lead"}
          </label>
          <select
            id={`status-${lead.session_id}`}
            value={status}
            onChange={(e) => void changeStatus(e.target.value as LeadStatus)}
            className={`rounded-full border bg-surface px-2 py-1 text-xs font-bold ${STATUS_STYLE[status]}`}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </td>
        <td className="px-3 py-3 text-sm text-muted">{when(lead.time)}</td>
      </tr>
      {open && (
        <tr id={`lead-${lead.session_id}`} className="bg-readme">
          <td colSpan={4} className="space-y-4 px-3 py-4">
            {error && (
              <p role="alert" className={alertError}>
                {error}
              </p>
            )}
            {lead.summary && (
              <div>
                <h3 className="text-sm font-bold">Summary</h3>
                <p className="whitespace-pre-wrap text-sm">{lead.summary}</p>
              </div>
            )}
            <div>
              <label htmlFor={`remarks-${lead.session_id}`} className="text-sm font-bold">
                Remarks
              </label>
              <textarea id={`remarks-${lead.session_id}`} rows={3} className={`${input} mt-1`} value={remarks} onChange={(e) => setRemarks(e.target.value)} />
              <div className="mt-2 flex items-center gap-3">
                <button type="button" className={btnSecondary} onClick={saveRemarks}>
                  Save remarks
                </button>
                {saved && <span role="status" className="text-sm text-ok">Saved</span>}
                <button type="button" className={`${btnSecondary} ml-auto`} onClick={hide}>
                  Hide lead
                </button>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-bold">Conversation</h3>
              {history === null ? (
                <p className="text-sm text-muted">Loading…</p>
              ) : (
                <ol className="mt-1 max-h-80 space-y-2 overflow-y-auto">
                  {history.map((m, i) => (
                    <li key={i} className={`max-w-[85%] rounded-xl border border-line px-3 py-2 text-sm ${m.type === "human" ? "ml-auto bg-ink text-readme" : "bg-surface"}`}>
                      <span className="sr-only">{m.type === "human" ? "Visitor: " : "Agent: "}</span>
                      <span className="whitespace-pre-wrap">{m.content}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
