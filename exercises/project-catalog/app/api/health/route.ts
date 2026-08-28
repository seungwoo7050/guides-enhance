// [Implementation 12]
// 현재 릴리스와 `status`만 담은 캐시 금지 응답을 제공합니다.
// [Implementation 12-1]
// Route Handler를 추가한 뒤 `next typegen`으로 라우트 타입을 만들고 `tsc`로 검사합니다.
export async function GET() {
  return Response.json(
    {
      status: "ok",
      release: process.env.APP_RELEASE ?? "local"
    },
    {
      headers: {
        "cache-control": "no-store"
      }
    }
  );
}
