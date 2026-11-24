import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSignup, type SignupInput } from "./useSignup";

vi.mock("@/lib/api", async () => {
  class ApiError extends Error {
    constructor(
      public readonly status: number,
      message: string,
    ) {
      super(message);
    }
  }
  return { ApiError, signUp: vi.fn() };
});
import { ApiError, signUp } from "@/lib/api";

const input: SignupInput = {
  name: " Jane ",
  website: " https://x.com ",
  email: " j@x.com ",
  password: "long enough pw",
  phone: "",
  description: " We sell things ",
  colour: "#219EBC",
};

beforeEach(() => vi.resetAllMocks());

describe("useSignup", () => {
  it("creates the account with trimmed fields and returns the embed script", async () => {
    vi.mocked(signUp).mockResolvedValue({ user: { id: 1, email: "j@x.com", is_admin: false, tenant_id: 2 }, domain: { key: "X_COM", address: "x.com" } });
    const { result } = renderHook(() => useSignup());

    await act(() => result.current.submit(input));

    expect(signUp).toHaveBeenCalledWith({
      name: "Jane",
      website: "https://x.com",
      email: "j@x.com",
      password: "long enough pw",
      phone: undefined,
      description: "We sell things",
    });
    expect(result.current.embedScript).toContain('data-colour="#219EBC"');
    expect(result.current.error).toBeNull();
  });

  it("passes the phone number when given", async () => {
    vi.mocked(signUp).mockResolvedValue({ user: { id: 1, email: "j@x.com", is_admin: false, tenant_id: 2 }, domain: { key: "X_COM", address: "x.com" } });
    const { result } = renderHook(() => useSignup());
    await act(() => result.current.submit({ ...input, phone: " +91 98765 43210 " }));
    expect(vi.mocked(signUp).mock.calls[0][0].phone).toBe("+91 98765 43210");
  });

  it("shows the server's message and no embed script when sign-up is refused", async () => {
    vi.mocked(signUp).mockRejectedValue(new ApiError(409, "This website is already signed up."));
    const { result } = renderHook(() => useSignup());

    await act(() => result.current.submit(input));

    expect(result.current.error).toBe("This website is already signed up.");
    expect(result.current.embedScript).toBeNull();
    expect(result.current.isSubmitting).toBe(false);
  });

  it("shows a generic message when the server cannot be reached", async () => {
    vi.mocked(signUp).mockRejectedValue(new TypeError("fetch failed"));
    const { result } = renderHook(() => useSignup());
    await act(() => result.current.submit(input));
    expect(result.current.error).toMatch(/Could not reach the server/);
  });
});
