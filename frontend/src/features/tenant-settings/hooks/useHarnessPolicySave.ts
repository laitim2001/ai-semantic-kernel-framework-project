/**
 * File: frontend/src/features/tenant-settings/hooks/useHarnessPolicySave.ts
 * Purpose: TanStack mutation hook — PUT /admin/tenants/{id}/harness-policy composite-replace.
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.106 C3 (Harness Policy tab write side)
 *
 * Description:
 *   Wraps `putHarnessPolicy` service func with TanStack `useMutation`. On success
 *   invalidates `[...HARNESS_POLICY_QUERY_KEY_BASE, tenantId]` to trigger GET
 *   re-fetch with the saved (sparse) policy applied. Verbatim mirror of Sprint
 *   57.104 `useModelPolicySave.ts` precedent.
 *
 * Created: 2026-06-12 (Sprint 57.106 C3)
 *
 * Modification History (newest-first):
 *   - 2026-06-12: Initial creation (Sprint 57.106 C3)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (putHarnessPolicy)
 *   - ./useHarnessPolicy.ts (HARNESS_POLICY_QUERY_KEY_BASE)
 *   - ../components/tabs/HarnessPolicyTab.tsx (consumer)
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { putHarnessPolicy } from "../services/tenantSettingsService";
import type { HarnessPolicy } from "../types";
import { HARNESS_POLICY_QUERY_KEY_BASE } from "./useHarnessPolicy";

export function useHarnessPolicySave(tenantId: string) {
  const qc = useQueryClient();
  return useMutation<HarnessPolicy, Error, HarnessPolicy>({
    mutationFn: (payload) => putHarnessPolicy(tenantId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: [...HARNESS_POLICY_QUERY_KEY_BASE, tenantId],
      });
    },
  });
}
