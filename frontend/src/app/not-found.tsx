import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: { absolute: "Page not found, chatbot0" }, robots: { index: false } };

// Exported as 404.html: Flask serves it with a 404 status for any path that has no file.
export default function NotFound() {
  return (
    <main className="pub pub-notfound">
      <div className="pub-wrap">
        <p className="pub-label">404</p>
        <h1 className="pub-title">That page doesn&rsquo;t exist.</h1>
        <p className="pub-lead">It may have moved. Start from the home page.</p>
        <Link className="pub-btn pub-btn--primary" href="/">
          Back to chatbot0
        </Link>
      </div>
    </main>
  );
}
