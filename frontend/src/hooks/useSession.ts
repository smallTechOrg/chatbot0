"use client";

import { useCallback, useEffect, useState } from "react";
import { auth, type Me } from "@/lib/api";

export type SessionState = { status: "loading" } | { status: "anonymous" } | { status: "signed-in"; me: Me };

/** Who is signed in. `refresh` reloads it (after a change that affects the trial banner, say). */
export function useSession() {
  const [state, setState] = useState<SessionState>({ status: "loading" });

  const refresh = useCallback(async () => {
    try {
      const me = await auth.me();
      setState(me ? { status: "signed-in", me } : { status: "anonymous" });
    } catch {
      setState({ status: "anonymous" });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { state, refresh };
}
