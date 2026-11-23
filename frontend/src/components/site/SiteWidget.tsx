"use client";

import { useEffect } from "react";
import { SITE_URL, WIDGET_ORIGIN } from "@/content/site";

/** True on chatbot0's own host: the widget needs a `domains` row for the page's origin, and only that host has one. */
export function widgetWanted(hostname: string): boolean {
  return hostname === new URL(SITE_URL).hostname;
}

/** Loads chatbot0's own chat widget on chatbot0.smalltech.in, the same one customers embed. */
export default function SiteWidget() {
  useEffect(() => {
    if (!widgetWanted(window.location.hostname)) return;
    const script = document.createElement("script");
    script.src = `${WIDGET_ORIGIN}/embed.js`;
    script.defer = true;
    script.dataset.chatUrl = `${WIDGET_ORIGIN}/embed/`;
    script.dataset.colour = "#1C1B18";
    script.dataset.tagline = "Talk to us";
    document.body.appendChild(script);
    return () => script.remove();
  }, []);
  return null;
}
