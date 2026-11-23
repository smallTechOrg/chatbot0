import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SIGNUP_ERRORS, useSignup, type SignupInput } from "./useSignup";

vi.mock("@/lib/api", () => ({ registerDomain: vi.fn(), saveCompanyPrompt: vi.fn() }));
import { registerDomain, saveCompanyPrompt } from "@/lib/api";

const input: SignupInput = {
  name: " Jane ",
  website: " https://x.com ",
  contactMethod: "email",
  email: " j@x.com ",
  phone: "",
  description: "We sell things",
  colour: "#219EBC",
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(console, "warn").mockImplementation(() => {});
});

describe("useSignup", () => {
  it("registers the domain with the contact details, saves the prompt, then returns the embed script", async () => {
    vi.mocked(registerDomain).mockResolvedValue({ kind: "created", key: "x.com" });
    vi.mocked(saveCompanyPrompt).mockResolvedValue(true);
    const { result } = renderHook(() => useSignup());

    await act(() => result.current.submit(input));

    expect(registerDomain).toHaveBeenCalledWith({ website_url: "https://x.com", contact_name: "Jane", email: "j@x.com" });
    expect(saveCompanyPrompt).toHaveBeenCalledWith("x.com", "We sell things");
    expect(result.current.embedScript).toContain('data-colour="#219EBC"');
    expect(result.current.error).toBeNull();
  });

  it("sends the phone as mobile when that is the chosen method, and skips an empty description", async () => {
    vi.mocked(registerDomain).mockResolvedValue({ kind: "created", key: "x.com" });
    const { result } = renderHook(() => useSignup());

    await act(() => result.current.submit({ ...input, contactMethod: "phone", phone: "+91 98", description: " " }));

    expect(registerDomain).toHaveBeenCalledWith({ website_url: "https://x.com", contact_name: "Jane", mobile: "+91 98" });
    expect(saveCompanyPrompt).not.toHaveBeenCalled();
  });

  it.each([
    ["duplicate", SIGNUP_ERRORS.duplicate],
    ["invalid", SIGNUP_ERRORS.invalid],
    ["failed", SIGNUP_ERRORS.failed],
  ] as const)("shows the %s error and no embed script", async (kind, message) => {
    vi.mocked(registerDomain).mockResolvedValue({ kind });
    const { result } = renderHook(() => useSignup());

    await act(() => result.current.submit(input));

    expect(result.current.error).toBe(message);
    expect(result.current.embedScript).toBeNull();
    expect(saveCompanyPrompt).not.toHaveBeenCalled();
    expect(result.current.isSubmitting).toBe(false);
  });

  it("continues when saving the prompt fails", async () => {
    vi.mocked(registerDomain).mockResolvedValue({ kind: "created", key: "x.com" });
    vi.mocked(saveCompanyPrompt).mockResolvedValue(false);
    const { result } = renderHook(() => useSignup());

    await act(() => result.current.submit(input));

    expect(result.current.embedScript).not.toBeNull();
  });

  it("goes back to the form on reset", async () => {
    vi.mocked(registerDomain).mockResolvedValue({ kind: "created", key: "x.com" });
    const { result } = renderHook(() => useSignup());
    await act(() => result.current.submit(input));
    act(() => result.current.reset());
    expect(result.current.embedScript).toBeNull();
  });
});
