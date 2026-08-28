import { defineConfig } from "vitest/config";

// [Implementation 14]
// Vitest가 브라우저 E2E 파일과 생성 디렉터리를 단위 테스트 대상에서 제외하도록 설정합니다.
export default defineConfig({
  test: {
    environment: "node",
    exclude: ["tests/e2e/**", "node_modules/**", ".next/**"]
  }
});
