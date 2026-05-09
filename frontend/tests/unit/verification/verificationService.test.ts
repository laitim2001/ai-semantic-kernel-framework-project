/**
 * File: frontend/tests/unit/verification/verificationService.test.ts
 * Purpose: Unit test for verificationService — URL building + 4xx/5xx error surface + fetchWithAuth integration.
 * Category: Frontend / tests / unit / verification
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.11 Day 2 / US-3)
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  _testing,
  verificationService,
} from "../../../src/features/verification/services/verificationService";
import type { VerificationLogFilter } from "../../../src/features/verification/types";

describe("verificationService.fetchVerificationRecent", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("builds URL with all filter params + returns parsed JSON on 200", async () => {
    const mockBody = {
      items: [
        {
          id: 1,
          tenant_id: "t1",
          session_id: "s1",
          turn_index: 0,
          verifier_name: "v1",
          verifier_type: "rules_based",
          passed: true,
          score: 0.95,
          reason: null,
          suggested_correction: null,
          correction_attempt: 0,
          created_at_ms: 1234567890000,
        },
      ],
      total: 1,
      has_more: false,
      next_offset: null,
      page_size: 50,
    };
    fetchSpy.mockResolvedValueOnce(new Response(JSON.stringify(mockBody), { status: 200 }));

    const filter: VerificationLogFilter = {
      session_id: "session-uuid",
      verifier_type: "rules_based",
      passed: false,
      limit: 50,
      offset: 0,
    };
    const result = await verificationService.fetchVerificationRecent(filter);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/verification/recent?"),
      expect.objectContaining({ credentials: "include" }),
    );
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain("session_id=session-uuid");
    expect(calledUrl).toContain("verifier_type=rules_based");
    expect(calledUrl).toContain("passed=false");
    expect(calledUrl).toContain("limit=50");
    expect(calledUrl).toContain("offset=0");
    expect(result).toEqual(mockBody);
  });

  it("omits undefined / empty filter fields from URLSearchParams", () => {
    const params = _testing._buildVerificationSearchParams({
      session_id: "  ", // whitespace-only → omit
      limit: 25,
      offset: 0,
    });
    expect(params.get("session_id")).toBeNull();
    expect(params.get("verifier_type")).toBeNull();
    expect(params.get("passed")).toBeNull();
    expect(params.get("limit")).toBe("25");
    expect(params.get("offset")).toBe("0");
  });

  it("throws Error with detail message on 403", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Audit role required" }), { status: 403 }),
    );

    await expect(
      verificationService.fetchVerificationRecent({ limit: 50, offset: 0 }),
    ).rejects.toThrow("Audit role required");
  });
});

describe("verificationService.fetchCorrectionTrace", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(global, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("builds URL with sessionId path param + returns parsed JSON on 200", async () => {
    const mockBody = { session_id: "abc-123", entries: [] };
    fetchSpy.mockResolvedValueOnce(new Response(JSON.stringify(mockBody), { status: 200 }));

    const result = await verificationService.fetchCorrectionTrace("abc-123");

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/v1/verification/abc-123/correction-trace",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(result).toEqual(mockBody);
  });

  it("throws Error with detail on 404 empty trace", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "No verification entries for this session." }), {
        status: 404,
      }),
    );

    await expect(verificationService.fetchCorrectionTrace("ghost-session")).rejects.toThrow(
      "No verification entries for this session.",
    );
  });
});
