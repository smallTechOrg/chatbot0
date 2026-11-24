"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, auth } from "@/lib/api";
import { MIN_PASSWORD_LENGTH } from "@/lib/signup";
import AuthCard from "./AuthCard";
import { alertError, btnPrimary, input, label, link } from "./classes";

type Mode = "login" | "setup";

/** Sign in, or (while no admin exists yet) the one-time first-admin setup. */
export default function LoginForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [needsSetup, setNeedsSetup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [setupPassword, setSetupPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    auth.status().then((s) => setNeedsSetup(s.needs_bootstrap), () => setNeedsSetup(false));
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await auth.login(email, password);
      else await auth.bootstrap(setupPassword, email, password);
      router.replace("/dashboard/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server. Please try again.");
      setBusy(false);
    }
  };

  const setup = mode === "setup";
  return (
    <AuthCard title={setup ? "First-time setup" : "Sign in"}>
      <form onSubmit={submit} className="space-y-4">
        {setup && (
          <div>
            <label className={label} htmlFor="setup-password">
              Setup password
            </label>
            <input id="setup-password" type="password" className={input} value={setupPassword} onChange={(e) => setSetupPassword(e.target.value)} required />
            <p className="mt-1 text-xs text-muted">The server&apos;s admin password. It only works until the first admin exists.</p>
          </div>
        )}
        <div>
          <label className={label} htmlFor="email">
            Email
          </label>
          <input id="email" type="email" autoComplete="email" className={input} value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className={label} htmlFor="password">
            {setup ? "Choose your password" : "Password"}
          </label>
          <input
            id="password"
            type="password"
            autoComplete={setup ? "new-password" : "current-password"}
            minLength={setup ? MIN_PASSWORD_LENGTH : undefined}
            className={input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {setup && <p className="mt-1 text-xs text-muted">At least {MIN_PASSWORD_LENGTH} characters.</p>}
        </div>
        {error && (
          <p role="alert" className={alertError}>
            {error}
          </p>
        )}
        <button type="submit" className={`${btnPrimary} w-full`} disabled={busy}>
          {busy ? "One moment…" : setup ? "Create the admin account" : "Sign in"}
        </button>
      </form>
      <div className="mt-4 space-y-1 text-sm text-muted">
        {needsSetup && (
          <p>
            <button type="button" className={link} onClick={() => setMode(setup ? "login" : "setup")}>
              {setup ? "Back to sign in" : "First-time setup"}
            </button>
          </p>
        )}
        <p>
          No account yet?{" "}
          <Link href="/signup/" className={link}>
            Sign up free
          </Link>
        </p>
        <p>Forgot your password? Ask your chatbot0 contact for a reset link.</p>
      </div>
    </AuthCard>
  );
}
