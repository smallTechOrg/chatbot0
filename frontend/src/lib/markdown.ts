// Bot replies are Markdown written by an LLM, shown in the widget on a customer's page. They are
// untrusted: raw HTML is escaped and only safe link targets are kept.

import { Marked, type Tokens } from "marked";

const SAFE_HREF = /^(https?:\/\/|mailto:|tel:|\/|#)/i;

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

const parser = new Marked({
  async: false,
  breaks: true, // a single newline is a line break
  gfm: true,
  renderer: {
    // Raw HTML in the reply is shown as text, never rendered.
    html: ({ text }: Tokens.HTML | Tokens.Tag) => escapeHtml(text),
    link({ href, title, tokens }: Tokens.Link) {
      const label = this.parser.parseInline(tokens);
      if (!SAFE_HREF.test(href.trim())) return label;
      const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
      return `<a href="${escapeHtml(href)}"${titleAttr} target="_blank" rel="noopener noreferrer">${label}</a>`;
    },
    image: ({ text }: Tokens.Image) => escapeHtml(text),
  },
});

/** The reply as safe HTML. */
export function renderMarkdown(text: string): string {
  return parser.parse(text) as string;
}
