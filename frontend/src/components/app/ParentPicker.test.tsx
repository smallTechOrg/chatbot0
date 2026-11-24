import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  class ApiError extends Error {
    constructor(
      public readonly status: number,
      message: string,
    ) {
      super(message);
    }
  }
  return { ApiError };
});
import { ApiError, type PromptChain } from "@/lib/api";
import ParentPicker from "./ParentPicker";

afterEach(cleanup);

const chain = (keys: string[]): PromptChain => ({ key: keys[0], chain: keys, ends_at_default: true, prompts: [] });

describe("ParentPicker", () => {
  it("offers the allowed parents without the website itself, and saves the choice", async () => {
    const save = vi.fn().mockResolvedValue(chain(["B", "A", "COMMON"]));
    const onSaved = vi.fn();
    render(<ParentPicker siteKey="B" current="COMMON" options={["COMMON", "A", "B"]} save={save} onSaved={onSaved} />);
    const select = screen.getByLabelText("Parent website") as HTMLSelectElement;
    expect([...select.options].map((o) => o.value)).toEqual(["COMMON", "A"]);
    expect((screen.getByRole("button", { name: "Set parent" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(select, { target: { value: "A" } });
    fireEvent.click(screen.getByRole("button", { name: "Set parent" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(save).toHaveBeenCalledWith("B", "A");
    expect(screen.getByRole("status").textContent).toContain("B → A → COMMON");
  });

  it("shows the server's message when the change is refused", async () => {
    const save = vi.fn().mockRejectedValue(new ApiError(400, "That is a loop."));
    const onSaved = vi.fn();
    render(<ParentPicker siteKey="A" current="COMMON" options={["COMMON", "B"]} save={save} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText("Parent website"), { target: { value: "B" } });
    fireEvent.click(screen.getByRole("button", { name: "Set parent" }));
    expect((await screen.findByRole("alert")).textContent).toContain("That is a loop.");
    expect(onSaved).not.toHaveBeenCalled();
  });
});
