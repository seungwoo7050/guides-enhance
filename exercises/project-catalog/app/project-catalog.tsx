"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState
} from "react";
import {
  ContractError,
  parseProjectQuery,
  parseSearchResult,
  toProjectSearchParams
} from "../lib/catalog-contract";
import {
  beginCatalogRequest,
  completeCatalogRequest,
  createCatalogState,
  failCatalogRequest,
  selectCatalogResult
} from "../lib/catalog-model";
import { createRequestCoordinator } from "../lib/request-coordinator";
import type {
  ProjectQuery,
  SearchResult
} from "../lib/project-types";

// [Implementation 8]
// 검색 초안, 확인된 결과, 안내 문구와 요청 생명주기를 `ProjectCatalog`가 함께 관리합니다.
export function ProjectCatalog({
  initialQuery,
  initialResult
}: {
  initialQuery: ProjectQuery;
  initialResult: SearchResult;
}) {
  const [draftQuery, setDraftQuery] = useState(initialQuery.q);
  const [draftStatus, setDraftStatus] = useState(initialQuery.status);
  const [catalog, setCatalog] = useState(() => createCatalogState(initialResult));
  const [announcement, setAnnouncement] = useState(
    `${initialResult.total} projects found.`
  );
  const coordinator = useRef(createRequestCoordinator());

  // [Implementation 8-1]
  // 검색 제출만 history에 기록하고, 뒤로/앞으로 이동에서는 URL을 읽어 최신 검증 응답만 반영합니다.
  const runSearch = useCallback(
    async (query: ProjectQuery, options: { writeHistory: boolean }) => {
      if (options.writeHistory) writeQueryToHistory(query);
      setCatalog((current) => beginCatalogRequest(current));
      setAnnouncement("Updating project results.");
      const request = coordinator.current.begin();

      try {
        const params = toProjectSearchParams(query);
        const response = await fetch(`/api/projects?${params.toString()}`, {
          signal: request.signal,
          headers: { accept: "application/json" }
        });
        if (!response.ok) {
          throw new Error(`Project search failed with status ${response.status}.`);
        }
        const raw: unknown = await response.json();
        const result = parseSearchResult(raw);
        if (!coordinator.current.isCurrent(request.generation)) return;
        setCatalog(completeCatalogRequest(result));
        setAnnouncement(`${result.total} projects found.`);
      } catch (error: unknown) {
        if (isAbortError(error) || !coordinator.current.isCurrent(request.generation)) return;
        const message =
          error instanceof ContractError
            ? "The server response was invalid. Previous results remain visible."
            : "Projects could not be loaded. Inputs and previous results remain unchanged.";
        setCatalog((current) => failCatalogRequest(current, message));
        setAnnouncement(message);
      }
    },
    []
  );

  useEffect(() => {
    function handlePopState() {
      const query = parseProjectQuery(new URLSearchParams(window.location.search));
      setDraftQuery(query.q);
      setDraftStatus(query.status);
      void runSearch(query, { writeHistory: false });
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [runSearch]);

  useEffect(() => () => coordinator.current.cancel(), []);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query: ProjectQuery = {
      q: draftQuery.trim().slice(0, 80),
      status: draftStatus,
      page: 1
    };
    setDraftQuery(query.q);
    setDraftStatus(query.status);
    await runSearch(query, { writeHistory: true });
  }

  const result = selectCatalogResult(catalog);
  const pending = catalog.status === "pending";

  return (
    <main>
      <header className="page-header">
        <p className="eyebrow">Project Catalog</p>
        <h1>Project Catalog</h1>
        <p>
          Share search filters through the URL and keep the latest search response.
        </p>
      </header>

      <form className="search" role="search" onSubmit={search}>
        <label htmlFor="query">Search</label>
        <input
          id="query"
          name="q"
          maxLength={80}
          value={draftQuery}
          onChange={(event) => setDraftQuery(event.target.value)}
        />
        <label htmlFor="status">Status</label>
        <select
          id="status"
          name="status"
          value={draftStatus}
          onChange={(event) =>
            setDraftStatus(event.target.value as ProjectQuery["status"])
          }
        >
          <option value="any">Any</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
        </select>
        <button type="submit">{pending ? "Search again" : "Search"}</button>
      </form>

      <p className="status-message" role="status" aria-live="polite">
        {announcement}
      </p>

      {result.projects.length === 0 ? (
        <p className="empty">No projects match these filters.</p>
      ) : (
        <ul className="projects">
          {result.projects.map((project) => (
            <li key={project.id}>
              <article><h2>{project.title}</h2><p>{project.summary}</p><span>{project.status}</span></article>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function writeQueryToHistory(query: ProjectQuery) {
  const params = toProjectSearchParams(query);
  const search = params.toString();
  const target = search ? `${window.location.pathname}?${search}` : window.location.pathname;
  window.history.pushState(null, "", target);
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

