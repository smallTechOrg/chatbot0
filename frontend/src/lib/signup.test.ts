import { describe, expect, it } from "vitest";
import { buildEmbedScript, isFormValid, isHexColour, type SignupFields } from "./signup";

const base: SignupFields = { name: "Jane", website: "https://x.com", contactMethod: "email", email: "j@x.com", phone: "" };

describe("isFormValid", () => {
  it("needs a name, a website and the chosen contact method", () => {
    expect(isFormValid(base)).toBe(true);
    expect(isFormValid({ ...base, name: "  " })).toBe(false);
    expect(isFormValid({ ...base, website: "" })).toBe(false);
    expect(isFormValid({ ...base, email: "" })).toBe(false);
  });

  it("ignores the contact field that is not chosen", () => {
    expect(isFormValid({ ...base, contactMethod: "phone", email: "j@x.com", phone: "" })).toBe(false);
    expect(isFormValid({ ...base, contactMethod: "phone", email: "", phone: "+919876543210" })).toBe(true);
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
