import type { Metadata } from "next";
import { Outfit } from "next/font/google";

// The widget's font (widget.module.css reads --font-outfit).
const outfit = Outfit({ variable: "--font-outfit", subsets: ["latin"], weight: ["300", "400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: { absolute: "chatbot0 chat" },
  robots: { index: false, follow: false },
};

export default function EmbedLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <div className={outfit.variable}>{children}</div>;
}
