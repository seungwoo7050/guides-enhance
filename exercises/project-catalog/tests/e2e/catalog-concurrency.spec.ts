import { expect, test } from "@playwright/test";

const resetToken = process.env.CATALOG_TEST_RESET_TOKEN;

test.beforeEach(async ({ request }) => {
  expect(resetToken, "Playwright reset token must be configured.").toBeTruthy();
  const response = await request.post("/api/test/reset", {
    headers: { "x-catalog-test-token": resetToken ?? "" }
  });
  expect(response.status()).toBe(200);
});

// [Implementation 15-2]
// URL 복원, 늦은 응답 차단, 잘못된 응답 거절, 저장 실패와 `409` 복구를 브라우저에서 확인합니다.
test("restores search state through URLs, reloads, and browser history", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Search").fill("Storage");
  await page.getByRole("button", { name: "Search", exact: true }).click();

  await expect(page).toHaveURL(/q=Storage/);
  await expect(page.getByRole("heading", { name: "Storage Index" })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Search")).toHaveValue("Storage");

  await page.getByLabel("Search").fill("Network");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Network Flow Inspector" })).toBeVisible();
  await page.goBack();

  await expect(page.getByLabel("Search")).toHaveValue("Storage");
  await expect(page.getByRole("heading", { name: "Storage Index" })).toBeVisible();
});

test("prevents a late response from replacing the latest result even when abort is ignored", async ({
  page
}) => {
  await page.goto("/");
  await page.evaluate(() => {
    const nativeFetch = window.fetch.bind(window);
    let releaseOld: (() => void) | undefined;
    let oldSignal: AbortSignal | undefined;
    let oldStarted = false;

    const project = (id: string, title: string) => ({
      id,
      title,
      summary: `${title} summary`,
      status: "active" as const,
      version: 1
    });
    const response = (value: unknown) =>
      new Response(JSON.stringify(value), {
        status: 200,
        headers: { "content-type": "application/json" }
      });

    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(
        typeof input === "string" || input instanceof URL ? input.toString() : input.url,
        window.location.href
      );
      if (url.pathname === "/api/projects" && url.searchParams.get("q") === "Network") {
        oldStarted = true;
        oldSignal = init?.signal ?? undefined;
        return new Promise<Response>((resolve) => {
          releaseOld = () =>
            resolve(
              response({
                projects: [project("network-inspector", "Network Flow Inspector")],
                total: 1,
                page: 1,
                pageSize: 4
              })
            );
        });
      }
      if (url.pathname === "/api/projects" && url.searchParams.get("q") === "Storage") {
        return Promise.resolve(
          response({
            projects: [project("storage-index", "Storage Index")],
            total: 1,
            page: 1,
            pageSize: 4
          })
        );
      }
      return nativeFetch(input, init);
    };

    Object.assign(window, {
      __catalogOldStarted: () => oldStarted,
      __catalogOldSignalAborted: () => Boolean(oldSignal?.aborted),
      __catalogReleaseOld: () => releaseOld?.()
    });
  });

  await page.getByLabel("Search").fill("Network");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect
    .poll(() =>
      page.evaluate(() =>
        (window as typeof window & { __catalogOldStarted(): boolean }).__catalogOldStarted()
      )
    )
    .toBe(true);

  await page.getByLabel("Search").fill("Storage");
  await page.getByLabel("Search").press("Enter");
  await expect(page.getByRole("heading", { name: "Storage Index" })).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() =>
        (
          window as typeof window & { __catalogOldSignalAborted(): boolean }
        ).__catalogOldSignalAborted()
      )
    )
    .toBe(true);

  await page.evaluate(() =>
    (window as typeof window & { __catalogReleaseOld(): void }).__catalogReleaseOld()
  );
  await expect(page.getByRole("heading", { name: "Network Flow Inspector" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Storage Index" })).toBeVisible();
});

test("rejects malformed success responses and preserves the previous result", async ({ page }) => {
  await page.goto("/");
  await page.route("**/api/projects?*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ projects: "not-an-array", total: 1, page: 1, pageSize: 4 })
    });
  });

  await page.getByLabel("Search").fill("malformed");
  await page.getByRole("button", { name: "Search", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("server response was invalid");
  await expect(page.getByRole("heading", { name: "Network Flow Inspector" })).toBeVisible();
});

test("preserves the latest server value and local draft after a version conflict", async ({ page }) => {
  await page.goto("/");
  const editButton = page
    .getByRole("article", { name: "Network Flow Inspector project" })
    .getByRole("button", { name: "Edit title" });
  await editButton.click();
  const input = page.getByLabel("Project title");
  await input.fill("Local draft title");

  const external = await page.request.patch("/api/projects/network-inspector", {
    data: { title: "Server-side title", version: 1 }
  });
  expect(external.status()).toBe(200);
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("latest server title");
  await expect(page.getByRole("heading", { name: "Server-side title" })).toBeVisible();
  await expect(input).toHaveValue("Local draft title");
  await expect(input).toBeFocused();
});

test("rolls back the optimistic value while preserving the draft after a general failure", async ({
  page
}) => {
  await page.goto("/");
  await page.route("**/api/projects/network-inspector", async (route) => {
    if (route.request().method() === "PATCH") {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ code: "unavailable" })
      });
    } else {
      await route.continue();
    }
  });

  const article = page.getByRole("article", { name: "Network Flow Inspector project" });
  await article.getByRole("button", { name: "Edit title" }).click();
  const input = page.getByLabel("Project title");
  await input.fill("Draft that survives failure");
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("previous server value was restored");
  await expect(page.getByRole("heading", { name: "Network Flow Inspector" })).toBeVisible();
  await expect(input).toHaveValue("Draft that survives failure");
  await expect(input).toBeFocused();
});
