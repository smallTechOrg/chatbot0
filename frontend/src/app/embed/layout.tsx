import type { Metadata } from "next";
import "@fontsource-variable/outfit";

// The widget's font (widget.module.css reads --font-outfit), self-hosted like the site font.
const FONT = { "--font-outfit": '"Outfit Variable"' } as React.CSSProperties;

export const metadata: Metadata = {
  title: { absolute: "chatbot0 chat" },
  robots: { index: false, follow: false },
};

export default function EmbedLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // eslint-disable-next-line react/forbid-dom-props -- sets the font variable the widget CSS reads
  return <div style={FONT}>{children}</div>;
}
