import { beforeEach, describe, expect, it } from "vitest";
import { GET as searchRoute } from "../app/api/projects/route";
import { PATCH as updateRoute } from "../app/api/projects/[id]/route";
import { restoreProjects, searchProjects, updateProject } from "../lib/projects";

// [Implementation 14-5]
// 저장소와 Route Handler가 검색, `version` 충돌과 HTTP 상태 코드를 같은 규칙으로 처리하는지 확인합니다.
describe("project store and HTTP routes", () => {
  beforeEach(restoreProjects);

  it("applies text, status, and page filters together", () => {
    expect(searchProjects({ q: "Storage", status: "active", page: 1 }).projects).toMatchObject([
      { id: "storage-index" }
    ]);
    expect(searchProjects({ q: "", status: "paused", page: 1 }).total).toBe(2);
  });

  it("updates only the current version and returns the latest value on conflict", () => {
    expect(updateProject("network-inspector", "Updated title", 1)).toMatchObject({
      kind: "updated",
      project: { title: "Updated title", version: 2 }
    });
    expect(updateProject("network-inspector", "Late title", 1)).toMatchObject({
      kind: "conflict",
      project: { title: "Updated title", version: 2 }
    });
  });

  it("returns normalized search results from the collection route", async () => {
    const response = await searchRoute(
      new Request("http://localhost/api/projects?q=Storage&status=active&page=1")
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toContain("no-store");
    await expect(response.json()).resolves.toMatchObject({
      projects: [{ id: "storage-index" }],
      total: 1,
      page: 1
    });
  });

  it("distinguishes invalid input, success, conflict, and missing projects", async () => {
    const invalid = await updateRoute(
      requestBody({ title: "", version: 1 }),
      context("network-inspector")
    );
    expect(invalid.status).toBe(400);

    const updated = await updateRoute(
      requestBody({ title: "Updated title", version: 1 }),
      context("network-inspector")
    );
    expect(updated.status).toBe(200);

    const conflict = await updateRoute(
      requestBody({ title: "Late title", version: 1 }),
      context("network-inspector")
    );
    expect(conflict.status).toBe(409);
    await expect(conflict.json()).resolves.toMatchObject({
      code: "version_conflict",
      project: { title: "Updated title", version: 2 }
    });

    const missing = await updateRoute(
      requestBody({ title: "Missing", version: 1 }),
      context("missing")
    );
    expect(missing.status).toBe(404);
  });
});

function requestBody(body: unknown) {
  return new Request("http://localhost/api/projects/id", {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
}

function context(id: string) {
  return { params: Promise.resolve({ id }) };
}
