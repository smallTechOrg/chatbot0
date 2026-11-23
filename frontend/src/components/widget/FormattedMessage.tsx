"use client";

import { useMemo } from "react";
import { renderMarkdown } from "@/lib/markdown";

/** A bot reply as formatted Markdown (see lib/markdown.ts: HTML is escaped, only safe links kept). */
export default function FormattedMessage({ text, className }: { text: string; className?: string }) {
  const html = useMemo(() => renderMarkdown(text), [text]);
  return <div className={`inline ${className ?? ""}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
