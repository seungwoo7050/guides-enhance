import type { Project, SearchResult } from "./project-types";

// [Implementation 4]
// `ready`, `empty`, `pending`, `error`만 허용하며, 요청 중이거나 실패해도 마지막 정상 결과를 보존합니다.
export type CatalogState =
  | { status: "ready"; result: SearchResult }
  | { status: "empty"; result: SearchResult }
  | { status: "pending"; previous: SearchResult }
  | { status: "error"; message: string; previous: SearchResult };

export function createCatalogState(result: SearchResult): CatalogState {
  return result.projects.length === 0
    ? { status: "empty", result }
    : { status: "ready", result };
}

export function beginCatalogRequest(state: CatalogState): CatalogState {
  return { status: "pending", previous: selectCatalogResult(state) };
}

export function completeCatalogRequest(result: SearchResult): CatalogState {
  return createCatalogState(result);
}

export function failCatalogRequest(state: CatalogState, message: string): CatalogState {
  return { status: "error", message, previous: selectCatalogResult(state) };
}

export function selectCatalogResult(state: CatalogState): SearchResult {
  return state.status === "ready" || state.status === "empty"
    ? state.result
    : state.previous;
}

export function replaceProjectInResult(result: SearchResult, project: Project): SearchResult {
  return {
    ...result,
    projects: result.projects.map((candidate) =>
      candidate.id === project.id ? project : candidate
    )
  };
}

export function replaceProjectInCatalogState(
  state: CatalogState,
  project: Project
): CatalogState {
  if (state.status === "ready" || state.status === "empty") {
    return {
      ...state,
      result: replaceProjectInResult(state.result, project)
    };
  }
  return {
    ...state,
    previous: replaceProjectInResult(state.previous, project)
  };
}
