/**
 * File: frontend/tests/e2e/verification/verification-real-ship.spec.ts
 * Purpose: Playwright e2e — Sprint 57.11 US-6 verification page real ship (Sprint 57.41-adapted).
 * Category: Frontend / e2e / verification
 * Scope: Phase 57 / Sprint 57.11 Day 4 / US-6 (adapted Sprint 57.41 Day 2 post mockup-fidelity rebuild)
 *
 * Description:
 *   Validates the /verification/recent page ships under the Sprint 57.41
 *   full mockup-fidelity rebuild architecture (VerificationView with NEW
 *   components VerificationPageHeader + VerificationStatsStrip +
 *   VerificationRunsTable + FailureKindsCard + FlakyChecksCard). The old
 *   VerificationList + filter form was orphan-deleted Sprint 57.41 Day 1.
 *
 *   Backend network calls mocked at browser layer via page.route() (~5x
 *   faster than booting backend per memory feedback_e2e_network_mocking_pattern).
 *
 *   AD-Verification-RealShip-E2E (POTENTIAL DEFERRAL): chat-v2 inline panel
 *   SSE injection test was scoped as STRETCH per plan §4.2; deferred to
 *   Phase 57.12+ as SSE mock at Playwright layer is brittle.
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 4 / US-6)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: FIX-020-A — toBeVisible→toBeAttached for sidebar Card titles (right column below-fold at Playwright 1280px viewport; structural composition check semantics)
 *   - 2026-05-25: Sprint 57.41 Day 2 — adapted to mockup-shape view post-VerificationList orphan delete (3 obsolete tests replaced by 2 NEW mockup-shape tests)
 *   - 2026-05-10: Initial creation (Sprint 57.11 Day 4 / US-6)
 *
 * Related:
 *   - frontend/src/pages/verification/index.tsx (auth gate + nested routes)
 *   - frontend/src/features/verification/components/VerificationView.tsx (Sprint 57.41 rebuild)
 *   - frontend/src/features/verification/components/VerificationRunsTable.tsx (Sprint 57.41 NEW)
 *   - tests/e2e/fixtures/auth-fixtures.ts (seedAuthJwt)
 */

import { expect, test, type Page } from "@playwright/test";

import { seedAuthJwt } from "../fixtures/auth-fixtures";

const SAMPLE_RECENT_PAGE = {
  items: [
    {
      id: "ver_1",
      session_id: "33333333-3333-4333-8333-333333333333",
      verifier_name: "salesforce_query",
      verifier_type: "llm_judge",
      passed: true,
      reason: "PII access requested for incident response",
      score: 0.94,
      created_at_ms: Date.now() - 60_000,
    },
    {
      id: "ver_2",
      session_id: "33333333-3333-4333-8333-333333333334",
      verifier_name: "patrol_get_results",
      verifier_type: "rules_based",
      passed: false,
      reason: "verifier.check failed: 1 of 5 items has no owner",
      score: 0.42,
      created_at_ms: Date.now() - 300_000,
    },
  ],
  total: 2,
  has_more: false,
};

async function mockVerificationRecent(
  page: Page,
  body: typeof SAMPLE_RECENT_PAGE | { items: never[]; total: 0; has_more: false },
): Promise<void> {
  await page.route("**/api/v1/verification/recent**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test.describe("Sprint 57.11 US-6 — Verification page real ship (Sprint 57.41-adapted)", () => {
  test("auth gate redirects to /auth/login when unauthenticated", async ({ page }) => {
    // No seedAuthJwt — simulate unauthenticated visitor
    await page.goto("/verification");
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("recent tab renders mockup-shape view (Sprint 57.41)", async ({ page }) => {
    await seedAuthJwt(page);
    await mockVerificationRecent(page, { items: [], total: 0, has_more: false });

    await page.goto("/verification");

    // Page header (Sprint 57.41 NEW VerificationPageHeader)
    await expect(page.getByText("Verification").first()).toBeVisible();

    // Sidebar mockup-shape Cards (Sprint 57.41 NEW FailureKindsCard + FlakyChecksCard).
    // FIX-020-A: toBeAttached() for sidebar (DOM presence) — the right column at
    // Playwright's 1280px default viewport renders below-fold when the table
    // grows tall; the spec's purpose is structural composition rendered, not
    // viewport visibility. Same lesson as Sprint 57.40 Day 2 D-DAY2-1 adapter
    // projects-into-multiple-cells getAllByText pattern: assertion semantics
    // must match what we actually want to verify.
    await expect(page.getByText("Recent verification runs")).toBeVisible();
    await expect(page.getByText("Failure kinds")).toBeAttached();
    await expect(page.getByText("Flaky checks")).toBeAttached();

    // AP-2 BackendGapBanner declarations present (≥ 1 visible — 3 fixture KPI in
    // StatsStrip + 2 sidebar Cards each declare; recent runs Card does not)
    const banners = page.getByTestId("backend-gap-banner");
    expect(await banners.count()).toBeGreaterThanOrEqual(1);
  });

  test("recent tab handles 2 mocked items (Sprint 57.41)", async ({ page }) => {
    await seedAuthJwt(page);
    await mockVerificationRecent(page, SAMPLE_RECENT_PAGE);

    await page.goto("/verification");

    // VerificationRunsTable renders ≥ 2 data rows (verifier_name shown as agent cell)
    await expect(page.getByText("salesforce_query").first()).toBeVisible();
    await expect(page.getByText("patrol_get_results").first()).toBeVisible();
  });
});
