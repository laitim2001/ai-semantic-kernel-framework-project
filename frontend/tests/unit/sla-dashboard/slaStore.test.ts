/**
 * File: frontend/tests/unit/sla-dashboard/slaStore.test.ts
 * Purpose: Unit test for slaStore — loadData success/error transitions.
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-3
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as slaService from "../../../src/features/sla-dashboard/services/slaService";
import { useSLAStore } from "../../../src/features/sla-dashboard/store/slaStore";
import type { SLAReportResponse } from "../../../src/features/sla-dashboard/types";

const mockReport: SLAReportResponse = {
  tenant_id: "t1",
  month: "2026-04",
  availability_pct: 99.7,
  api_p99_ms: 850,
  loop_simple_p99_ms: 4200,
  loop_medium_p99_ms: 28000,
  loop_complex_p99_ms: 110000,
  hitl_queue_notif_p99_ms: 45000,
  violations_count: 0,
};

describe("slaStore", () => {
  beforeEach(() => {
    useSLAStore.getState().reset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loadData success transitions: loading=true → data set → loading=false", async () => {
    vi.spyOn(slaService, "fetchSLAReport").mockResolvedValueOnce(mockReport);

    const promise = useSLAStore.getState().loadData("tenant-uuid");
    expect(useSLAStore.getState().loading).toBe(true);
    await promise;
    expect(useSLAStore.getState().loading).toBe(false);
    expect(useSLAStore.getState().data).toEqual(mockReport);
    expect(useSLAStore.getState().error).toBeNull();
  });

  it("loadData error transitions: loading=true → error set → loading=false", async () => {
    vi.spyOn(slaService, "fetchSLAReport").mockRejectedValueOnce(new Error("HTTP 500"));

    await useSLAStore.getState().loadData("tenant-uuid");
    expect(useSLAStore.getState().loading).toBe(false);
    expect(useSLAStore.getState().error).toBe("HTTP 500");
    expect(useSLAStore.getState().data).toBeNull();
  });

  it("setMonth clears stale data + error", () => {
    useSLAStore.setState({ data: mockReport, error: "stale" });
    useSLAStore.getState().setMonth("2026-05");
    expect(useSLAStore.getState().currentMonth).toBe("2026-05");
    expect(useSLAStore.getState().data).toBeNull();
    expect(useSLAStore.getState().error).toBeNull();
  });
});
