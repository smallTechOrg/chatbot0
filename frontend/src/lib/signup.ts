// Pure helpers for the sign-up form: validation and the embed snippet.

import { WIDGET_FRAME_PATH, WIDGET_ORIGIN } from "@/content/site";

export type ContactMethod = "email" | "phone";

export interface SignupFields {
  name: string;
  website: string;
  contactMethod: ContactMethod;
  email: string;
  phone: string;
}

const HEX_COLOUR = /^#[0-9A-Fa-f]{6}$/;

export function isHexColour(value: string): boolean {
  return HEX_COLOUR.test(value);
}

/** The form can be submitted when the name, the website and the chosen contact method are filled in. */
export function isFormValid(f: SignupFields): boolean {
  const contact = f.contactMethod === "email" ? f.email : f.phone;
  return f.name.trim() !== "" && f.website.trim() !== "" && contact.trim() !== "";
}

/** The one-line script a customer pastes into their site. */
export function buildEmbedScript(colour: string): string {
  return [
    "<script",
    `  src="${WIDGET_ORIGIN}/embed.js"`,
    `  data-chat-url="${WIDGET_ORIGIN}${WIDGET_FRAME_PATH}"`,
    `  data-colour="${colour}"`,
    '  data-tagline="Chat with us"',
    "  defer",
    "></script>",
  ].join("\n");
}
