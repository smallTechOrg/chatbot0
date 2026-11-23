import { describe, expect, it } from "vitest";
import { widgetWanted } from "./SiteWidget";

describe("widgetWanted", () => {
  it("loads the widget on chatbot0's own host only", () => {
    expect(widgetWanted("chatbot0.smalltech.in")).toBe(true);
    expect(widgetWanted("zero-sales-agent-a23rjysfbq-uc.a.run.app")).toBe(false);
    expect(widgetWanted("localhost")).toBe(false);
  });
});
