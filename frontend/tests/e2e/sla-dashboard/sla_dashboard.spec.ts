/**
 * File: frontend/tests/e2e/sla-dashboard/sla_dashboard.spec.ts
 * Purpose: Playwright e2e — admin loads /sla-dashboard with mocked sla-report endpoint.
 * Category: Frontend / e2e / sla-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-5 → Sprint 57.25 (mockup-fidelity rebuild adapt)
 *
 * Description:
 *   Validates the SLA Dashboard post-Sprint-57.25 6-widget-group rebuild:
 *     1. Happy path: admin loads /sla-dashboard?tenant_id=... → fetches
 *        56.3 sla-report → renders 6 mockup widget groups (page-head /
 *        4-stat grid / LatencyChart / SLO status / slow ops / error rate)
 *        + MonthPicker auxiliary preserved per Sprint 57.25 Q1 alignment.
 *     2. Error path: backend 500 → error message + retry button → mock 200
 *        → click retry → success.
 *
 *   Uses page.route() browser-layer mock per D19 (mirrors cost_dashboard.spec.ts).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 4)
 * Last Modified: 2026-05-19
 *
 * Modification History (newest-first):
 *   - 2026-05-19: Sprint 57.25 Day 3 — adapt selectors for 6-widget rebuild
 *     (violations-badge + 6 sla-card-* DELETED with Karpathy §3 orphan
 *     SLAMetricsCard removal; replaced by sla-stat-grid + sla-latency-chart
 *     + sla-slo-card + sla-slow-ops-table + sla-error-rate-card visibility)
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 4)
 */

import { expect, test } from "@playwright/test";

import { seedAuthJwt } from "../fixtures/auth-fixtures";

const TENANT_ID = "00000000-0000-4000-8000-000000000099";
const SLA_ENDPOINT = `**/api/v1/admin/tenants/${TENANT_ID}/sla-report**`;

const mockSLAReport = {
  tenant_id: TENANT_ID,
  month: new Date().toISOString().substring(0, 7),
  availability_pct: 99.7,
  api_p99_ms: 850,
  loop_simple_p99_ms: 4200,
  loop_medium_p99_ms: 28000,
  loop_complex_p99_ms: 110000,
  hitl_queue_notif_p99_ms: 45000,
  violations_count: 0,
};

test.describe("Sprint 57.1 US-5 → 57.25 — SLA Dashboard e2e (mockup-fidelity rebuild)", () => {
  // Sprint 57.13 US-A2: the page is <RequireAuth>-gated + reads authStore.tenant.id.
  test.beforeEach(async ({ page }) => {
    await seedAuthJwt(page, { tenantId: TENANT_ID });
  });

  test("happy path: admin loads dashboard, sees 6 mockup widget groups + MonthPicker auxiliary", async ({ page }) => {
    await page.route(SLA_ENDPOINT, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockSLAReport),
      });
    });

    await page.goto(`/sla-dashboard?tenant_id=${TENANT_ID}`);

    // AppShellV2 pageTitle="SLA Dashboard" renders h1 chrome heading
    await expect(page.getByRole("heading", { name: "SLA Dashboard" })).toBeVisible();

    // MonthPicker preserved as auxiliary per Sprint 57.25 Q1 alignment
    await expect(page.getByLabel("Select month")).toBeVisible();

    // §1 page-head NEW Sprint 57.25 widgets
    await expect(page.getByTestId("sla-range-tab-24h")).toBeVisible();
    await expect(page.getByTestId("sla-action-refresh")).toBeVisible();
    await expect(page.getByTestId("sla-action-export")).toBeVisible();

    // §2 4-stat sparkline grid (Sprint 57.25 Day 1 US-B2)
    await expect(page.getByTestId("sla-stat-grid")).toBeVisible();

    // §3 24h LatencyChart 3-series (Sprint 57.25 Day 1 US-B3)
    await expect(page.getByTestId("sla-latency-chart")).toBeVisible();

    // §4 SLO status card (Sprint 57.25 Day 2 US-C1)
    await expect(page.getByTestId("sla-slo-card")).toBeVisible();

    // §5 Top slow operations table (Sprint 57.25 Day 2 US-C2)
    await expect(page.getByTestId("sla-slow-ops-table")).toBeVisible();

    // §6 Error rate by service card (Sprint 57.25 Day 2 US-C3)
    await expect(page.getByTestId("sla-error-rate-card")).toBeVisible();
  });

  test("error path: backend 500 shows retry; mock 200 on retry recovers", async ({ page }) => {
    // Sprint 57.9 US-6 Day 4: TanStack StrictMode double-render fix — gate
    // success on retryClicked instead of firstCall flag (mirror cost-dashboard).
    let retryClicked = false;
    await page.route(SLA_ENDPOINT, async (route) => {
      if (!retryClicked) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "internal server error" }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockSLAReport),
        });
      }
    });

    await page.goto(`/sla-dashboard?tenant_id=${TENANT_ID}`);

    // Error UX visible (Sprint 57.13 US-B2: <ErrorRetry> headline)
    await expect(page.getByText("Failed to load data")).toBeVisible();
    const retryButton = page.getByRole("button", { name: "Retry" });
    await expect(retryButton).toBeVisible();

    retryClicked = true;
    await retryButton.click();

    // Post-retry: ErrorRetry banner gone; 6 widget groups remain visible
    // (the 4-stat grid / chart / SLO / slow ops / error rate render
    // unconditionally outside the `error &&` guard per Sprint 57.25 layout).
    await expect(page.getByText("Failed to load data")).not.toBeVisible();
    await expect(page.getByTestId("sla-stat-grid")).toBeVisible();
    await expect(page.getByTestId("sla-latency-chart")).toBeVisible();
  });
});
