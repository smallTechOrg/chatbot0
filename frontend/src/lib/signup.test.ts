import { describe, expect, it } from "vitest";
import { buildEmbedScript, isFormValid, isHexColour, type SignupFields } from "./signup";

const base: SignupFields = { name: "Jane", website: "https://x.com", email: "j@x.com", password: "long enough pw" };

describe("isFormValid", () => {
  it("needs a name, a website, an email and a password of at least 10 characters", () => {
    expect(isFormValid(base)).toBe(true);
    expect(isFormValid({ ...base, name: "  " })).toBe(false);
    expect(isFormValid({ ...base, website: "" })).toBe(false);
    expect(isFormValid({ ...base, email: "" })).toBe(false);
    expect(isFormValid({ ...base, password: "123456789" })).toBe(false);
    expect(isFormValid({ ...base, password: "1234567890" })).toBe(true);
  });
});

describe("isHexColour", () => {
  it("accepts #rrggbb only", () => {
    expect(isHexColour("#219EBC")).toBe(true);
    expect(isHexColour("#fff")).toBe(false);
    expect(isHexColour("219EBC")).toBe(false);
  });
});

describe("buildEmbedScript", () => {
  const script = buildEmbedScript("#FB8500");

  it("loads embed.js and the /embed/ frame from chatbot0, not zer0", () => {
    expect(script).toContain('src="https://chatbot0.smalltech.in/embed.js"');
    expect(script).toContain('data-chat-url="https://chatbot0.smalltech.in/embed/"');
    expect(script).not.toContain("zer0.smalltech.in");
  });

  it("carries the chosen colour and the default tagline", () => {
    expect(script).toContain('data-colour="#FB8500"');
    expect(script).toContain('data-tagline="Chat with us"');
    expect(script.endsWith("></script>")).toBe(true);
  });
});
