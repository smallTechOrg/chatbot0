import { describe, expect, it } from "vitest";
import { canonicalUrl, pageMetadata } from "./seo";

describe("pageMetadata", () => {
  const meta = pageMetadata({ path: "/pricing", title: "Pricing, chatbot0", description: "Simple pricing." });

  it("uses the title as given, with no template", () => {
    expect(meta.title).toEqual({ absolute: "Pricing, chatbot0" });
  });

  it("points the canonical and og:url at chatbot0.smalltech.in with a trailing slash", () => {
    expect(meta.alternates?.canonical).toBe("https://chatbot0.smalltech.in/pricing/");
    expect(meta.openGraph?.url).toBe("https://chatbot0.smalltech.in/pricing/");
  });

  it("keeps the landing page canonical at the root", () => {
    expect(canonicalUrl("/")).toBe("https://chatbot0.smalltech.in/");
  });

  it("sets Open Graph and Twitter images", () => {
    expect(meta.twitter).toMatchObject({ card: "summary_large_image" });
    expect(JSON.stringify(meta.openGraph?.images)).toContain("https://chatbot0.smalltech.in/og-chatbot0.png");
  });
});
