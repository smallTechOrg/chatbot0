// Per-page metadata for the public pages: title, description, canonical, Open Graph and Twitter tags.

import type { Metadata } from "next";
import { SITE_URL } from "@/content/site";

export interface PageSeo {
  /** Path with a leading slash, "/" for the landing page. */
  path: string;
  title: string;
  description: string;
}

const OG_IMAGE = `${SITE_URL}/og-chatbot0.png`;
const OG_ALT = "chatbot0, the AI chat agent for business websites, by smallTech";

/** The canonical URL of a page. It ends in a slash, like every URL of the export (`trailingSlash: true`). */
export function canonicalUrl(path: string): string {
  return SITE_URL + (path.endsWith("/") ? path : `${path}/`);
}

export function pageMetadata({ path, title, description }: PageSeo): Metadata {
  const url = canonicalUrl(path);
  return {
    title: { absolute: title },
    description,
    robots: { index: true, follow: true },
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      siteName: "chatbot0",
      locale: "en_US",
      title,
      description,
      url,
      images: [{ url: OG_IMAGE, width: 1200, height: 630, alt: OG_ALT }],
    },
    twitter: { card: "summary_large_image", title, description, images: [OG_IMAGE] },
  };
}
