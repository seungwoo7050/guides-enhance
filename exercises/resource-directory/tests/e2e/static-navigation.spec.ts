import { expect, test } from "@playwright/test";

// [Implementation 13-2]
// Browser tests verify generated routes and endpoint output instead of Astro component internals.
test("static routes, metadata and JSON output agree", async ({ page, request }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Resource Directory");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("기술 자료");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "https://resource-directory.example/"
  );

  await page.getByRole("link", { name: "전체 자료 보기" }).click();
  await expect(page).toHaveURL(/\/resources\/$/);
  await expect(page.getByRole("article")).toHaveCount(6);

  await page.getByRole("link", { name: "HTTP 상태 코드 빠른 참조" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("HTTP 상태 코드 빠른 참조");
  await expect(page.getByRole("heading", { name: "실패 종류를 먼저 나눕니다" })).toBeVisible();

  const response = await request.get("/resources.json");
  expect(response.status()).toBe(200);
  const body = (await response.json()) as Array<Record<string, unknown>>;
  expect(body).toHaveLength(6);
  expect(body[0]).toHaveProperty("id");
  expect(body[0]).not.toHaveProperty("body");
});

test("category pages contain only their configured entries", async ({ page }) => {
  await page.goto("/categories/data/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("데이터 자료");
  await expect(page.getByRole("article")).toHaveCount(2);
  await expect(page.getByRole("link", { name: "CSV 방언 확인표" })).toBeVisible();
  await expect(page.getByRole("link", { name: "HTTP 상태 코드 빠른 참조" })).toHaveCount(0);
});
