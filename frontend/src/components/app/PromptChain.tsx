"use client";

import { useEffect, useState } from "react";
import { ApiError, sites, type PromptChain as Chain } from "@/lib/api";
import { alertError } from "./classes";

const BADGE: Record<string, string> = {
  own: "border-ok text-ok",
  inherited: "border-gold text-gold-60",
  default: "border-line text-muted",
  missing: "border-bad text-bad",
};

/** Read-only: the parent chain of a website and, for each prompt the bot uses, which website's text is in effect. */
export default function PromptChain({
  siteKey,
  version = 0,
  onLoaded,
}: {
  siteKey: string;
  /** Change it to load the chain again (after the parent was changed). */
  version?: number;
  onLoaded?: (chain: Chain) => void;
}) {
  const [data, setData] = useState<Chain | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setData(null);
    setError(null);
    sites.promptChain(siteKey).then(
      (d) => {
        if (!current) return;
        setData(d);
        onLoaded?.(d);
      },
      (err) => current && setError(err instanceof ApiError ? err.message : "Could not load the prompt hierarchy."),
    );
    return () => {
      current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onLoaded is a callback the parent may recreate
  }, [siteKey, version]);

  if (error) {
    return (
      <p role="alert" className={alertError}>
        {error}
      </p>
    );
  }
  if (!data) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <div className="space-y-3">
      <p className="text-sm" data-testid="prompt-chain">
        <span className="font-semibold">Lookup order: </span>
        {data.chain.map((k, i) => (
          <span key={k}>
            {i > 0 && " → "}
            <code className="rounded bg-surface px-1">{k}</code>
          </span>
        ))}
        {!data.ends_at_default && <span className="text-muted"> (does not reach the default COMMON prompts)</span>}
      </p>
      <p className="text-xs text-muted">
        The bot uses a website&apos;s own prompt when it has one. Otherwise it looks at its parent, then the parent&apos;s parent, and so on.
      </p>
      <ul className="divide-y divide-line text-sm">
        {data.prompts.map((p) => (
          <li key={`${p.agent_type}/${p.type}`} className="py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">
                {p.agent_type}: {p.type}
              </span>
              <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${BADGE[p.origin] ?? BADGE.missing}`}>{p.label}</span>
            </div>
            {p.preview && <p className="mt-1 whitespace-pre-wrap text-xs text-muted">{p.preview}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
