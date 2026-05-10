/**
 * File: frontend/tests/e2e/memory/memory-page.spec.ts
 * Purpose: Playwright e2e — Sprint 57.12 US-5/US-8 /memory page ship (auth gate + 2-tab nav + recent table).
 * Category: Frontend / e2e / memory
 * Scope: Phase 57 / Sprint 57.12 Day 4 / US-8
 *
 * Description:
 *   Validates the /memory page (US-5) routing ship (US-8):
 *     1. Auth gate redirects to /auth/login when unauthenticated.
 *     2. Authenticated visit renders AppShellV2 (h1 "Memory") + 2 tab links
 *        (Recent / By Scope) + the recent table populated from a mocked
 *        GET /api/v1/memory/recent (page.route() per
 *        feedback_e2e_network_mocking_pattern — backend coverage lives in
 *        tests/integration/api/test_memory.py).
 *     3. Default redirect: /memory → /memory/recent.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 4 / US-8)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 4 / US-8)
 *
 * Related:
 *   - frontend/src/pages/memory/index.tsx (auth gate + AppShellV2 + nested routes)
 *   - frontend/src/features/memory/components/MemoryRecentList.tsx
 *   - frontend/src/routes.config.ts (Sprint 57.12 US-8 — /memory active=true)
 *   - tests/e2e/fixtures/auth-fixtures.ts (seedAuthJwt / clearAuthJwt)
 */

import { expect, test, type Page } from "@playwright/test";

import { clearAuthJwt, seedAuthJwt } from "../fixtures/auth-fixtures";

const SAMPLE_RECENT_PAGE = {
  items: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      layer: "user" as const,
      scope_id: "22222222-2222-4222-8222-222222222222",
      key: null,
      content: "User prefers dark mode and terse summaries.",
      category: "preference",
      expires_at_ms: null,
      created_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
      updated_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
      tenant_id: "33333333-3333-4333-8333-333333333333",
    },
    {
      id: "44444444-4444-4444-8444-444444444444",
      layer: "user" as const,
      scope_id: "22222222-2222-4222-8222-222222222222",
      key: null,
      content: "Last deployment incident: 2026-04-29 cache stampede.",
      category: "incident",
      expires_at_ms: Date.UTC(2026, 7, 10, 0, 0, 0),
      created_at_ms: Date.UTC(2026, 4, 10, 8, 5, 0),
      updated_at_ms: Date.UTC(2026, 4, 10, 8, 5, 0),
      tenant_id: "33333333-3333-4333-8333-333333333333",
    },
  ],
  total: 2,
  has_more: false,
  next_offset: null,
  page_size: 50,
};

async function mockMemoryRecent(page: Page, body: typeof SAMPLE_RECENT_PAGE): Promise<void> {
  await page.route("**/api/v1/memory/recent**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test.describe("Sprint 57.12 US-8 — /memory page", () => {
  test("auth gate: unauthenticated visit redirects to /auth/login", async ({ page }) => {
    await clearAuthJwt(page);
    await page.goto("/memory");
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("authenticated visit renders AppShellV2 + 2 tabs + recent table rows", async ({ page }) => {
    await seedAuthJwt(page);
    await mockMemoryRecent(page, SAMPLE_RECENT_PAGE);

    await page.goto("/memory");

    // Default redirect /memory → /memory/recent.
    await expect(page).toHaveURL(/\/memory\/recent$/);

    // AppShellV2 page-level title + 2 tab links.
    await expect(page.getByRole("heading", { level: 1, name: "Memory" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Recent" })).toBeVisible();
    await expect(page.getByRole("link", { name: "By Scope" })).toBeVisible();

    // MemoryRecentList rendered + 2 mocked rows visible.
    await expect(page.getByTestId("memory-table")).toBeVisible();
    await expect(page.getByText(/User prefers dark mode/i)).toBeVisible();
    await expect(page.getByText(/cache stampede/i)).toBeVisible();
  });
});
