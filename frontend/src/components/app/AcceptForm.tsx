"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, auth } from "@/lib/api";
import { MIN_PASSWORD_LENGTH } from "@/lib/signup";
import AuthCard from "./AuthCard";
import { alertError, btnPrimary, input, label } from "./classes";

/** Set a password from an invite or reset link (/accept/?token=...). */
export default function AcceptForm() {
  // Read once: the effect below removes the token from the URL.
  const searchParams = useSearchParams();
  const [token] = useState(() => searchParams.get("token") ?? "");
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Keep the one-time token out of the address bar and the history once it has been read.
  useEffect(() => {
    if (token) window.history.replaceState(null, "", window.location.pathname);
  }, [token]);

  const mismatch = again !== "" && again !== password;
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== again) return;
    setBusy(true);
    setError(null);
    try {
      await auth.accept(token, password);
      router.replace("/dashboard/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server. Please try again.");
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <AuthCard title="Link not valid">
        <p className="text-sm">This link has no token. Ask for a new one.</p>
      </AuthCard>
    );
  }
  return (
    <AuthCard title="Choose your password">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className={label} htmlFor="new-password">
            New password
          </label>
          <input id="new-password" type="password" autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} className={input} value={password} onChange={(e) => setPassword(e.target.value)} required />
          <p className="mt-1 text-xs text-muted">At least {MIN_PASSWORD_LENGTH} characters.</p>
        </div>
        <div>
          <label className={label} htmlFor="again">
            Type it again
          </label>
          <input id="again" type="password" autoComplete="new-password" className={input} value={again} onChange={(e) => setAgain(e.target.value)} aria-invalid={mismatch} required />
          {mismatch && <p className="mt-1 text-xs text-bad">The passwords do not match.</p>}
        </div>
        {error && (
          <p role="alert" className={alertError}>
            {error}
          </p>
        )}
        <button type="submit" className={`${btnPrimary} w-full`} disabled={busy || mismatch}>
          {busy ? "One moment…" : "Save password and sign in"}
        </button>
      </form>
    </AuthCard>
  );
}
