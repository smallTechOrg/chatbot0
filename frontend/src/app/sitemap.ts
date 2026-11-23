import type { MetadataRoute } from "next";
import { canonicalUrl } from "@/lib/seo";

export const dynamic = "force-static";

/** The public pages, in sitemap order. */
export const PAGE_PATHS = ["/", "/pricing", "/sales", "/support", "/industries", "/about", "/signup"] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  return PAGE_PATHS.map((path) => ({ url: canonicalUrl(path) }));
}
