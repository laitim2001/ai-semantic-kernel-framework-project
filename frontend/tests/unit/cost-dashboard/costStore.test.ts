/**
 * File: frontend/tests/unit/cost-dashboard/costStore.test.ts
 * Purpose: Unit test for costStore — loadData success/error transitions.
 * Category: Frontend / tests / unit / cost-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as costService from "../../../src/features/cost-dashboard/services/costService";
import { useCostStore } from "../../../src/features/cost-dashboard/store/costStore";
import type { CostSummaryResponse } from "../../../src/features/cost-dashboard/types";

describe("costStore", () => {
  beforeEach(() => {
    useCostStore.getState().reset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loadData success transitions: loading=true → data set → loading=false", async () => {
    const mockData: CostSummaryResponse = {
      tenant_id: "t1",
      month: "2026-04",
      total_cost_usd: "12.34",
      by_type: { llm_input: { "azure_openai_gpt-5.4": { quantity: "1000", total_cost_usd: "10.00", entry_count: 5 } } },
    };
    vi.spyOn(costService, "fetchCostSummary").mockResolvedValueOnce(mockData);

    const promise = useCostStore.getState().loadData("tenant-uuid");
    expect(useCostStore.getState().loading).toBe(true);
    await promise;
    expect(useCostStore.getState().loading).toBe(false);
    expect(useCostStore.getState().data).toEqual(mockData);
    expect(useCostStore.getState().error).toBeNull();
  });

  it("loadData error transitions: loading=true → error set → loading=false", async () => {
    vi.spyOn(costService, "fetchCostSummary").mockRejectedValueOnce(new Error("HTTP 500"));

    await useCostStore.getState().loadData("tenant-uuid");
    expect(useCostStore.getState().loading).toBe(false);
    expect(useCostStore.getState().error).toBe("HTTP 500");
    expect(useCostStore.getState().data).toBeNull();
  });

  it("setMonth clears stale data + error", () => {
    useCostStore.setState({
      data: {
        tenant_id: "t",
        month: "2026-03",
        total_cost_usd: "1",
        by_type: {},
      },
      error: "stale",
    });
    useCostStore.getState().setMonth("2026-04");
    expect(useCostStore.getState().currentMonth).toBe("2026-04");
    expect(useCostStore.getState().data).toBeNull();
    expect(useCostStore.getState().error).toBeNull();
  });
});
