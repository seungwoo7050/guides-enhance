import { updateProject } from "../../../../lib/projects";

// [Implementation 10-1]
// 제목과 `version`을 검사하고 성공, 입력 오류, 없음과 충돌을 HTTP 상태 코드로 구분합니다.
export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const body: unknown = await request.json().catch(() => null);
  if (!isRenameRequest(body)) {
    return Response.json(
      { code: "invalid_request", message: "Check the title and version." },
      { status: 400 }
    );
  }

  const result = updateProject(id, body.title.trim(), body.version);
  if (result.kind === "not_found") {
    return Response.json(
      { code: "not_found", message: "Project not found." },
      { status: 404 }
    );
  }
  if (result.kind === "conflict") {
    return Response.json(
      {
        code: "version_conflict",
        message: "Another change was saved first.",
        project: result.project
      },
      { status: 409 }
    );
  }
  return Response.json({ project: result.project });
}

function isRenameRequest(value: unknown): value is { title: string; version: number } {
  return (
    typeof value === "object" &&
    value !== null &&
    "title" in value &&
    "version" in value &&
    typeof value.title === "string" &&
    value.title.trim().length > 0 &&
    value.title.trim().length <= 80 &&
    typeof value.version === "number" &&
    Number.isSafeInteger(value.version) &&
    value.version >= 0
  );
}
