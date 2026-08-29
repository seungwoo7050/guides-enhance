/// <reference types="vitest/config" />

import { getViteConfig } from "astro/config";

// [Implementation 12]
// Unit tests exercise pure transformations; browser behavior remains in Playwright.
export default getViteConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    exclude: ["tests/e2e/**", "node_modules/**", "dist/**"]
  }
});
