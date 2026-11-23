"use client";

import { useCallback, useState } from "react";
import { registerDomain, saveCompanyPrompt } from "@/lib/api";
import { trackSite } from "@/lib/analytics";
import { buildEmbedScript, type SignupFields } from "@/lib/signup";

export const SIGNUP_ERRORS = {
  duplicate: "This website is already signed up. Write to us at contact@smalltech.in and we'll help.",
  invalid: "Please check your website address, email or phone number.",
  failed: "Failed to register domain. Please try again.",
  unknown: "Something went wrong.",
} as const;

export interface SignupInput extends SignupFields {
  description: string;
  colour: string;
}

/** The sign-up flow: register the website, save the description, then hand back the embed script. */
export function useSignup() {
  const [isSubmitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [embedScript, setEmbedScript] = useState<string | null>(null);

  const submit = useCallback(async (input: SignupInput) => {
    setSubmitting(true);
    setError(null);
    try {
      const contact =
        input.contactMethod === "email" ? { email: input.email.trim() } : { mobile: input.phone.trim() };
      const domain = await registerDomain({
        website_url: input.website.trim(),
        contact_name: input.name.trim(),
        ...contact,
      });
      if (domain.kind !== "created") throw new Error(SIGNUP_ERRORS[domain.kind]);

      const description = input.description.trim();
      if (description && !(await saveCompanyPrompt(domain.key, description))) {
        console.warn("Prompt save failed, continuing...");
      }
      setEmbedScript(buildEmbedScript(input.colour));
      trackSite("sign_up");
    } catch (err) {
      setError(err instanceof Error ? err.message : SIGNUP_ERRORS.unknown);
      trackSite("signup_error");
    } finally {
      setSubmitting(false);
    }
  }, []);

  const reset = useCallback(() => {
    setEmbedScript(null);
    setError(null);
  }, []);

  return { isSubmitting, error, embedScript, submit, reset };
}
