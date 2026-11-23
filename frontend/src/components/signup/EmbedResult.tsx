"use client";

import { useEffect, useRef, useState } from "react";
import { trackSite } from "@/lib/analytics";

interface Props {
  script: string;
  colour: string;
  onRestart: () => void;
}

/** Copy to the clipboard; older browsers and non-HTTPS pages have no navigator.clipboard, so select and execCommand. */
async function copyText(text: string, fallbackTarget: HTMLElement | null): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      /* fall through to the selection copy */
    }
  }
  if (!fallbackTarget) return false;
  const range = document.createRange();
  range.selectNodeContents(fallbackTarget);
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  if (ok) selection?.removeAllRanges();
  return ok;
}

/** The "you're all set" step: the script to paste, a copy button and a preview of the widget button. */
export default function EmbedResult({ script, colour, onRestart }: Props) {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    titleRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2500);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    if (await copyText(script, codeRef.current)) {
      setCopied(true);
      trackSite("embed_code_copy");
    }
  };

  return (
    <div>
      <div className="pub-section__head">
        <p className="pub-label">Done</p>
        <h1 className="pub-title" tabIndex={-1} ref={titleRef}>
          You&apos;re <span className="pub-accent">all set.</span>
        </h1>
        <p className="pub-lead">
          Copy the script below and paste it into your website&apos;s HTML, just before the closing{" "}
          <code className="pub-code-inline">&lt;/body&gt;</code> tag.
        </p>
      </div>
      <div className="pub-embed">
        <pre className="pub-embed__code">
          <code ref={codeRef}>{script}</code>
        </pre>
        <button type="button" className="pub-btn pub-btn--primary pub-embed__copy" onClick={copy}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <p className="pub-label pub-embed__preview-label">Preview</p>
      {/* eslint-disable-next-line react/forbid-dom-props -- the colour is the visitor's own choice */}
      <span className="pub-widget-preview" style={{ background: colour }}>
        <span aria-hidden="true">💬</span> Chat with us
      </span>
      <div className="pub-actions pub-embed__after">
        <button type="button" className="pub-btn pub-btn--secondary" onClick={onRestart}>
          &larr; Start over
        </button>
      </div>
    </div>
  );
}
