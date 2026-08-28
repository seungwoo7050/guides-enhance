import type { Project, ProjectQuery, SearchResult } from "./project-types";

const PAGE_SIZE = 4;

// [Implementation 2]
// 서버 프로세스가 프로젝트와 `version`을 보관하며, 호출자에게는 복사본만 돌려줍니다.
const initialProjects: Project[] = [
  {
    id: "network-inspector",
    title: "Network Flow Inspector",
    summary: "Tracks packets and connection state together.",
    status: "active",
    version: 1
  },
  {
    id: "storage-index",
    title: "Storage Index",
    summary: "Validates page and B+ tree changes.",
    status: "active",
    version: 1
  },
  {
    id: "release-monitor",
    title: "Release Monitor",
    summary: "Records deployment outcomes and recovery conditions.",
    status: "paused",
    version: 1
  },
  {
    id: "task-runner",
    title: "Command Runner",
    summary: "Manages execution timeouts and result reports.",
    status: "active",
    version: 1
  },
  {
    id: "event-recovery",
    title: "Event Recovery",
    summary: "Converges duplicate and out-of-order events.",
    status: "paused",
    version: 1
  }
];

declare global {
  var __projectCatalogStore: Map<string, Project> | undefined;
}

const projects =
  globalThis.__projectCatalogStore ??
  (globalThis.__projectCatalogStore = createInitialStore());

// [Implementation 2-1]
// `q`, `status`, `page`를 적용해 현재 페이지의 결과와 전체 개수를 계산합니다.
export function searchProjects(query: ProjectQuery): SearchResult {
  const normalized = query.q.toLocaleLowerCase("en-US");
  const matches = [...projects.values()].filter((project) => {
    const textMatches =
      normalized.length === 0 ||
      `${project.title} ${project.summary}`.toLocaleLowerCase("en-US").includes(normalized);
    const statusMatches = query.status === "any" || project.status === query.status;
    return textMatches && statusMatches;
  });
  const start = (query.page - 1) * PAGE_SIZE;
  return {
    projects: matches.slice(start, start + PAGE_SIZE).map(cloneProject),
    total: matches.length,
    page: query.page,
    pageSize: PAGE_SIZE
  };
}

// [Implementation 2-2]
// 요청의 `version`이 현재 값과 같을 때만 제목과 `version`을 함께 갱신합니다.
export function updateProject(id: string, title: string, version: number) {
  const current = projects.get(id);
  if (!current) return { kind: "not_found" as const };
  if (current.version !== version) {
    return { kind: "conflict" as const, project: cloneProject(current) };
  }

  const next: Project = {
    ...current,
    title,
    version: current.version + 1
  };
  projects.set(id, next);
  return { kind: "updated" as const, project: cloneProject(next) };
}

// [Implementation 2-3]
// 각 테스트가 같은 초기 데이터에서 시작하도록 프로세스 내 저장소를 되돌립니다.
export function restoreProjects() {
  projects.clear();
  for (const project of initialProjects) projects.set(project.id, cloneProject(project));
}

function createInitialStore() {
  return new Map(initialProjects.map((project) => [project.id, cloneProject(project)]));
}

function cloneProject(project: Project): Project {
  return { ...project };
}
