// Pure helpers for the sign-up form: validation and the embed snippet.

import { WIDGET_FRAME_PATH, WIDGET_ORIGIN } from "@/content/site";

export const MIN_PASSWORD_LENGTH = 10;

export interface SignupFields {
  name: string;
  website: string;
  email: string;
  password: string;
}

const HEX_COLOUR = /^#[0-9A-Fa-f]{6}$/;

export function isHexColour(value: string): boolean {
  return HEX_COLOUR.test(value);
}

/** The form can be submitted when name, website and email are filled in and the password is long enough. */
export function isFormValid(f: SignupFields): boolean {
  return f.name.trim() !== "" && f.website.trim() !== "" && f.email.trim() !== "" && f.password.length >= MIN_PASSWORD_LENGTH;
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
