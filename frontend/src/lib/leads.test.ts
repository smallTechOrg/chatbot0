import { describe, expect, it } from "vitest";
import type { Lead } from "@/lib/api";
import { domainsOf, filterLeads, paginate, statusCounts, trialMessage } from "./leads";

const lead = (over: Partial<Lead>): Lead => ({
  session_id: "s",
  name: "Alice",
  email: "alice@acme.com",
  mobile_number: "",
  country: "",
  status: "OPEN",
  remarks: "",
  summary: "",
  domain: "ACME",
  channel: "web",
  time: "2026-01-01T00:00:00Z",
  tenant_id: 1,
  tenant: "smallTech",
  ...over,
});

const all = [
  lead({ session_id: "1", name: "Alice", status: "OPEN" }),
  lead({ session_id: "2", name: "Bob", email: "bob@x.io", status: "CLOSED", domain: "XCO", summary: "wants a quote" }),
  lead({ session_id: "3", name: "Cleo", status: "QUALIFYING", channel: "whatsapp" }),
];

describe("filterLeads", () => {
  it("searches name, email, summary and domain, ignoring case", () => {
    expect(filterLeads(all, { query: "BOB", status: "ALL", domain: "" })).toHaveLength(1);
    expect(filterLeads(all, { query: "quote", status: "ALL", domain: "" })[0].name).toBe("Bob");
    expect(filterLeads(all, { query: "xco", status: "ALL", domain: "" })[0].name).toBe("Bob");
  });

  it("filters by status and by website together", () => {
    expect(filterLeads(all, { query: "", status: "OPEN", domain: "" }).map((l) => l.name)).toEqual(["Alice"]);
    expect(filterLeads(all, { query: "", status: "ALL", domain: "ACME" })).toHaveLength(2);
    expect(filterLeads(all, { query: "", status: "CLOSED", domain: "ACME" })).toHaveLength(0);
  });
});

describe("counts and domains", () => {
  it("counts each status", () => {
    expect(statusCounts(all)).toEqual({ ALL: 3, OPEN: 1, QUALIFYING: 1, CLOSED: 1 });
  });
  it("lists the websites once, sorted", () => {
    expect(domainsOf(all)).toEqual(["ACME", "XCO"]);
  });
});

describe("paginate", () => {
  const rows = Array.from({ length: 25 }, (_, i) => i);
  it("returns the page asked for", () => {
    expect(paginate(rows, 2).rows).toEqual([10, 11, 12, 13, 14, 15, 16, 17, 18, 19]);
    expect(paginate(rows, 3)).toMatchObject({ page: 3, pages: 3 });
  });
  it("clamps the page into range and handles no rows", () => {
    expect(paginate(rows, 99).page).toBe(3);
    expect(paginate(rows, -4).page).toBe(1);
    expect(paginate([], 1)).toEqual({ rows: [], page: 1, pages: 1 });
  });
});

describe("trialMessage", () => {
  it("shows the trial usage until the account is enabled", () => {
    const t = { enabled: false, trial_conversation_limit: 20, trial_conversations_used: 12 };
    expect(trialMessage(t)).toBe("12 of 20 trial conversations used. We'll enable your account shortly.");
    expect(trialMessage({ ...t, enabled: true })).toBeNull();
  });
});
