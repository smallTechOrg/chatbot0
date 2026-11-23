import { beforeEach, describe, expect, it } from "vitest";
import { SESSION_TTL_MS, loadSession } from "./session";

beforeEach(() => localStorage.clear());

describe("loadSession", () => {
  it("creates a UUID session and keeps it", () => {
    const id = loadSession(1000);
    expect(id).toMatch(/^[0-9a-f-]{36}$/);
    expect(loadSession(2000)).toBe(id);
  });

  it("starts a new session after the 30 minute expiry", () => {
    const id = loadSession(1000);
    expect(loadSession(1000 + SESSION_TTL_MS + 1)).not.toBe(id);
  });

  it("recovers from a corrupt stored value", () => {
    localStorage.setItem("chat_session", "{not json");
    expect(loadSession()).toMatch(/^[0-9a-f-]{36}$/);
  });
});
