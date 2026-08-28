import { parseProjectQuery } from "../../../lib/catalog-contract";
import { searchProjects } from "../../../lib/projects";

// [Implementation 10]
// 검색 쿼리를 검사한 결과를 캐시하지 않는 JSON 응답으로 반환합니다.
export async function GET(request: Request) {
  const query = parseProjectQuery(new URL(request.url).searchParams);
  return Response.json(searchProjects(query), {
    headers: { "cache-control": "no-store" }
  });
}
