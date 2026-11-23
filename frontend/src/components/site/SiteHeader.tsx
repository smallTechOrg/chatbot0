"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CONTACT_EMAIL } from "@/content/site";
import Wordmark from "./Wordmark";

export const NAV_PAGES = [
  { path: "/sales", label: "Sales agent" },
  { path: "/support", label: "Support agent" },
  { path: "/industries", label: "Industries" },
  { path: "/pricing", label: "Pricing" },
  { path: "/about", label: "About" },
] as const;

export default function SiteHeader() {
  const pathname = (usePathname() ?? "/").replace(/(.)\/$/, "$1");
  const current = (path: string) => (pathname === path ? ("page" as const) : undefined);

  return (
    <header className="pub-header">
      <div className="pub-wrap pub-header__inner">
        <Link className="pub-brand" href="/" aria-label="chatbot0 home">
          <Wordmark />
        </Link>
        <nav className="pub-nav" aria-label="Main">
          {NAV_PAGES.map(({ path, label }) => (
            <Link key={path} href={`${path}/`} className="pub-nav__link" aria-current={current(path)}>
              {label}
            </Link>
          ))}
        </nav>
        <Link className="pub-btn pub-btn--primary pub-header__cta" href="/signup/">
          Sign up free
        </Link>
        <details className="pub-menu">
          <summary className="pub-menu__toggle" aria-label="Menu">
            Menu
          </summary>
          <div className="pub-menu__panel">
            <Link href="/#how">How it works</Link>
            {NAV_PAGES.map(({ path, label }) => (
              <Link key={path} href={`${path}/`} aria-current={current(path)}>
                {label}
              </Link>
            ))}
            <a href={`mailto:${CONTACT_EMAIL}`}>Contact</a>
            <Link className="pub-btn pub-btn--primary" href="/signup/">
              Sign up free
            </Link>
          </div>
        </details>
      </div>
    </header>
  );
}
