"use client";

import { createContext, useContext } from "react";
import type { Me } from "@/lib/api";

interface SessionValue {
  me: Me;
  refresh: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export const SessionProvider = SessionContext.Provider;

/** The signed-in user; only valid inside <AppShell>. */
export function useMe(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useMe must be used inside <AppShell>");
  return value;
}
