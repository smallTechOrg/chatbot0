import { describe, expect, it } from "vitest";
import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("renders bold, lists and line breaks", () => {
    expect(renderMarkdown("**hi**")).toContain("<strong>hi</strong>");
    expect(renderMarkdown("- a\n- b")).toContain("<li>a</li>");
    expect(renderMarkdown("one\ntwo")).toContain("<br>");
  });

  it("shows raw HTML as text instead of rendering it", () => {
    const html = renderMarkdown('<img src=x onerror="alert(1)"> and <script>alert(1)</script>');
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<script");
    expect(html).toContain("&lt;script&gt;");
  });

  it("drops links that are not http(s), mailto or tel", () => {
    expect(renderMarkdown("[x](javascript:alert(1))")).not.toContain("href");
    expect(renderMarkdown("[x](JaVaScRiPt:alert(1))")).not.toContain("href");
    expect(renderMarkdown("[x](data:text/html,hi)")).not.toContain("href");
  });

  it("opens safe links in a new tab without leaking the opener", () => {
    const html = renderMarkdown("[site](https://example.com)");
    expect(html).toContain('href="https://example.com"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain("noopener");
  });
});
