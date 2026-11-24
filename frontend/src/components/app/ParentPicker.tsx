"use client";

import { useState } from "react";
import { ApiError, type PromptChain } from "@/lib/api";
import { alertError, alertOk, btnSecondary, input, label } from "./classes";

/**
 * Choose the website this one inherits its prompts from. `options` are the allowed parents (the server checks
 * them again and rejects loops). `save` returns the new chain; `onSaved` lets the chain view reload.
 */
export default function ParentPicker({
  siteKey,
  current,
  options,
  disabled,
  save,
  onSaved,
}: {
  siteKey: string;
  /** The present parent's key, or null. */
  current: string | null;
  options: string[];
  disabled?: boolean;
  save: (key: string, parentKey: string) => Promise<PromptChain>;
  onSaved: (chain: PromptChain) => void;
}) {
  const [choice, setChoice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const choices = [...new Set(options)].filter((k) => k !== siteKey);
  const selected = choice ?? current ?? "";
  const id = `parent-${siteKey}`;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const chain = await save(siteKey, selected);
      setChoice(null);
      setMessage({ ok: true, text: `Saved. The new order is ${chain.chain.join(" → ")}.` });
      onSaved(chain);
    } catch (err) {
      setMessage({ ok: false, text: err instanceof ApiError ? err.message : "Could not change the parent." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-56 flex-1">
          <label className={label} htmlFor={id}>
            Parent website
          </label>
          <select id={id} className={input} value={selected} disabled={disabled || busy} onChange={(e) => setChoice(e.target.value)}>
            {current === null && selected === "" && <option value="">None</option>}
            {current !== null && !choices.includes(current) && <option value={current}>{current}</option>}
            {choices.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" className={btnSecondary} disabled={disabled || busy || selected === "" || selected === current}>
          Set parent
        </button>
      </div>
      <p className="text-xs text-muted">
        This website uses its own prompts first, then its parent&apos;s, and so on up. The parent is shared by every address of this website
        (including its www version).
      </p>
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? alertOk : alertError}>
          {message.text}
        </p>
      )}
    </form>
  );
}
