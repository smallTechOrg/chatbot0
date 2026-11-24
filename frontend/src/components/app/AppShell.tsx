"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import Wordmark from "@/components/site/Wordmark";
import { useSession } from "@/hooks/useSession";
import { auth } from "@/lib/api";
import { trialMessage } from "@/lib/leads";
import { btnSecondary } from "./classes";
import { SessionProvider } from "./SessionContext";

const NAV = [
  { href: "/dashboard/", label: "Leads" },
  { href: "/dashboard/sites/", label: "Websites" },
  { href: "/dashboard/whatsapp/", label: "WhatsApp" },
] as const;

/** The frame of every signed-in page: sends visitors without a session to /login/, shows the nav and the trial banner. */
export default function AppShell({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const { state, refresh } = useSession();
  const router = useRouter();
  const pathname = usePathname() ?? "";

  useEffect(() => {
    if (state.status === "anonymous") router.replace("/login/");
    if (state.status === "signed-in" && adminOnly && !state.me.user.is_admin) router.replace("/dashboard/");
  }, [state, adminOnly, router]);

  if (state.status !== "signed-in" || (adminOnly && !state.me.user.is_admin)) {
    return (
      <main className="grid min-h-screen place-items-center bg-readme text-muted" aria-busy="true">
        Loading…
      </main>
    );
  }

  const { me } = state;
  const banner = trialMessage(me.tenant);
  const signOut = async () => {
    try {
      await auth.logout();
    } finally {
      router.replace("/login/");
    }
  };

  return (
    <SessionProvider value={{ me, refresh }}>
      <div className="min-h-screen bg-readme font-[family-name:var(--font-montserrat)] text-ink">
        <header className="border-b border-line bg-readme">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
            <Link href="/" aria-label="chatbot0 home">
              <Wordmark />
            </Link>
            <nav aria-label="Dashboard" className="flex flex-wrap gap-4 text-sm font-semibold">
              {[...NAV, ...(me.user.is_admin ? [{ href: "/admin/", label: "Admin" }] : [])].map((item) => {
                const current = pathname === item.href || pathname === item.href.slice(0, -1);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={current ? "page" : undefined}
                    className={`border-b-2 py-1 ${current ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink"}`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="ml-auto flex items-center gap-3 text-sm">
              <span className="text-muted">{me.user.email}</span>
              <button type="button" className={btnSecondary} onClick={signOut}>
                Sign out
              </button>
            </div>
          </div>
        </header>
        {banner && (
          <div role="status" className="border-b border-gold bg-surface px-5 py-2 text-center text-sm font-medium">
            {banner}
          </div>
        )}
        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
      </div>
    </SessionProvider>
  );
}
