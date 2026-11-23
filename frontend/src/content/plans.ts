// Pricing, in one place so it can change without touching the pages. The owner has not
// confirmed these prices are current (SMA-8). Ported from chatbot0/content.py.

export interface Plan {
  key: "free" | "basic" | "pro";
  name: string;
  /** USD per month, billed monthly. */
  monthly: number;
  /** USD per month, billed yearly; null for the free plan. */
  yearly: number | null;
  /** [feature, included] */
  features: ReadonlyArray<readonly [string, boolean]>;
  cta: string;
  featured?: boolean;
}

export const PLANS: readonly Plan[] = [
  {
    key: "free",
    name: "Free",
    monthly: 0,
    yearly: null,
    features: [
      ["200 conversations a month", true],
      ["Built-in lead dashboard", true],
      ["Priority support", false],
      ["Free customisations", false],
      ["Free backend integration", false],
    ],
    cta: "Start free",
  },
  {
    key: "basic",
    name: "Basic",
    monthly: 4,
    yearly: 3,
    features: [
      ["1,000 conversations a month", true],
      ["Built-in lead dashboard", true],
      ["Priority support", true],
      ["Free customisations", true],
      ["Free backend integration", false],
    ],
    cta: "Choose Basic",
  },
  {
    key: "pro",
    name: "Pro",
    monthly: 12,
    yearly: 10,
    features: [
      ["Unlimited conversations", true],
      ["Built-in lead dashboard", true],
      ["Priority support", true],
      ["Free customisations", true],
      ["Free backend integration", true],
    ],
    cta: "Choose Pro",
    featured: true,
  },
];

export const FREE_CONVERSATIONS = "200";

/** Whole-percent saving of yearly over monthly billing, computed from the prices; null when there is none. */
export function yearlySavingPct(plan: Pick<Plan, "monthly" | "yearly">): number | null {
  if (!plan.yearly || !plan.monthly) return null;
  return Math.round(((plan.monthly - plan.yearly) * 100) / plan.monthly);
}

export const MAX_YEARLY_SAVING_PCT = Math.max(...PLANS.map((p) => yearlySavingPct(p) ?? 0));
export const LOWEST_PAID_MONTHLY = Math.min(...PLANS.filter((p) => p.monthly).map((p) => p.monthly));
