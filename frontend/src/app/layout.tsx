import type { Metadata, Viewport } from "next";
import "@fontsource-variable/montserrat";
import Script from "next/script";
import "./globals.css";
import { SITE_URL } from "@/content/site";

// smallTech brand font (Brand Guidelines v1.2: Montserrat only). Self-hosted from the npm package: the build
// needs no network (next/font/google fetched Google Fonts at build time and flaked in CI and Docker builds).

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: "chatbot0",
};

export const viewport: Viewport = { themeColor: "#F5F1EE" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        {/* smallTech analytics: one GA4 property for every site. It runs on chatbot0.smalltech.in only. */}
        <Script src="/st-analytics.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
