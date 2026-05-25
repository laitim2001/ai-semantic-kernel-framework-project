/**
 * File: frontend/tests/e2e/governance/approvals.spec.ts
 * Purpose: Playwright e2e — reviewer flow on /governance/approvals page
 *   (Sprint 57.40 rebuild: 5-component composition + inline DetailPane).
 * Category: Frontend / e2e / governance
 * Scope: Phase 53 / Sprint 53.6 US-2 → Sprint 57.40 (mockup rebuild adapt)
 *
 * Description:
 *   Validates the post-Sprint-57.40 governance approvals page:
 *     1. Renders HITL Approvals header + 5-tab nav + 4-KPI strip + 2-col grid
 *     2. Row click selects approval → ApprovalDetailPane renders on right col
 *     3. Approve & continue / Reject buttons dispatch decide POST (no reason)
 *     4. Escalate / Approve-with-edits are AP-2 alert stubs (no decide POST)
 *     5. Empty list renders the no-items message
 *
 *   Mock layer unchanged (page.route() at network layer; backend integration
 *   covered by tests/integration/api/test_governance_endpoints.py).
 *
 * Created: 2026-05-04 (Sprint 53.6 Day 2)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — adapt to mockup-fidelity rebuild (heading HITL Approvals; row-click selects → DetailPane; no DecisionModal; no reason field; Escalate AP-2 alert stub; error UI surface deferred Phase 58+ — see AD-ApprovalDetailPane-Mutation-Error-Surface carryover)
 *   - 2026-05-09: Sprint 57.9 US-6 Day 4 — add seedAuthJwt beforeEach (auth gate)
 *   - 2026-05-04: Initial creation (Sprint 53.6 Day 2)
 *
 * Related:
 *   - frontend/src/features/governance/components/{ApprovalsPage,ApprovalsPageHeader,ApprovalsStatsStrip,ApprovalsFilterTabs,ApprovalList,ApprovalDetailPane,ApprovalsEmptyTab}.tsx
 *   - frontend/src/features/governance/hooks/{useApprovals,useApprovalDecide}.ts
 *   - tests/e2e/fixtures/approval-fixtures.ts
 *   - tests/e2e/fixtures/auth-fixtures.ts (seedAuthJwt for auth gate bypass)
 */

import { expect, test } from "@playwright/test";

import {
  mockGovernanceDecide,
  mockGovernanceList,
  sampleApprovals,
} from "../fixtures/approval-fixtures";
import { seedAuthJwt } from "../fixtures/auth-fixtures";

test.describe("Sprint 57.40 — Governance approvals reviewer flow (post-rebuild)", () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthJwt(page);
  });

  test("main flow: approve removes the item from the list", async ({ page }) => {
    const items = sampleApprovals();
    const list = await mockGovernanceList(page, items);
    const decide = await mockGovernanceDecide(page);

    await page.goto("/governance/approvals");

    // HITL Approvals heading + Pending approvals card title
    // page-title is a <div className="page-title"> verbatim from mockup, no implicit heading role
    await expect(page.getByText("HITL Approvals", { exact: true })).toBeVisible();
    await expect(page.getByText("Pending approvals", { exact: true })).toBeVisible();

    // ApprovalList: header row + 3 data rows = 4 rows total. Don't probe text
    // with getByText — sessionTitle (from payload.summary) and the tool-name
    // cell can both contain the same string, tripping strict-mode duplicate.
    // Row-by-name regex on the click locator below covers row identity.
    await expect(page.getByRole("row")).toHaveCount(4);

    // DetailPane empty-state copy visible before selection.
    await expect(
      page.getByText("Select an approval from the list to view details."),
    ).toBeVisible();

    // Click row → DetailPane re-renders with request_id mono in header.
    await page.getByRole("row", { name: /delete_customer_record/ }).click();
    await expect(page.getByText(items[0].request_id)).toBeVisible();

    // Approve & continue → mutate dispatches with NO reason field; refresh
    // shows the remaining 2 items.
    list.setItems(items.slice(1));
    await page.getByRole("button", { name: "Approve & continue" }).click();

    // List collapsed to header + 2 rows.
    await expect(page.getByRole("row")).toHaveCount(3);
    await expect(page.getByText("delete_customer_record")).not.toBeVisible();

    // POST shape — no reason field in new flow (DetailPane has no textbox).
    expect(decide.records).toHaveLength(1);
    expect(decide.records[0]).toMatchObject({
      requestId: items[0].request_id,
      decision: "approved",
      reason: null,
    });
  });

  test("reject flow dispatches decision=rejected", async ({ page }) => {
    const items = sampleApprovals();
    await mockGovernanceList(page, items);
    const decide = await mockGovernanceDecide(page);

    await page.goto("/governance/approvals");
    await page.getByRole("row", { name: /send_external_email/ }).click();
    await expect(page.getByText(items[1].request_id)).toBeVisible();

    await page.getByRole("button", { name: /^Reject$/ }).click();

    expect(decide.records).toHaveLength(1);
    expect(decide.records[0]).toMatchObject({
      requestId: items[1].request_id,
      decision: "rejected",
      reason: null,
    });
  });

  test("escalate AP-2 stub fires alert + does NOT dispatch decide", async ({ page }) => {
    // Sprint 57.40 deferred Escalate to L2 to Phase 58+ (backend gap). The
    // button surface is preserved per mockup but invokes alert() with a
    // "backend gap (Phase 58+)" message; no decide POST is dispatched.
    const items = sampleApprovals();
    await mockGovernanceList(page, items);
    const decide = await mockGovernanceDecide(page);

    // Capture the alert dialog via page.on("dialog").
    const alerts: string[] = [];
    page.on("dialog", async (d) => {
      alerts.push(d.message());
      await d.dismiss();
    });

    await page.goto("/governance/approvals");
    await page.getByRole("row", { name: /execute_db_migration/ }).click();
    await expect(page.getByText(items[2].request_id)).toBeVisible();

    await page.getByRole("button", { name: /Escalate to L2/ }).click();

    // Alert was triggered with AP-2 backend-gap message.
    expect(alerts).toHaveLength(1);
    expect(alerts[0]).toMatch(/backend gap/i);

    // Critically: no decide POST was dispatched (AP-2 stub).
    expect(decide.records).toHaveLength(0);
  });

  test.skip(
    "decide error UI surface — DEFERRED Phase 58+ AD-ApprovalDetailPane-Mutation-Error-Surface",
    async () => {
      // Sprint 57.40 rebuild removed DecisionModal which previously hosted the
      // [role="alert"] region. ApprovalDetailPane currently has no UI surface
      // for useApprovalDecide.mutate() error states. Restoring proper error UI
      // (banner inside DetailPane or page-level toast) is deferred to Phase 58+
      // per next-phase-candidates.md carryover AD. Test will be unskipped when
      // the error UI is wired.
    },
  );

  test("empty list renders the no-items message", async ({ page }) => {
    await mockGovernanceList(page, []);

    await page.goto("/governance/approvals");
    // Page-level heading (mockup .page-title) + Card title still present even
    // when zero items.
    // page-title is a <div className="page-title"> verbatim from mockup, no implicit heading role
    await expect(page.getByText("HITL Approvals", { exact: true })).toBeVisible();
    await expect(page.getByText("Pending approvals", { exact: true })).toBeVisible();
    // ApprovalList early-return text (kept verbatim from Sprint 53.5 vintage).
    await expect(page.getByText("No pending approvals.")).toBeVisible();
  });
});
