import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

let query = "";
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(query) }));
import IndustriesFromQuery from "./IndustriesFromQuery";

afterEach(cleanup);

describe("IndustriesFromQuery", () => {
  it("highlights the industry that ?industry= names, by name or slug", () => {
    query = "industry=Real%20Estate";
    const { container } = render(<IndustriesFromQuery />);
    const current = container.querySelector('[aria-current="true"]');
    expect(current?.id).toBe("real-estate");
    expect(current?.className).toContain("pub-card--current");
    expect(container.querySelector("h1")?.textContent).toBe("chatbot0 for Real Estate.");
  });

  it("highlights nothing for an unknown or removed industry", () => {
    for (query of ["industry=Small%20Business", "", "industry=nope"]) {
      const { container, unmount } = render(<IndustriesFromQuery />);
      expect(container.querySelector(".pub-card--current")).toBeNull();
      expect(container.querySelector("h1")?.textContent).toBe("One agent, shaped to your business.");
      unmount();
    }
  });

  it("lists every industry card", () => {
    query = "";
    const { container } = render(<IndustriesFromQuery />);
    expect(container.querySelectorAll("article.pub-card").length).toBe(10);
  });
});
