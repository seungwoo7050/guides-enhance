import { describe, expect, it } from "vitest";
import Page from "../app/page";
import {
  parseProjectQuery,
  toProjectSearchParams,
  toURLSearchParams
} from "../lib/catalog-contract";

// [Implementation 14-1]
// 잘못된 쿼리를 정규화하고 서버 첫 화면의 조건과 결과가 같은 입력을 쓰는지 확인합니다.
describe("URL query and server bootstrap", () => {
  it("normalizes unsafe query values and preserves canonical round trips", () => {
    const query = parseProjectQuery(
      new URLSearchParams({ q: `  ${"a".repeat(90)}  `, status: "deleted", page: "-4" })
    );

    expect(query).toEqual({ q: "a".repeat(80), status: "any", page: 1 });
    expect(parseProjectQuery(toProjectSearchParams(query))).toEqual(query);
  });

  it("ignores array-valued server query inputs", () => {
    const params = toURLSearchParams({
      q: ["first", "second"],
      status: "active",
      page: "2"
    });

    expect(params.get("q")).toBeNull();
    expect(params.get("status")).toBe("active");
    expect(params.get("page")).toBe("2");
  });

  it("derives the initial client props from one server-side URL snapshot", async () => {
    const element = await Page({
      searchParams: Promise.resolve({ q: "Storage", status: "active", page: "1" })
    });

    expect(element.props.initialQuery).toEqual({ q: "Storage", status: "active", page: 1 });
    expect(
      element.props.initialResult.projects.map((project: { id: string }) => project.id)
    ).toEqual(["storage-index"]);
  });
});
