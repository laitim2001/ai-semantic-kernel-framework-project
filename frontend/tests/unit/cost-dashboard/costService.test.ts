/**
 * File: frontend/tests/unit/cost-dashboard/costService.test.ts
 * Purpose: Unit test for costService — fetch URL building + 5xx error throw.
 * Category: Frontend / tests / unit / cost-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCostSummary } from "../../../src/features/cost-dashboard/services/costService";

describe("costService.fetchCostSummary", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("builds correct URL + returns parsed JSON on 200", async () => {
    const mockBody = {
      tenant_id: "t1",
      month: "2026-04",
      total_cost_usd: "5.00",
      by_type: {},
    };
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify(mockBody), { status: 200 }),
    );

    const result = await fetchCostSummary("tenant-uuid", "2026-04");
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/admin/tenants/tenant-uuid/cost-summary?month=2026-04",
      { credentials: "include" },
    );
    expect(result).toEqual(mockBody);
  });

  it("throws Error with detail message on 500", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "internal server error" }), { status: 500 }),
    );

    await expect(fetchCostSummary("tenant-uuid", "2026-04")).rejects.toThrow("internal server error");
  });
});
