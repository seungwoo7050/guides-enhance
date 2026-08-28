// [Implementation 1]
// Route Handler와 Server/Client Component가 함께 주고받을 수 있도록 직렬화 가능한 타입만 정의합니다.
export type ProjectStatus = "active" | "paused";

export type Project = {
  id: string;
  title: string;
  summary: string;
  status: ProjectStatus;
  version: number;
};

export type ProjectQuery = {
  q: string;
  status: "any" | ProjectStatus;
  page: number;
};

export type SearchResult = {
  projects: Project[];
  total: number;
  page: number;
  pageSize: number;
};

export type RenameProjectCommand = {
  id: string;
  title: string;
  version: number;
};

export type RenameOutcome =
  | { kind: "success"; project: Project }
  | { kind: "conflict"; project: Project; message: string }
  | { kind: "error"; message: string };
