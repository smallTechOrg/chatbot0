import { describe, expect, it } from "vitest";
import { isHttpsUrl, isSlackWebhookUrl } from "./slack";

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

describe("isHttpsUrl", () => {
  it("accepts https addresses", () => {
    expect(isHttpsUrl(" https://crm.acme.test/leads?x=1 ")).toBe(true);
  });

  it.each(["", "crm.acme.test", "http://crm.acme.test", "https://", "javascript:alert(1)", "https://a.test/x y", "https://a.test/<b>", "https://a.test/x|y"])(
    "rejects %j",
    (value) => {
      expect(isHttpsUrl(value)).toBe(false);
    },
  );
});
