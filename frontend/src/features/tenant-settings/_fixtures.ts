/**
 * File: frontend/src/features/tenant-settings/_fixtures.ts
 * Purpose: Mockup fixtures for tabs NOT yet wired to backend (post Sprint 57.49 migration).
 * Category: Frontend / tenant-settings / fixtures
 * Scope: Phase 57 / Sprint 57.44 Day 1 (initial verbatim port) → Sprint 57.49 Day 1 (5-section cleanup)
 *
 * Description:
 *   Sprint 57.44 initial: ported the entire mockup 6-tab fixture set from
 *   `page-admin.jsx:411-621` because backend TenantResponse only exposed 10
 *   baseline fields.
 *
 *   Sprint 57.46/47/48 backend extensions + Sprint 57.49 frontend migration
 *   wave removed 5 fixture sections (FEATURE_FLAGS / QUOTAS / RATE_LIMITS /
 *   HITL_POLICIES / MEMBERS + GENERAL_FIXTURE) — all real-data backed now.
 *
 *   Retained fixtures:
 *   - IDENTITY_FIXTURE — SCIM / Allowed-domains / MFA fields still pending
 *     backend (Phase 58+); SSO enabled status now from real `data.sso_enabled`
 *   - DANGER_OPS — UI-only actions (Suspend / Rotate / Tombstone / Delete);
 *     destructive endpoint integration is intentional Phase 58+ scope
 *   - SEATS_FIXTURE — kept for backward-compat but unused after Sprint 57.49
 *     (GeneralTab now uses `data.seats`); will remove in next cleanup pass
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1)
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — drop 5 migrated sections (FF/Quotas/RateLimits/HITL/Members/General)
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1) — verbatim mockup port for 6-tab rebuild
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx L548-551 (IDENTITY_FIXTURE)
 *   - reference/design-mockups/page-admin.jsx L606-610 (DANGER_OPS)
 *   - ./components/tabs/GeneralTab.tsx (IDENTITY_FIXTURE consumer)
 *   - ./components/tabs/DangerZoneTab.tsx (DANGER_OPS consumer)
 */

export interface DangerOp {
  k: string;
  v: string;
  btn: string;
}

export const DANGER_OPS: DangerOp[] = [
  { k: "Suspend tenant", v: "Block all new sessions and tool calls. Existing sessions complete.", btn: "Suspend" },
  { k: "Rotate all API keys", v: "Invalidate every active key. Operators must re-issue.", btn: "Rotate" },
  { k: "Tombstone all PII", v: "GDPR Art. 17. Memory entries marked subject-erased; audit chain preserves hashes.", btn: "Tombstone" },
  { k: "Delete tenant", v: "Permanent. Cannot be undone. WORM audit retained 7 years per compliance.", btn: "Delete" },
];

/**
 * Identity & SSO mockup defaults — Provider type / SCIM / Allowed-domains / MFA
 * remain fixture pending Phase 58+ SSO admin endpoint. SSO enabled status now
 * uses real `data.sso_enabled` field (Sprint 57.46).
 */
export const IDENTITY_FIXTURE = {
  provider: "SAML 2.0 · WorkOS",
  scim: "enabled",
  allowedDomains: "acme.com, acme.io",
  mfa: "required",
};
