"use client";

import { useCallback, useState } from "react";
import { ApiError, signUp } from "@/lib/api";
import { trackSite } from "@/lib/analytics";
import { buildEmbedScript, type SignupFields } from "@/lib/signup";

export interface SignupInput extends SignupFields {
  phone: string;
  description: string;
  colour: string;
}

/** The sign-up flow: create the account (tenant, user and website), then hand back the embed script. */
export function useSignup() {
  const [isSubmitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [embedScript, setEmbedScript] = useState<string | null>(null);

  const submit = useCallback(async (input: SignupInput) => {
    setSubmitting(true);
    setError(null);
    try {
      await signUp({
        name: input.name.trim(),
        website: input.website.trim(),
        email: input.email.trim(),
        password: input.password,
        phone: input.phone.trim() || undefined,
        description: input.description.trim() || undefined,
      });
      setEmbedScript(buildEmbedScript(input.colour));
      trackSite("sign_up");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server. Please try again.");
      trackSite("signup_error");
    } finally {
      setSubmitting(false);
    }
  }, []);

  return { isSubmitting, error, embedScript, submit };
}
