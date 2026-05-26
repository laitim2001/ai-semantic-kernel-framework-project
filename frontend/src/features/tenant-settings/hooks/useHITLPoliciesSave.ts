/**
 * File: frontend/src/features/tenant-settings/hooks/useHITLPoliciesSave.ts
 * Purpose: TanStack Query mutation hook for HITLPolicies upsert PUT (consumed by HITLPoliciesTab edit mode).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.54 Track B
 *
 * Description:
 *   Mirror useTenantSettingsSave pattern (Sprint 57.9 US-6). On mutate() success
 *   the hook invalidates [...HITL_POLICIES_QUERY_KEY_BASE, tenantId] so
 *   HITLPoliciesTab auto-refreshes with the latest server state. Mutation state
 *   (isPending / error) consumed by HITLPoliciesTab edit mode for save-button
 *   disabled + inline-error rendering.
 *
 *   Sprint 57.54 Track B — closes AD-AgentFactor-Tier-3-Validation-Sprint-57.54.
 *
 * Created: 2026-05-26 (Sprint 57.54 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.54 Day 1 Track B)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (saveHITLPolicies)
 *   - ./useHITLPolicies.ts (HITL_POLICIES_QUERY_KEY_BASE single-source)
 *   - ../components/tabs/HITLPoliciesTab.tsx (consumer)
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { saveHITLPolicies } from "../services/tenantSettingsService";
import type {
  HITLPolicyUpsertRequest,
  HITLPolicyUpsertResponse,
} from "../types";
import { HITL_POLICIES_QUERY_KEY_BASE } from "./useHITLPolicies";

export function useHITLPoliciesSave(tenantId: string) {
  const qc = useQueryClient();
  return useMutation<HITLPolicyUpsertResponse, Error, HITLPolicyUpsertRequest>({
    mutationFn: (payload) => saveHITLPolicies(tenantId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: [...HITL_POLICIES_QUERY_KEY_BASE, tenantId],
      });
    },
  });
}
