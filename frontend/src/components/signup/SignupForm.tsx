"use client";

import { useRef, useState } from "react";
import { DEFAULT_WIDGET_COLOUR, WIDGET_COLOURS, mailto, CONTACT_EMAIL } from "@/content/site";
import { FREE_CONVERSATIONS } from "@/content/plans";
import { useSignup } from "@/hooks/useSignup";
import { trackSite } from "@/lib/analytics";
import { MIN_PASSWORD_LENGTH, isFormValid, isHexColour } from "@/lib/signup";
import EmbedResult from "./EmbedResult";

/** The sign-up form, and after a successful submit the embed script. Phase 3 turns this into account creation. */
export default function SignupForm() {
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [description, setDescription] = useState("");
  const [colour, setColour] = useState<string>(DEFAULT_WIDGET_COLOUR);
  const startTracked = useRef(false);
  const { isSubmitting, error, embedScript, submit } = useSignup();

  const fields = { name, website, email, password };
  const canSubmit = isFormValid(fields) && !isSubmitting;
  const pickerValue = isHexColour(colour) ? colour.toLowerCase() : DEFAULT_WIDGET_COLOUR.toLowerCase();

  if (embedScript) {
    return <EmbedResult script={embedScript} colour={colour} />;
  }

  return (
    <div>
      <div className="pub-section__head">
        <p className="pub-label">Sign up free</p>
        <h1 className="pub-title">
          Your AI chat agent, <span className="pub-accent">live in minutes.</span>
        </h1>
        <p className="pub-lead">
          Tell us about your business and get the one line of code that puts chatbot0 on your website.{" "}
          {FREE_CONVERSATIONS} conversations a month free, no card needed.
        </p>
      </div>

      <noscript>
        <p className="pub-alert">
          The sign-up form needs JavaScript. Turn it on, or email{" "}
          <a className="pub-link" href={mailto("chatbot0 sign-up")}>
            {CONTACT_EMAIL}
          </a>{" "}
          and we&apos;ll set you up.
        </p>
      </noscript>

      <form
        className="pub-form"
        id="signup-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) void submit({ ...fields, phone, description, colour });
        }}
      >
        <div className="pub-field">
          <label className="pub-field__label" htmlFor="su-name">
            Your name
          </label>
          <input
            className="pub-input"
            id="su-name"
            type="text"
            placeholder="Jane Doe"
            autoComplete="name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            onFocus={() => {
              if (startTracked.current) return;
              startTracked.current = true;
              trackSite("signup_form_start");
            }}
          />
        </div>

        <div className="pub-field">
          <label className="pub-field__label" htmlFor="su-website">
            Website URL
          </label>
          <input
            className="pub-input"
            id="su-website"
            type="url"
            placeholder="https://www.example.com"
            autoComplete="url"
            required
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
        </div>

        <div className="pub-field">
          <label className="pub-field__label" htmlFor="su-email">
            Email
          </label>
          <input
            className="pub-input"
            id="su-email"
            type="email"
            placeholder="jane@example.com"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="pub-field">
          <label className="pub-field__label" htmlFor="su-password">
            Password <span className="pub-field__hint">(at least {MIN_PASSWORD_LENGTH} characters; you sign in to your dashboard with it)</span>
          </label>
          <input
            className="pub-input"
            id="su-password"
            type="password"
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <div className="pub-field">
          <label className="pub-field__label" htmlFor="su-phone">
            Phone <span className="pub-field__hint">(optional)</span>
          </label>
          <input
            className="pub-input"
            id="su-phone"
            type="tel"
            placeholder="+919876543210"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>

        <div className="pub-field">
          <label className="pub-field__label" htmlFor="su-prompt">
            About your business{" "}
            <span className="pub-field__hint">
              (optional: what you offer, who it&apos;s for, prices, policies, FAQs. The more detail you give, the smarter it
              gets.)
            </span>
          </label>
          <textarea
            className="pub-input pub-input--area"
            id="su-prompt"
            rows={4}
            placeholder="We are XYZ Interiors, a design studio in Pune. We fit out homes and offices, from single rooms to full projects. Consultations are free and..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <fieldset className="pub-field">
          <legend className="pub-field__label">Widget colour</legend>
          <div className="pub-colour">
            <input
              className="pub-colour__picker"
              id="su-colour-picker"
              type="color"
              value={pickerValue}
              aria-label="Pick a widget colour"
              onChange={(e) => setColour(e.target.value)}
            />
            <label className="pub-sr" htmlFor="su-colour">
              Widget colour (hex)
            </label>
            <input
              className="pub-input pub-input--mono"
              id="su-colour"
              type="text"
              pattern="^#[0-9A-Fa-f]{6}$"
              spellCheck={false}
              value={colour}
              onChange={(e) => setColour(e.target.value)}
            />
            {/* eslint-disable-next-line react/forbid-dom-props -- the colour is the visitor's own choice */}
            <span className="pub-colour__bubble" style={{ background: colour }} aria-hidden="true">
              💬
            </span>
          </div>
          <div className="pub-swatches">
            {WIDGET_COLOURS.map((c) => (
              <button
                key={c}
                type="button"
                className="pub-swatch"
                aria-label={`Select colour ${c}`}
                aria-pressed={colour === c}
                // eslint-disable-next-line react/forbid-dom-props -- each swatch is its own colour
                style={{ background: c }}
                onClick={() => setColour(c)}
              />
            ))}
          </div>
        </fieldset>

        {error && (
          <p className="pub-alert" id="signup-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="pub-btn pub-btn--primary pub-form__submit" id="signup-submit" disabled={!canSubmit}>
          {isSubmitting ? "Setting up your agent…" : "Get my embed script"}
        </button>
        <p className="pub-caption">
          Questions or a custom setup?{" "}
          <a className="pub-link" href={mailto("chatbot0 sign-up")}>
            {CONTACT_EMAIL}
          </a>
        </p>
      </form>
    </div>
  );
}
