// Checks for the Slack webhook field, so a wrong paste is caught before it is sent.

export const SLACK_WEBHOOK_PREFIX = "https://hooks.slack.com/services/";

/** Whether `value` looks like a Slack incoming-webhook URL (the server checks again). */
export function isSlackWebhookUrl(value: string): boolean {
  const url = value.trim();
  return url.startsWith(SLACK_WEBHOOK_PREFIX) && url.length > SLACK_WEBHOOK_PREFIX.length && !/\s/.test(url);
}
