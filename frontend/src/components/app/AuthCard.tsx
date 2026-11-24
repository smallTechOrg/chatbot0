import Link from "next/link";
import Wordmark from "@/components/site/Wordmark";
import { card } from "./classes";

/** The centred card the login, accept and similar pages sit in. */
export default function AuthCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <main className="grid min-h-screen place-items-center bg-readme px-5 py-10 font-[family-name:var(--font-montserrat)] text-ink">
      <div className="w-full max-w-md">
        <Link href="/" aria-label="chatbot0 home" className="mb-6 block text-center">
          <Wordmark />
        </Link>
        <div className={card}>
          <h1 className="mb-4 text-2xl font-bold">{title}</h1>
          {children}
        </div>
      </div>
    </main>
  );
}
