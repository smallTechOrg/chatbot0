import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import DisplayNameStatus, { WHATSAPP_MANAGER_URL, describeNameStatus } from "./DisplayNameStatus";

afterEach(cleanup);

describe("DisplayNameStatus", () => {
  it("maps Meta's statuses to plain wording and shows unknown ones raw", () => {
    expect(describeNameStatus("APPROVED")).toBe("Approved");
    expect(describeNameStatus("PENDING_REVIEW")).toBe("In review by Meta");
    expect(describeNameStatus("DECLINED")).toBe("Declined by Meta: edit and resubmit in WhatsApp Manager");
    expect(describeNameStatus("SOMETHING_NEW")).toBe("SOMETHING_NEW");
    expect(describeNameStatus(null)).toBe("Not checked yet");
  });

  it("renders the Display name line", () => {
    render(<DisplayNameStatus nameStatus="PENDING_REVIEW" lastError={null} />);
    expect(screen.getByText(/Display name:/).parentElement?.textContent).toContain("In review by Meta");
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("links to WhatsApp Manager when the last error is 131037", () => {
    render(<DisplayNameStatus nameStatus="DECLINED" lastError="HTTP 400: needs display name approval (code 131037)" />);
    const link = screen.getByRole("link", { name: "WhatsApp Manager" });
    expect(link.getAttribute("href")).toBe(WHATSAPP_MANAGER_URL);
    expect(screen.getByText(/needs Meta approval/)).toBeTruthy();
  });
});
