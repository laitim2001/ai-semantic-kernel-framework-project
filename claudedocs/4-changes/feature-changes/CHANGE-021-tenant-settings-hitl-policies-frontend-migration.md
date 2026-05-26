# CHANGE-021: HITLPoliciesTab — fixture → useHITLPolicies real backend

**Date**: 2026-05-26
**Sprint**: 57.49 Day 1 (Track A 1.1.4)
**Scope**: Frontend / tenant-settings / HITLPoliciesTab

## Problem

HITLPoliciesTab consumed `HITL_POLICIES` (4 hard-coded risk-tier rows) fixture. Sprint 57.48 Track A shipped `/admin/tenants/{id}/hitl-policies` endpoint projecting composite policy → per-RiskLevel list.

## Solution

- NEW `useHITLPolicies(tenantId)` hook + `fetchHITLPolicies` service func
- `HITLPoliciesTab` accepts `tenantId: string` prop; consumes hook
- Adapter:
  - Backend `risk` enum (`"LOW"|"MEDIUM"|"HIGH"|"CRITICAL"`) → lowercase for `.sev-${level}` CSS class match
  - Backend `sla_seconds: number | null` → `formatSla` helper renders `Ns`/`Nm`/`Nh` (mockup fixture pre-formatted "5m" reconstructed)
  - Mockup `off: string[]` (off-platform channels) NOT in backend yet — render `<span className="subtle">—</span>` placeholder
  - Empty list state: "No HITL policy override configured. Platform defaults apply."

## Verification

- `useSubResourceHooks.test.tsx` covers QUERY_KEY_BASE + 4-row projection
- ESLint + tsc clean

## Impact

Frontend now shows real per-tenant HITL policy from `DBHITLPolicyStore`. Off-platform routing channels Phase 58+ when backend wire lands.
