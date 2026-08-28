import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const resetToken = process.env.CATALOG_TEST_RESET_TOKEN;
const budget = JSON.parse(
  readFileSync(join(process.cwd(), "performance-budget.json"), "utf8")
) as {
  maximumInitialJavaScriptBytes: number;
  maximumDomNodes: number;
};

test.beforeEach(async ({ request }) => {
  expect(resetToken, "Playwright reset token must be configured.").toBeTruthy();
  const response = await request.post("/api/test/reset", {
    headers: { "x-catalog-test-token": resetToken ?? "" }
  });
  expect(response.status()).toBe(200);
});

// [Implementation 15-3]
// 키보드 초점, 의미 있는 HTML, 애니메이션 감소, 좁은 화면과 JavaScript·DOM 예산을 브라우저에서 확인합니다.
test("restores focus after keyboard cancellation and repeated saves", async ({ page }) => {
  await page.goto("/");
  const article = page.getByRole("article", { name: "Network Flow Inspector project" });
  const editButton = article.getByRole("button", { name: "Edit title" });

  await editButton.focus();
  await page.keyboard.press("Enter");
  const input = page.getByLabel("Project title");
  await expect(input).toBeFocused();
  await input.fill("Draft to cancel");
  await page.keyboard.press("Escape");
  await expect(editButton).toBeFocused();

  for (const title of ["First keyboard title", "Second keyboard title"]) {
    await page.keyboard.press("Enter");
    await expect(input).toBeFocused();
    await input.fill(title);
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("article", { name: `${title} project` })).toBeVisible();
    await expect(page.getByRole("status")).toContainText("Title saved");
    await expect(
      page
        .getByRole("article", { name: `${title} project` })
        .getByRole("button", { name: "Edit title" })
    ).toBeFocused();
  }
});

test("provides semantic landmarks and a visible keyboard focus indicator", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("main")).toHaveCount(1);
  await expect(page.getByRole("heading", { level: 1, name: "Project Catalog" })).toBeVisible();
  await expect(page.getByRole("search")).toBeVisible();
  await expect(page.getByLabel("Search")).toBeVisible();
  await expect(page.getByLabel("Status")).toBeVisible();
  await expect(page.getByRole("list")).toBeVisible();

  const query = page.getByLabel("Search");
  await query.focus();
  const focusStyle = await query.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      width: Number.parseFloat(style.outlineWidth),
      style: style.outlineStyle,
      color: style.outlineColor
    };
  });
  expect(focusStyle.width).toBeGreaterThanOrEqual(2);
  expect(focusStyle.style).not.toBe("none");
  expect(focusStyle.color).not.toBe("transparent");
});

test("reduces transition and animation durations for reduced-motion users", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const durations = await page
    .getByRole("button", { name: "Search", exact: true })
    .evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        transition: style.transitionDuration,
        animation: style.animationDuration
      };
    });

  expect(maximumDurationInMilliseconds(durations.transition)).toBeLessThanOrEqual(0.01);
  expect(maximumDurationInMilliseconds(durations.animation)).toBeLessThanOrEqual(0.01);
});

test("avoids horizontal overflow at 320px, 200% zoom, and the maximum title length", async ({
  page
}) => {
  const longTitle = "A".repeat(80);
  const update = await page.request.patch("/api/projects/network-inspector", {
    data: { title: longTitle, version: 1 }
  });
  expect(update.status()).toBe(200);

  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: longTitle })).toBeVisible();
  expect(await hasNoHorizontalOverflow(page)).toBe(true);

  await page.setViewportSize({ width: 640, height: 720 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  expect(await hasNoHorizontalOverflow(page)).toBe(true);
});

test("keeps initial JavaScript and DOM size within the published budget", async ({ page }) => {
  const scriptBytes: number[] = [];
  page.on("response", async (response) => {
    if (response.request().resourceType() !== "script") return;
    try {
      scriptBytes.push((await response.body()).byteLength);
    } catch {
      // 화면 이동 중 취소되어 응답 본문을 받지 못한 스크립트는 초기 응답 합계에 포함하지 않습니다.
    }
  });

  await page.goto("/", { waitUntil: "networkidle" });
  const totalScriptBytes = scriptBytes.reduce((total, size) => total + size, 0);
  const domNodes = await page.locator("*").count();

  expect(totalScriptBytes).toBeGreaterThan(0);
  expect(totalScriptBytes).toBeLessThanOrEqual(budget.maximumInitialJavaScriptBytes);
  expect(domNodes).toBeLessThanOrEqual(budget.maximumDomNodes);
});

function maximumDurationInMilliseconds(value: string) {
  return Math.max(
    ...value.split(",").map((entry) => {
      const duration = entry.trim();
      if (duration.endsWith("ms")) return Number.parseFloat(duration);
      if (duration.endsWith("s")) return Number.parseFloat(duration) * 1_000;
      return Number.POSITIVE_INFINITY;
    })
  );
}

async function hasNoHorizontalOverflow(page: Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth
  );
}
