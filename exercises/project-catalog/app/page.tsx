import React from "react";
import { ProjectCatalog } from "./project-catalog";
import {
  parseProjectQuery,
  toURLSearchParams
} from "../lib/catalog-contract";
import { searchProjects } from "../lib/projects";

// [Implementation 6]
// URL 쿼리를 한 번만 읽어 첫 검색 조건과 결과가 서로 어긋나지 않게 합니다.
export default async function Page({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const query = parseProjectQuery(toURLSearchParams(raw));
  const initialResult = searchProjects(query);

  return <ProjectCatalog initialQuery={query} initialResult={initialResult} />;
}
