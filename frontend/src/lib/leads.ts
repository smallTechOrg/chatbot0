// Filtering, counting and paging of the lead list, kept apart from the components so they can be tested.

import type { Lead, LeadStatus } from "@/lib/api";

export type StatusFilter = "ALL" | LeadStatus;

export interface LeadFilter {
  query: string;
  status: StatusFilter;
  /** "" means every website. */
  domain: string;
}

export const PAGE_SIZE = 10;

function matches(lead: Lead, query: string): boolean {
  if (!query) return true;
  const haystack = [lead.name, lead.email, lead.mobile_number, lead.country, lead.domain, lead.summary, lead.remarks]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.trim().toLowerCase());
}

export function filterLeads(leads: readonly Lead[], filter: LeadFilter): Lead[] {
  return leads.filter(
    (l) => (filter.status === "ALL" || l.status === filter.status) && (!filter.domain || l.domain === filter.domain) && matches(l, filter.query),
  );
}

export function statusCounts(leads: readonly Lead[]): Record<StatusFilter, number> {
  const counts: Record<StatusFilter, number> = { ALL: leads.length, OPEN: 0, QUALIFYING: 0, CLOSED: 0 };
  for (const l of leads) counts[l.status] += 1;
  return counts;
}

export function domainsOf(leads: readonly Lead[]): string[] {
  return [...new Set(leads.map((l) => l.domain))].sort();
}

export interface Page<T> {
  rows: T[];
  page: number;
  pages: number;
}

/** One page of rows; `page` is 1-based and clamped into range. */
export function paginate<T>(rows: readonly T[], page: number, size: number = PAGE_SIZE): Page<T> {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const current = Math.min(Math.max(1, page), pages);
  return { rows: rows.slice((current - 1) * size, current * size), page: current, pages };
}

/** "12 of 20 trial conversations used" for a tenant that is not enabled yet; null once it is. */
export function trialMessage(tenant: { enabled: boolean; trial_conversation_limit: number; trial_conversations_used: number }): string | null {
  if (tenant.enabled) return null;
  return `${tenant.trial_conversations_used} of ${tenant.trial_conversation_limit} trial conversations used. We'll enable your account shortly.`;
}
