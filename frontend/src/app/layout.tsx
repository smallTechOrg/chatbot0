import type { Metadata, Viewport } from "next";
import { Montserrat } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { SITE_URL } from "@/content/site";

// smallTech brand font (Brand Guidelines v1.2: Montserrat only).
const montserrat = Montserrat({ variable: "--font-montserrat", subsets: ["latin"], weight: ["400", "500", "600", "700"] });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: "chatbot0",
};

export const viewport: Viewport = { themeColor: "#F5F1EE" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={montserrat.variable}>
      <body>
        {children}
        {/* smallTech analytics: one GA4 property for every site. It runs on chatbot0.smalltech.in only. */}
        <Script src="/st-analytics.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
