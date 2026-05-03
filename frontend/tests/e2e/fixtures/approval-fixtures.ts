/**
 * File: frontend/tests/e2e/fixtures/approval-fixtures.ts
 * Purpose: Helpers + canned ApprovalSummary data for governance + chat e2e specs.
 * Category: Frontend / e2e / fixtures
 * Scope: Phase 53 / Sprint 53.6 US-2 + US-3
 *
 * Description:
 *   Sprint 53.6 e2e specs use Playwright `page.route()` network mocks rather
 *   than booting a real backend + seeding DB + issuing JWTs. Rationale (D11):
 *
 *     1. Backend integration is exercised by `tests/integration/api/
 *        test_governance_endpoints.py` (11 cases incl. cross-tenant 404).
 *     2. e2e specs OWN frontend behavior validation: list rendering,
 *        modal interaction, request payload shape, error UI.
 *     3. Mocking at network layer keeps specs fast (~5s vs ~60s with backend
 *        boot) and isolated (no DB cleanup, no port conflicts in CI).
 *
 *   This module exports:
 *     - sampleApprovals(): canned ApprovalSummary[] (3 items, 2 risk levels)
 *     - mockGovernanceList(page, items): wires GET /api/v1/governance/approvals
 *     - mockGovernanceDecide(page, opts): wires POST /api/v1/governance/approvals/{id}/decide
 *
 * Created: 2026-05-04 (Sprint 53.6 Day 2)
 *
 * Related:
 *   - frontend/src/features/governance/types.ts (ApprovalSummary shape)
 *   - frontend/src/features/governance/services/governanceService.ts (API contract)
 *   - tests/e2e/governance/approvals.spec.ts (US-2 consumer)
 */

import type { Page, Route } from "@playwright/test";

export type ApprovalFixture = {
  request_id: string;
  tenant_id: string;
  session_id: string;
  requester: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  payload: {
    tool_name: string;
    tool_arguments?: Record<string, unknown>;
    reason?: string;
    summary?: string;
  };
  sla_deadline: string;
  context_snapshot: Record<string, unknown>;
};

const TENANT_A = "00000000-0000-4000-8000-00000000000a";

/** Canned approvals for tenant A — used by US-2 spec. Three items, mix of risk levels. */
export function sampleApprovals(): ApprovalFixture[] {
  const futureSla = new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString();
  return [
    {
      request_id: "11111111-1111-4111-8111-111111111111",
      tenant_id: TENANT_A,
      session_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      requester: "alice@tenant-a.example",
      risk_level: "HIGH",
      payload: {
        tool_name: "delete_customer_record",
        tool_arguments: { customer_id: "C-1024" },
        reason: "Compliance escalation",
        summary: "approve tool call: delete_customer_record",
      },
      sla_deadline: futureSla,
      context_snapshot: {},
    },
    {
      request_id: "22222222-2222-4222-8222-222222222222",
      tenant_id: TENANT_A,
      session_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      requester: "bob@tenant-a.example",
      risk_level: "MEDIUM",
      payload: {
        tool_name: "send_external_email",
        tool_arguments: { recipient: "ext@example.com" },
        reason: "Outbound email policy review",
        summary: "approve tool call: send_external_email",
      },
      sla_deadline: futureSla,
      context_snapshot: {},
    },
    {
      request_id: "33333333-3333-4333-8333-333333333333",
      tenant_id: TENANT_A,
      session_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      requester: "carol@tenant-a.example",
      risk_level: "CRITICAL",
      payload: {
        tool_name: "execute_db_migration",
        reason: "Schema change escalation",
        summary: "approve tool call: execute_db_migration",
      },
      sla_deadline: futureSla,
      context_snapshot: {},
    },
  ];
}

/**
 * Mock GET /api/v1/governance/approvals to return the supplied items.
 *
 * The mutable wrapper allows tests to swap the response between calls
 * (e.g. show 3 items → reviewer approves one → next poll shows 2 items).
 */
export async function mockGovernanceList(
  page: Page,
  initial: ApprovalFixture[],
): Promise<{ setItems: (items: ApprovalFixture[]) => void; getCallCount: () => number }> {
  let items = [...initial];
  let calls = 0;
  await page.route("**/api/v1/governance/approvals", async (route: Route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    calls += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items, count: items.length }),
    });
  });
  return {
    setItems: (next: ApprovalFixture[]) => {
      items = [...next];
    },
    getCallCount: () => calls,
  };
}

export type DecideRecord = {
  requestId: string;
  decision: string;
  reason: string | null;
};

/**
 * Mock POST /api/v1/governance/approvals/{id}/decide. Returns 200 by default;
 * supply `respondWith` to override (e.g. status 500 for error test).
 *
 * The captured records array is appended in order — assert against it after
 * the test action to verify the spec dispatched the right requests.
 */
export async function mockGovernanceDecide(
  page: Page,
  opts: {
    respondWith?: { status: number; body: object };
  } = {},
): Promise<{ records: DecideRecord[] }> {
  const records: DecideRecord[] = [];
  const response = opts.respondWith ?? {
    status: 200,
    body: { request_id: "", decision: "approved", reviewer: "test" },
  };
  await page.route("**/api/v1/governance/approvals/*/decide", async (route: Route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    const url = new URL(route.request().url());
    // /api/v1/governance/approvals/{id}/decide → segments [..., approvals, id, decide]
    const segments = url.pathname.split("/");
    const requestId = segments[segments.length - 2] ?? "";
    const body = (route.request().postDataJSON() ?? {}) as {
      decision?: string;
      reason?: string | null;
    };
    records.push({
      requestId,
      decision: body.decision ?? "",
      reason: body.reason ?? null,
    });
    await route.fulfill({
      status: response.status,
      contentType: "application/json",
      body: JSON.stringify({ ...response.body, request_id: requestId }),
    });
  });
  return { records };
}
