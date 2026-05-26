/**
 * File: frontend/tests/unit/tenant-settings/useTenantIdentity.test.tsx
 * Purpose: Vitest coverage for Sprint 57.50 useTenantIdentity hook (Identity fixture cleanup).
 * Category: Frontend / Tests / tenant-settings / unit
 * Scope: Phase 57 / Sprint 57.50 Day 1 (closes AD-TenantSettings-IdentityFixture-Cleanup)
 *
 * Description:
 *   Verifies useTenantIdentity hook honors the standard pattern:
 *   - TENANT_IDENTITY_QUERY_KEY_BASE is exported + correctly namespaced
 *   - `enabled: Boolean(tenantId)` short-circuit when empty
 *   - Service call on success returns the mock data with 4 fields
 *     (provider/scim_enabled/allowed_domains/mfa_required)
 *
 * Created: 2026-05-26 (Sprint 57.50 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.50 Day 1)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import * as svc from "@/features/tenant-settings/services/tenantSettingsService";
import {
  TENANT_IDENTITY_QUERY_KEY_BASE,
  useTenantIdentity,
} from "@/features/tenant-settings/hooks/useTenantIdentity";

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("Sprint 57.50 — useTenantIdentity hook", () => {
  test("TENANT_IDENTITY_QUERY_KEY_BASE = ['tenant-settings', 'identity']", () => {
    expect(TENANT_IDENTITY_QUERY_KEY_BASE).toEqual(["tenant-settings", "identity"]);
  });

  test("disabled when tenantId is empty", async () => {
    const spy = vi.spyOn(svc, "fetchTenantIdentity").mockResolvedValue({
      provider: "SAML 2.0 · WorkOS",
      scim_enabled: true,
      allowed_domains: ["acme.com"],
      mfa_required: true,
    });
    const { result } = renderHook(() => useTenantIdentity(""), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches with tenantId + returns 4-field identity on success", async () => {
    const payload = {
      provider: "SAML 2.0 · WorkOS",
      scim_enabled: true,
      allowed_domains: ["acme.com", "acme.io"],
      mfa_required: true,
    };
    vi.spyOn(svc, "fetchTenantIdentity").mockResolvedValueOnce(payload);
    const { result } = renderHook(() => useTenantIdentity("tenant-x"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(payload);
    expect(result.current.data?.allowed_domains).toHaveLength(2);
    expect(result.current.data?.mfa_required).toBe(true);
  });

  test("propagates error from fetchTenantIdentity rejection", async () => {
    vi.spyOn(svc, "fetchTenantIdentity").mockRejectedValueOnce(new Error("HTTP 404: tenant not found"));
    const { result } = renderHook(() => useTenantIdentity("tenant-missing"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toContain("tenant not found");
  });
});
