import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

const budget = JSON.parse(
  readFileSync(join(process.cwd(), "performance-budget.json"), "utf8")
) as {
  maximumDetailJavaScriptBytes: number;
  maximumDetailDomNodes: number;
  maximumHydratedIslands: number;
};

// [Implementation 13-3]
// The test detects page-wide hydration, broken persistence and invisible keyboard focus.
test("only the favorite control hydrates and its state survives reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("astro-island")).toHaveCount(0);

  await page.goto("/resources/http-status-reference/");
  await expect(page.locator("astro-island")).toHaveCount(budget.maximumHydratedIslands);

  const button = page.getByRole("button", { name: "HTTP 상태 코드 빠른 참조 즐겨찾기 추가" });
  await expect(button).toBeEnabled();
  await button.focus();
  const outline = await button.evaluate((element) => {
    const style = getComputedStyle(element);
    return { width: Number.parseFloat(style.outlineWidth), style: style.outlineStyle };
  });
  expect(outline.width).toBeGreaterThanOrEqual(2);
  expect(outline.style).not.toBe("none");

  await button.click();
  await expect(
    page.getByRole("button", { name: "HTTP 상태 코드 빠른 참조 즐겨찾기 해제" })
  ).toHaveAttribute("aria-pressed", "true");

  await page.reload();
  await expect(
    page.getByRole("button", { name: "HTTP 상태 코드 빠른 참조 즐겨찾기 해제" })
  ).toHaveAttribute("aria-pressed", "true");
});

test("storage failure leaves the article usable and reports the failure", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(Storage.prototype, "setItem", {
      configurable: true,
      value() {
        throw new DOMException("storage blocked");
      }
    });
  });

  await page.goto("/resources/http-status-reference/");
  const button = page.getByRole("button", { name: "HTTP 상태 코드 빠른 참조 즐겨찾기 추가" });
  await button.click();

  await expect(button).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("status")).toHaveText(
    "브라우저 저장소에 즐겨찾기를 저장하지 못했습니다."
  );
  await expect(page.getByRole("heading", { name: "실패 종류를 먼저 나눕니다" })).toBeVisible();
});

test("detail JavaScript and DOM stay inside the declared budget", async ({ page }) => {
  const scriptBytes: number[] = [];
  page.on("response", async (response) => {
    if (response.request().resourceType() !== "script") return;
    try {
      scriptBytes.push((await response.body()).byteLength);
    } catch {
      // A canceled optional chunk is not part of the successfully loaded page body.
    }
  });

  await page.goto("/resources/http-status-reference/", { waitUntil: "networkidle" });
  const total = scriptBytes.reduce((sum, value) => sum + value, 0);
  const domNodes = await page.locator("*").count();

  expect(total).toBeGreaterThan(0);
  expect(total).toBeLessThanOrEqual(budget.maximumDetailJavaScriptBytes);
  expect(domNodes).toBeLessThanOrEqual(budget.maximumDetailDomNodes);
});

test("small screens and reduced motion preserve the reading flow", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/resources/unicode-normalization-notes/");

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth
    )
  ).toBe(true);

  const scrollBehavior = await page.evaluate(
    () => getComputedStyle(document.documentElement).scrollBehavior
  );
  expect(scrollBehavior).toBe("auto");
});
