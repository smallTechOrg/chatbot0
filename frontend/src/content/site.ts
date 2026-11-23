// URLs and contact details shared by every public page. Ported from chatbot0/content.py.

export const SITE_URL = "https://chatbot0.smalltech.in";
export const ZER0_URL = "https://zer0.smalltech.in";
export const CONTACT_EMAIL = "contact@smalltech.in";
export const GITHUB_URL = "https://github.com/smallTechOrg";
export const LINKEDIN_URL = "https://www.linkedin.com/company/madhyamakist";

/** Where the chat widget (embed.js and the /embed/ frame) is served from: this app. */
export const WIDGET_ORIGIN = SITE_URL;

/** The widget colour the sign-up form starts with, and its preset swatches (the visitor's widget, not the page palette). */
export const DEFAULT_WIDGET_COLOUR = "#219EBC";
export const WIDGET_COLOURS = [
  "#219EBC",
  "#023047",
  "#FB8500",
  "#FFB703",
  "#E63946",
  "#2D6A4F",
  "#7209B7",
  "#000000",
] as const;

export const mailto = (subject?: string): string =>
  subject ? `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}` : `mailto:${CONTACT_EMAIL}`;
