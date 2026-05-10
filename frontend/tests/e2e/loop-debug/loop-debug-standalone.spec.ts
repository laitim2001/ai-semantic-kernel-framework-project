/**
 * File: frontend/tests/e2e/loop-debug/loop-debug-standalone.spec.ts
 * Purpose: Playwright e2e — Sprint 57.12 US-4/US-8 /loop-debug standalone page ship.
 * Category: Frontend / e2e / loop-debug
 * Scope: Phase 57 / Sprint 57.12 Day 4 / US-8
 *
 * Description:
 *   Validates the /loop-debug standalone page (US-4) routing ship (US-8):
 *     1. Auth gate redirects to /auth/login when unauthenticated
 *        (Sprint 57.8 US-5 + 57.9 D-PRE-16 cascade lesson — seedAuthJwt
 *        required for authenticated tests).
 *     2. Authenticated visit renders AppShellV2 (h1 "Loop Debug") +
 *        LoopVisualizer standalone empty state (no live session events yet).
 *
 *   No backend boot — auth gate + page render only (the loop-debug page is a
 *   thin wrapper over LoopVisualizer reading the in-memory chat-v2 store, so
 *   a fresh tab shows the explanatory empty state). Inline-panel population is
 *   covered by chat-v2-loop-inline.spec.ts.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 4 / US-8)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 4 / US-8)
 *
 * Related:
 *   - frontend/src/pages/loop-debug/index.tsx (auth gate + AppShellV2 wrap)
 *   - frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx
 *   - frontend/src/routes.config.ts (Sprint 57.12 US-8 — /loop-debug active=true)
 *   - tests/e2e/fixtures/auth-fixtures.ts (seedAuthJwt / clearAuthJwt)
 */

import { expect, test } from "@playwright/test";

import { clearAuthJwt, seedAuthJwt } from "../fixtures/auth-fixtures";

test.describe("Sprint 57.12 US-8 — /loop-debug standalone page", () => {
  test("auth gate: unauthenticated visit redirects to /auth/login", async ({ page }) => {
    await clearAuthJwt(page);
    await page.goto("/loop-debug");
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("authenticated visit renders AppShellV2 + LoopVisualizer standalone empty state", async ({
    page,
  }) => {
    await seedAuthJwt(page);
    await page.goto("/loop-debug");

    // AppShellV2 page-level title (sticky header h1).
    await expect(page.getByRole("heading", { level: 1, name: "Loop Debug" })).toBeVisible();

    // LoopVisualizer standalone empty state (fresh tab: no chat-v2 session run yet).
    await expect(
      page.getByText(/No loop events yet\. Start a chat-v2 session/i),
    ).toBeVisible();
  });
});
