import { describe, expect, it } from "vitest";
import {
  countResourcesByCategory,
  isResourceCategory,
  selectRelatedResources,
  sortResourceRecords,
  toResourceSummary,
  type ResourceRecord
} from "../src/lib/resource-model";

const records: ResourceRecord[] = [
  {
    id: "old-featured",
    title: "오래된 추천 자료",
    summary: "추천 자료",
    category: "web",
    tags: ["HTTP"],
    publishedAt: new Date("2026-01-01T00:00:00Z"),
    featured: true
  },
  {
    id: "new-data",
    title: "새 데이터 자료",
    summary: "데이터 자료",
    category: "data",
    tags: ["CSV"],
    publishedAt: new Date("2026-06-01T00:00:00Z"),
    featured: false
  },
  {
    id: "updated-web",
    title: "수정된 웹 자료",
    summary: "웹 자료",
    category: "web",
    tags: ["Storage"],
    publishedAt: new Date("2026-02-01T00:00:00Z"),
    updatedAt: new Date("2026-07-01T00:00:00Z"),
    featured: false
  }
];
const oldFeatured = records[0];
const updatedWeb = records[2];
if (!oldFeatured || !updatedWeb) throw new Error("resource test fixtures are incomplete");

// [Implementation 12-1]
// These tests catch ordering or serialization changes that would make routes and JSON disagree.
describe("resource model", () => {
  it("accepts only the configured category ids", () => {
    expect(isResourceCategory("web")).toBe(true);
    expect(isResourceCategory("security")).toBe(false);
  });

  it("orders featured content before the latest effective date", () => {
    expect(sortResourceRecords(records).map(({ id }) => id)).toEqual([
      "old-featured",
      "updated-web",
      "new-data"
    ]);
  });

  it("serializes dates and copies tag arrays", () => {
    const summary = toResourceSummary(updatedWeb);
    expect(summary.updatedAt).toBe("2026-07-01T00:00:00.000Z");
    expect(summary.categoryLabel).toBe("웹");
    summary.tags.push("changed");
    expect(updatedWeb.tags).toEqual(["Storage"]);
  });

  it("counts categories and selects related entries without the current entry", () => {
    expect(countResourcesByCategory(records)).toEqual({ web: 2, data: 1, tooling: 0 });
    expect(selectRelatedResources(records, oldFeatured).map(({ id }) => id)).toEqual([
      "updated-web"
    ]);
  });
});
