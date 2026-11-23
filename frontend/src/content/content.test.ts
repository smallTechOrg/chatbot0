import { describe, expect, it } from "vitest";
import { INDUSTRIES, findIndustry } from "./industries";
import { LOWEST_PAID_MONTHLY, MAX_YEARLY_SAVING_PCT, PLANS, yearlySavingPct } from "./plans";

describe("plans", () => {
  it("computes yearly savings from the prices", () => {
    const by = Object.fromEntries(PLANS.map((p) => [p.key, p]));
    expect(yearlySavingPct(by.free)).toBeNull();
    expect(yearlySavingPct(by.basic)).toBe(25); // $4 -> $3
    expect(yearlySavingPct(by.pro)).toBe(17); // $12 -> $10
  });

  it("derives the headline numbers", () => {
    expect(MAX_YEARLY_SAVING_PCT).toBe(25);
    expect(LOWEST_PAID_MONTHLY).toBe(4);
  });

  it("features Pro only", () => {
    expect(PLANS.filter((p) => p.featured).map((p) => p.key)).toEqual(["pro"]);
  });
});

describe("findIndustry", () => {
  it.each([
    ["E-Commerce", "e-commerce"],
    ["IT Support", "it-support"],
    ["real estate", "real-estate"],
    ["enterprises", "enterprises"],
    ["it-support", "it-support"],
  ])("finds %s", (value, slug) => {
    expect(findIndustry(value)?.slug).toBe(slug);
  });

  it("drops Small Business and unknown or empty values", () => {
    expect(findIndustry("Small Business")).toBeUndefined();
    expect(findIndustry("")).toBeUndefined();
    expect(findIndustry(null)).toBeUndefined();
  });

  it("lists every industry once, with no small-business wording", () => {
    expect(new Set(INDUSTRIES.map((i) => i.slug)).size).toBe(INDUSTRIES.length);
    expect(JSON.stringify(INDUSTRIES).toLowerCase()).not.toMatch(/small business|small-business|smb/);
  });
});
