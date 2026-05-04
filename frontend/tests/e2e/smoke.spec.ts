/**
 * File: frontend/tests/e2e/smoke.spec.ts
 * Purpose: Minimal smoke test verifying Playwright runner spawns headless chromium
 *   and the dev/preview server serves the SPA.
 * Category: Frontend / e2e / smoke
 * Scope: Phase 53 / Sprint 53.6 US-1
 *
 * Description:
 *   The smoke spec is intentionally tiny — it exists to prove the bootstrap
 *   works (npm install + browser install + playwright.config.ts + webServer
 *   auto-start). Any actual feature coverage is owned by the governance +
 *   chat ApprovalCard specs (Sprint 53.6 US-2 / US-3).
 *
 * Created: 2026-05-04 (Sprint 53.6 Day 1)
 *
 * Related:
 *   - playwright.config.ts (testDir + webServer)
 *   - frontend/index.html (title source)
 */

import { expect, test } from "@playwright/test";

test.describe("Sprint 53.6 US-1 Playwright bootstrap smoke", () => {
  test("home page loads with expected title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/IPA Platform/i);
  });

  test("governance route resolves without crash", async ({ page }) => {
    const response = await page.goto("/governance/approvals");
    // SPA always returns the index HTML; just assert non-5xx.
    expect(response?.ok()).toBeTruthy();
    await expect(page).toHaveTitle(/IPA Platform/i);
  });
});
