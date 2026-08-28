import type { Project, ProjectQuery, ProjectStatus, SearchResult } from "./project-types";

// [Implementation 3]
// 외부 입력 형식 오류를 모두 `ContractError`로 바꿔 호출부가 한 방식으로 처리하게 합니다.
export class ContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ContractError";
  }
}

// [Implementation 3-1]
// URL 쿼리를 허용 범위로 정규화하며, 다시 직렬화해도 같은 값이 나오게 합니다.
export function toURLSearchParams(
  raw: Record<string, string | string[] | undefined>
): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === "string") params.set(key, value);
  }
  return params;
}

export function parseProjectQuery(params: URLSearchParams): ProjectQuery {
  const q = (params.get("q") ?? "").trim().slice(0, 80);
  const rawStatus = params.get("status");
  const status: ProjectQuery["status"] = isProjectStatus(rawStatus) ? rawStatus : "any";
  const rawPage = Number(params.get("page") ?? "1");
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  return { q, status, page };
}

export function toProjectSearchParams(query: ProjectQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q.length > 0) params.set("q", query.q);
  if (query.status !== "any") params.set("status", query.status);
  if (query.page !== 1) params.set("page", String(query.page));
  return params;
}

// [Implementation 3-2]
// `unknown` JSON의 필드, 숫자 범위와 중복 id를 확인한 뒤 내부 타입으로 바꿉니다.
export function parseProject(value: unknown): Project {
  if (!isRecord(value)) throw new ContractError("Project must be an object.");

  const id = parseNonEmptyString(value.id, "project.id", 120);
  const title = parseNonEmptyString(value.title, "project.title", 80);
  const summary = parseString(value.summary, "project.summary", 500);
  if (!isProjectStatus(value.status)) {
    throw new ContractError("project.status is not supported.");
  }
  const version = parseNonNegativeInteger(value.version, "project.version");

  return { id, title, summary, status: value.status, version };
}

export function parseSearchResult(value: unknown): SearchResult {
  if (!isRecord(value)) throw new ContractError("Search response must be an object.");
  if (!Array.isArray(value.projects)) {
    throw new ContractError("search.projects must be an array.");
  }

  const projects = value.projects.map(parseProject);
  const uniqueIds = new Set(projects.map((project) => project.id));
  if (uniqueIds.size !== projects.length) {
    throw new ContractError("Search response contains duplicate project identifiers.");
  }

  const total = parseNonNegativeInteger(value.total, "search.total");
  const page = parsePositiveInteger(value.page, "search.page");
  const pageSize = parsePositiveInteger(value.pageSize, "search.pageSize");
  if (total < projects.length) {
    throw new ContractError("search.total is smaller than the returned project count.");
  }

  return { projects, total, page, pageSize };
}

export function parseProjectEnvelope(value: unknown): { project: Project } {
  if (!isRecord(value) || !("project" in value)) {
    throw new ContractError("Project response envelope is invalid.");
  }
  return { project: parseProject(value.project) };
}

function isProjectStatus(value: unknown): value is ProjectStatus {
  return value === "active" || value === "paused";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseString(value: unknown, name: string, maximumLength: number): string {
  if (typeof value !== "string" || value.length > maximumLength) {
    throw new ContractError(`${name} is outside its string bounds.`);
  }
  return value;
}

function parseNonEmptyString(value: unknown, name: string, maximumLength: number): string {
  const parsed = parseString(value, name, maximumLength);
  if (parsed.trim().length === 0) throw new ContractError(`${name} must not be empty.`);
  return parsed;
}

function parseNonNegativeInteger(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    throw new ContractError(`${name} must be a non-negative safe integer.`);
  }
  return value;
}

function parsePositiveInteger(value: unknown, name: string): number {
  const parsed = parseNonNegativeInteger(value, name);
  if (parsed === 0) throw new ContractError(`${name} must be positive.`);
  return parsed;
}
