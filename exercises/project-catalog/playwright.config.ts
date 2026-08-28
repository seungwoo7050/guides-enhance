import { defineConfig } from "@playwright/test";
import { randomUUID } from "node:crypto";

// [Implementation 15]
// Playwright가 매 실행마다 고유 포트에서 운영 서버를 시작하고 실패 자료를 남기도록 설정합니다.
const envPort = Number(process.env.CATALOG_E2E_PORT);
const defaultPort = 30_000;
const port = Number.isSafeInteger(envPort) && envPort > 0 ? envPort : defaultPort;
const baseURL = `http://127.0.0.1:${port}`;
const resetToken = process.env.CATALOG_TEST_RESET_TOKEN?.trim() || randomUUID();
process.env.CATALOG_TEST_RESET_TOKEN = resetToken;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  },
  webServer: {
    command: `npm run start -- --hostname 127.0.0.1 --port ${port}`,
    url: `${baseURL}/api/health`,
    env: {
      PLAYWRIGHT: "1",
      CATALOG_TEST_RESET_TOKEN: resetToken,
      APP_RELEASE: "playwright-e2e"
    },
    reuseExistingServer: false,
    timeout: 60_000
  }
});
