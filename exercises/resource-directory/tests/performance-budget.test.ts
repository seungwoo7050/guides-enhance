import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const budget = JSON.parse(
  readFileSync(join(process.cwd(), "performance-budget.json"), "utf8")
) as Record<string, unknown>;

// [Implementation 12-3]
// A fixed schema prevents silent removal or accidental expansion of the browser budget.
describe("performance budget", () => {
  it("contains only measurable positive limits", () => {
    expect(Object.keys(budget).sort()).toEqual([
      "maximumDetailDomNodes",
      "maximumDetailJavaScriptBytes",
      "maximumHydratedIslands"
    ]);
    for (const value of Object.values(budget)) {
      expect(typeof value).toBe("number");
      expect(value).toBeGreaterThan(0);
    }
  });
});
