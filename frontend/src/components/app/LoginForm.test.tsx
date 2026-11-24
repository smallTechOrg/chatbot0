import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }), useSearchParams: () => new URLSearchParams("token=abc") }));
vi.mock("@/lib/api", async () => {
  class ApiError extends Error {
    constructor(
      public readonly status: number,
      message: string,
    ) {
      super(message);
    }
  }
  return { ApiError, auth: { status: vi.fn(), login: vi.fn(), bootstrap: vi.fn(), accept: vi.fn() } };
});
import { ApiError, auth } from "@/lib/api";
import AcceptForm from "./AcceptForm";
import LoginForm from "./LoginForm";

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(auth.status).mockResolvedValue({ needs_bootstrap: false });
});
afterEach(cleanup);

function type(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("LoginForm", () => {
  it("signs in and goes to the dashboard", async () => {
    vi.mocked(auth.login).mockResolvedValue({ id: 1, email: "a@b.co", is_admin: false, tenant_id: 1 });
    render(<LoginForm />);
    type("Email", "a@b.co");
    type("Password", "secret-password");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard/"));
    expect(auth.login).toHaveBeenCalledWith("a@b.co", "secret-password");
  });

  it("shows the server's message when sign-in fails", async () => {
    vi.mocked(auth.login).mockRejectedValue(new ApiError(401, "Wrong email or password."));
    render(<LoginForm />);
    type("Email", "a@b.co");
    type("Password", "nope-nope-nope");
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Wrong email or password.");
    expect(replace).not.toHaveBeenCalled();
  });

  it("offers first-time setup only while the server says it is needed", async () => {
    const { unmount } = render(<LoginForm />);
    await waitFor(() => expect(auth.status).toHaveBeenCalled());
    expect(screen.queryByText("First-time setup")).toBeNull();
    unmount();
    vi.mocked(auth.status).mockResolvedValue({ needs_bootstrap: true });
    render(<LoginForm />);
    fireEvent.click(await screen.findByText("First-time setup"));
    vi.mocked(auth.bootstrap).mockResolvedValue({ id: 1, email: "root@b.co", is_admin: true, tenant_id: 1 });
    type("Setup password", "shared");
    type("Email", "root@b.co");
    type("Choose your password", "a long enough password");
    fireEvent.click(screen.getByRole("button", { name: "Create the admin account" }));
    await waitFor(() => expect(auth.bootstrap).toHaveBeenCalledWith("shared", "root@b.co", "a long enough password"));
  });
});

describe("AcceptForm", () => {
  it("will not submit while the two passwords differ", () => {
    render(<AcceptForm />);
    type("New password", "a long enough password");
    type("Type it again", "something else entirely");
    expect(screen.getByText("The passwords do not match.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Save password and sign in" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("sends the token from the link with the new password", async () => {
    vi.mocked(auth.accept).mockResolvedValue({ id: 1, email: "a@b.co", is_admin: false, tenant_id: 1 });
    render(<AcceptForm />);
    type("New password", "a long enough password");
    type("Type it again", "a long enough password");
    fireEvent.click(screen.getByRole("button", { name: "Save password and sign in" }));
    await waitFor(() => expect(auth.accept).toHaveBeenCalledWith("abc", "a long enough password"));
    expect(replace).toHaveBeenCalledWith("/dashboard/");
  });
});
