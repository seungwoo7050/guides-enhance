import { describe, expect, it } from "vitest";
import {
  beginCatalogRequest,
  completeCatalogRequest,
  createCatalogState,
  failCatalogRequest,
  replaceProjectInCatalogState,
  selectCatalogResult
} from "../lib/catalog-model";
import type { Project, SearchResult } from "../lib/project-types";

const project: Project = {
  id: "storage-index",
  title: "Storage Index",
  summary: "Validates page and B+ tree changes.",
  status: "active",
  version: 1
};

const result: SearchResult = {
  projects: [project],
  total: 1,
  page: 1,
  pageSize: 4
};

// [Implementation 14-3]
// 요청 상태 전이와 항목 교체가 마지막 정상 결과를 잃지 않는지 확인합니다.
describe("catalog state machine", () => {
  it("preserves the last verified result through pending and error states", () => {
    const ready = createCatalogState(result);
    const pending = beginCatalogRequest(ready);
    const failed = failCatalogRequest(pending, "failed");

    expect(ready.status).toBe("ready");
    expect(pending.status).toBe("pending");
    expect(failed.status).toBe("error");
    expect(selectCatalogResult(failed)).toEqual(result);
  });

  it("distinguishes empty and ready successful results", () => {
    expect(completeCatalogRequest({ ...result, projects: [], total: 0 }).status).toBe("empty");
    expect(completeCatalogRequest(result).status).toBe("ready");
  });

  it("replaces one project without changing the current request state", () => {
    const updated = { ...project, title: "Updated title", version: 2 };
    const pending = beginCatalogRequest(createCatalogState(result));
    const next = replaceProjectInCatalogState(pending, updated);

    expect(next.status).toBe("pending");
    expect(selectCatalogResult(next).projects[0]).toEqual(updated);
  });
});
