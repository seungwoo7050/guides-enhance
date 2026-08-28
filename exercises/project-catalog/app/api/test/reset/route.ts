import { restoreProjects } from "../../../../lib/projects";

// [Implementation 11]
// 테스트 모드와 토큰이 모두 맞을 때만 데이터를 초기화하며, 나머지는 `404`로 숨깁니다.
export async function POST(request: Request) {
  const testMode = process.env.NODE_ENV === "test" || process.env.PLAYWRIGHT === "1";
  const expectedToken = process.env.CATALOG_TEST_RESET_TOKEN;
  const suppliedToken = request.headers.get("x-catalog-test-token");

  if (!testMode || !expectedToken || suppliedToken !== expectedToken) {
    return Response.json({ code: "not_found" }, { status: 404 });
  }

  restoreProjects();
  return Response.json({ ok: true }, { headers: { "cache-control": "no-store" } });
}
