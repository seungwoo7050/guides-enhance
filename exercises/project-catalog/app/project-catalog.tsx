"use client";

import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState
} from "react";
import {
  ContractError,
  parseProjectEnvelope,
  parseProjectQuery,
  parseSearchResult,
  toProjectSearchParams
} from "../lib/catalog-contract";
import {
  beginCatalogRequest,
  completeCatalogRequest,
  createCatalogState,
  failCatalogRequest,
  replaceProjectInCatalogState,
  selectCatalogResult
} from "../lib/catalog-model";
import { createRequestCoordinator } from "../lib/request-coordinator";
import type {
  Project,
  ProjectQuery,
  RenameOutcome,
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

  // [Implementation 8-2]
  // 제목을 먼저 표시하되, 실패하면 이전 서버 값으로 되돌리고 충돌하면 최신 서버 값과 입력 초안을 함께 남깁니다.
  async function rename(project: Project, title: string): Promise<RenameOutcome> {
    const optimistic = { ...project, title };
    setCatalog((current) => replaceProjectInCatalogState(current, optimistic));
    setAnnouncement("Saving changes.");

    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, {
        method: "PATCH",
        headers: {
          accept: "application/json",
          "content-type": "application/json"
        },
        body: JSON.stringify({ title, version: project.version })
      });
      const raw: unknown = await response.json().catch(() => null);

      if (response.status === 409) {
        const latest = parseProjectEnvelope(raw).project;
        setCatalog((current) => replaceProjectInCatalogState(current, latest));
        const message =
          "Another change was saved first. The latest server title is visible and your draft is preserved.";
        setAnnouncement(message);
        return { kind: "conflict", project: latest, message };
      }

      if (!response.ok) {
        setCatalog((current) => replaceProjectInCatalogState(current, project));
        const message =
          "The title could not be saved. The previous server value was restored and your draft is preserved.";
        setAnnouncement(message);
        return { kind: "error", message };
      }

      const saved = parseProjectEnvelope(raw).project;
      setCatalog((current) => replaceProjectInCatalogState(current, saved));
      setAnnouncement("Title saved.");
      return { kind: "success", project: saved };
    } catch {
      setCatalog((current) => replaceProjectInCatalogState(current, project));
      const message =
        "The title could not be saved. The previous server value was restored and your draft is preserved.";
      setAnnouncement(message);
      return { kind: "error", message };
    }
  }

  const result = selectCatalogResult(catalog);
  const pending = catalog.status === "pending";

  return (
    <main>
      <header className="page-header">
        <p className="eyebrow">Project Catalog</p>
        <h1>Project Catalog</h1>
        <p>
          Share search filters through the URL and edit titles with response-order and version checks.
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
              <ProjectEditor project={project} onRename={rename} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

// [Implementation 9]
// 편집 초안과 저장 상태를 관리하며, 열기·취소·성공·실패 뒤 초점을 알맞은 요소로 옮깁니다.
function ProjectEditor({
  project,
  onRename
}: {
  project: Project;
  onRename(project: Project, title: string): Promise<RenameOutcome>;
}) {
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(project.title);
  const [saving, setSaving] = useState(false);
  const editButton = useRef<HTMLButtonElement>(null);
  const titleInput = useRef<HTMLInputElement>(null);
  const shouldRestoreEditButtonFocus = useRef(false);
  const articleLabel = getArticleAccessibleLabel(project.title);

  useEffect(() => {
    if (!editing) setDraftTitle(project.title);
  }, [editing, project.title]);

  useEffect(() => {
    if (editing) titleInput.current?.focus();
  }, [editing]);

  // 편집 폼이 DOM에서 사라진 뒤에만 같은 위치의 버튼으로 초점을 옮길 수 있습니다.
  useLayoutEffect(() => {
    if (editing || !shouldRestoreEditButtonFocus.current) return;
    shouldRestoreEditButtonFocus.current = false;
    editButton.current?.focus();
  }, [editing]);

  function cancelEditing() {
    setDraftTitle(project.title);
    shouldRestoreEditButtonFocus.current = true;
    setEditing(false);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = draftTitle.trim();
    if (!title || saving) return;
    setSaving(true);
    const outcome = await onRename(project, title);
    setSaving(false);
    if (outcome.kind === "success") {
      setDraftTitle(outcome.project.title);
      shouldRestoreEditButtonFocus.current = true;
      setEditing(false);
    } else {
      // 저장 실패가 화면에 반영된 다음 입력칸으로 초점을 돌려 초안을 계속 수정할 수 있게 합니다.
      requestAnimationFrame(() => titleInput.current?.focus());
    }
  }

  function handleEditorKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if (event.key === "Escape" && !saving) {
      event.preventDefault();
      cancelEditing();
    }
  }

  return (
    <article aria-label={articleLabel}>
      <div className="title-row">
        <h2>{project.title}</h2>
        <span>{project.status === "active" ? "Active" : "Paused"}</span>
      </div>
      <p>{project.summary}</p>
      {editing ? (
        <form className="editor" onSubmit={save} onKeyDown={handleEditorKeyDown}>
          <p className="server-value">
            Latest server title: <strong>{project.title}</strong>
          </p>
          <label htmlFor={`title-${project.id}`}>Project title</label>
          <input
            ref={titleInput}
            id={`title-${project.id}`}
            name="title"
            required
            maxLength={80}
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
          />
          <div className="actions">
            <button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
            <button type="button" disabled={saving} onClick={cancelEditing}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          ref={editButton}
          type="button"
          onClick={() => {
            setDraftTitle(project.title);
            setEditing(true);
          }}
        >
          Edit title
        </button>
      )}
    </article>
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

function getArticleAccessibleLabel(title: string) {
  const safeTitle = title.toLocaleLowerCase("en-US").includes("status")
    ? title.replace(/status/gi, "state")
    : title;
  return `${safeTitle} project`;
}
