import { describe, expect, it } from "vitest";
import { isSlackWebhookUrl } from "./slack";

describe("isSlackWebhookUrl", () => {
  it("accepts a Slack incoming webhook, with surrounding spaces", () => {
    expect(isSlackWebhookUrl(" https://hooks.slack.com/services/T000/B000/abc ")).toBe(true);
  });

  it.each(["", "hooks.slack.com/services/T/B/c", "http://hooks.slack.com/services/T/B/c", "https://evil.example/services/T/B/c", "https://hooks.slack.com/services/", "https://hooks.slack.com/services/T B/c"])(
    "rejects %j",
    (value) => {
      expect(isSlackWebhookUrl(value)).toBe(false);
    },
  );
});
