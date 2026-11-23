import Link from "next/link";
import { GITHUB_URL, LINKEDIN_URL, ZER0_URL, mailto } from "@/content/site";
import Wordmark from "./Wordmark";

export default function SiteFooter() {
  return (
    <footer className="pub-footer">
      <div className="pub-wrap pub-footer__inner">
        <div className="pub-footer__brand">
          <Wordmark />
          <span className="pub-footer__by">by</span>
          <a href="https://smalltech.in" className="pub-footer__logo" aria-label="smallTech">
            {/* eslint-disable-next-line @next/next/no-img-element -- a static SVG lockup; next/image is not used in the static export */}
            <img src="/logo-smalltech.svg" alt="smallTech" width={416} height={92} />
          </a>
        </div>
        <div className="pub-footer__meta">
          <nav className="pub-footer__nav" aria-label="Footer">
            <Link href="/sales/">sales agent</Link>
            <Link href="/support/">support agent</Link>
            <Link href="/industries/">industries</Link>
            <Link href="/about/">about</Link>
            <a href={ZER0_URL}>Zer0</a>
            <a href={mailto("chatbot0")}>contact</a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              github
            </a>
            <a href={LINKEDIN_URL} target="_blank" rel="noreferrer">
              linkedin
            </a>
          </nav>
          <span className="pub-footer__legal">&copy; 2026 madhyamakist pvt ltd</span>
        </div>
      </div>
    </footer>
  );
}
