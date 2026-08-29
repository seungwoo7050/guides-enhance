import { describe, expect, it } from "vitest";
import { buildCanonicalUrl, buildPageTitle } from "../src/lib/seo";

// [Implementation 12-2]
// Metadata helpers are tested directly so canonical mistakes fail before browser verification.
describe("SEO helpers", () => {
  it("uses the site name alone for the home page", () => {
    expect(buildPageTitle()).toBe("Resource Directory");
  });

  it("adds the site name to detail titles", () => {
    expect(buildPageTitle("HTTP 상태 코드")).toBe("HTTP 상태 코드 | Resource Directory");
  });

  it("normalizes relative canonical paths", () => {
    const canonical = buildCanonicalUrl(
      "resources/test/",
      new URL("https://resource-directory.example")
    );
    expect(canonical.toString()).toBe(
      "https://resource-directory.example/resources/test/"
    );
  });

  it("rejects canonical generation when the site origin is missing", () => {
    expect(() => buildCanonicalUrl("/resources/", undefined)).toThrow(/site/);
  });
});
