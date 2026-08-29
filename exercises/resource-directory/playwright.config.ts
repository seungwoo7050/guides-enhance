import { defineConfig } from "@playwright/test";

const configuredPort = Number(process.env.RESOURCE_DIRECTORY_E2E_PORT);
const port = Number.isSafeInteger(configuredPort) && configuredPort > 0 ? configuredPort : 4321;
const baseURL = `http://127.0.0.1:${port}`;

// [Implementation 13]
// E2E runs against the built static site through Astro preview, never against the dev server.
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
    command: `npm run preview -- --host 127.0.0.1 --port ${port}`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 60_000
  }
});
