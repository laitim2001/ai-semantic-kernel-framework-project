# Sprint 57.50 — TenantSettings Identity Fixture Cleanup (1-hr Single-Track Hygiene)

**Phase**: 57+ Frontend SaaS / Phase 58+ Backend Schema Extension (Identity sub-track)
**Goal**: Close `AD-TenantSettings-IdentityFixture-Cleanup` (Sprint 57.49 carryover) — migrate the 4 IDENTITY_FIXTURE fields (provider/scim/allowedDomains/mfa) from `_fixtures.ts` to a real backend endpoint following the Sprint 57.48 Track D RateLimits Option A fixture-projection precedent, plus drop the unused `SEATS_FIXTURE` per Sprint 57.49 `_fixtures.ts` comment "will remove in next cleanup pass".
**Branch**: `feature/sprint-57-50-tenant-settings-identity-fixture-cleanup`
**Class**: `medium-backend` 0.80 (5th data point — under new agent_factor sub-class table from Sprint 57.48 Option B activation)
**Sub-class**: `mechanical-single-domain` (single feature area: tenant-settings; pattern-reuse from Sprint 57.48 RateLimits Option A + Sprint 57.49 5-hook pattern) → **`agent_factor = 0.45`** (NEW sub-class table — **2nd validation**)
**Date**: 2026-05-26 (Sprint 57.49 closeout same-day continuation)
**Prior sprint reference**: Sprint 57.49 (5-tab migration; 1st validation @ ratio ~0.14) + Sprint 57.48 Track D RateLimits Option A fixture-projection + Sprint 57.47 MEMBERS pattern + Sprint 57.46 Tenant ORM extension

---

## 1. Sprint Goal

```
AS a platform admin viewing /tenant-settings General tab Identity & SSO section
I WANT the 4 Identity & SSO rows (Identity provider / SCIM / Allowed-domains / MFA)
   to display data fetched from a real backend endpoint (not hardcoded
   IDENTITY_FIXTURE constants) — using Sprint 57.48 Track D RateLimits Option A
   fixture-projection pattern (read-only DEFAULT_IDENTITY backend constant; defers
   full SSO admin schema to Phase 58+)
SO THAT (a) `_fixtures.ts` is purged of all remaining 5-tab-related fixtures
   (retain DANGER_OPS only — UI-only actions); (b) we generate the 2nd validation
   data point under the NEW `mechanical-single-domain` 0.45 sub-class agent_factor
   from Sprint 57.48 Option B activation; (c) future Phase 58+ SSO admin endpoint
   extension can land without frontend refactor (frontend already consumes the
   backend shape).
```

## 2. Background & Context

### 2.1 IDENTITY_FIXTURE current state (Sprint 57.49 carryover)

Per Sprint 57.49 closeout `_fixtures.ts` cleanup:
- 5 sections migrated to real backend (FF / Quotas / RateLimits / HITL / Members / GeneralFixture)
- `IDENTITY_FIXTURE` retained with comment "SCIM / Allowed-domains / MFA fields still pending backend (Phase 58+); SSO enabled status now from real `data.sso_enabled`"
- `SEATS_FIXTURE` retained with comment "will remove in next cleanup pass"
- `DANGER_OPS` retained as UI-only (intentional Phase 58+ destructive endpoint integration)

`IDENTITY_FIXTURE` shape (`frontend/src/features/tenant-settings/_fixtures.ts:56-61`):

```typescript
export const IDENTITY_FIXTURE = {
  provider: "SAML 2.0 · WorkOS",
  scim: "enabled",
  allowedDomains: "acme.com, acme.io",
  mfa: "required",
};
```

Consumed at 4 sites in `GeneralTab.tsx` (lines 141 / 145 / 149 / 153) — Identity provider Badge / SCIM Badge tone="success" / allowedDomains span.mono / MFA Badge tone="success".

### 2.2 Sprint 57.48 Track D RateLimits Option A fixture-projection precedent

Sprint 57.48 Track D shipped `GET /admin/tenants/{tenant_id}/rate-limits` returning fixture-projection from `tenants.meta_data` JSONB resolution with `DEFAULT_RATE_LIMITS` constant fallback. This pattern:
- 0 Alembic migration; 0 ORM column add
- Single new endpoint + Pydantic response model + DEFAULT_X constant
- Multi-tenant isolation via existing admin auth + tenant_id path param
- Defers full persistence (dedicated table + admin PATCH) to Phase 58.x (carryover AD `AD-TenantSettings-RateLimits-Persistence`)

Sprint 57.50 mirrors this pattern for Identity sub-resource:
- `GET /admin/tenants/{tenant_id}/identity` → `TenantIdentityResponse` (provider / scim_enabled / allowed_domains / mfa_required)
- `DEFAULT_IDENTITY` constant returned when `tenants.meta_data['identity']` is missing
- Frontend consumes via NEW TanStack Query hook + NEW service function

### 2.3 2nd validation under NEW sub-class `mechanical-single-domain` 0.45

Per Sprint 57.49 retro Q4 carryover `AD-AgentFactor-Sub-Class-Validation-Sprint-57.50`:
- 1st validation @ Sprint 57.49 ratio actual/committed-with-agent-factor **~0.14 BELOW band by 0.71** → KEEP single-data-point caution
- 2nd validation @ Sprint 57.50 (this sprint) needed; if also < 0.7 → escalate to tier-2 refinement (propose split `mechanical-pattern-reuse-heavy` 0.30 vs `mechanical-greenfield` 0.50)
- If ratio lands in [0.85, 1.20] band → validates new sub-class table → KEEP 0.45
- If > 1.20 → suggests 0.45 too aggressive for mechanical-single-domain → roll back to 0.65

**Sprint 57.50 work shape**: 1 backend endpoint (mechanical pattern reuse of Sprint 57.48 Track D RateLimits) + 1 frontend hook (mechanical pattern reuse of Sprint 57.49 5-hook pattern) + 1 GeneralTab refactor (4 Badge rows). Pure mechanical-single-domain ✅.

---

## 3. User Stories

### US-1: Backend `GET /admin/tenants/{tenant_id}/identity` endpoint

```
AS a frontend engineer consuming a tenant's identity & SSO configuration
I WANT a read-only backend endpoint returning the 4 Identity fields
   (provider / scim_enabled / allowed_domains / mfa_required) via Option A
   fixture-projection from `tenants.meta_data['identity']` JSONB with
   DEFAULT_IDENTITY constant fallback
SO THAT IDENTITY_FIXTURE can be removed from frontend; future SSO admin
   endpoint extension can replace the fixture-projection backend internally
   without changing the response contract or frontend hook.
```

**Acceptance**:
- NEW endpoint `GET /admin/tenants/{tenant_id}/identity` in `backend/src/api/v1/admin/tenants.py` (or new sub-router if pattern dictates)
- NEW Pydantic response model `TenantIdentityResponse` (provider: str / scim_enabled: bool / allowed_domains: list[str] / mfa_required: bool)
- NEW constant `DEFAULT_IDENTITY` in module (matching mockup fixture defaults: `SAML 2.0 · WorkOS` / `True` / `["acme.com", "acme.io"]` / `True`)
- Resolution logic: `tenants.meta_data['identity']` JSONB lookup; on miss → return DEFAULT_IDENTITY
- Admin auth gate (mirror existing `/feature-flags` / `/rate-limits` endpoints)
- Multi-tenant isolation: tenant_id path param + admin role enforced (cross-tenant access returns 403; **critical test required**)
- ≥4 NEW pytest tests (success path + 404 missing tenant + 403 cross-tenant + DEFAULT fallback when meta_data missing)

### US-2: Frontend hook + GeneralTab consumption

```
AS a platform admin viewing /tenant-settings General tab
I WANT the Identity & SSO section's 4 Badge rows to display data fetched from
   the Sprint 57.50 backend endpoint (not hardcoded IDENTITY_FIXTURE)
SO THAT the page reflects real tenant identity config; future SSO admin endpoint
   replacement is transparent to the frontend.
```

**Acceptance**:
- NEW service function `fetchTenantIdentity(tenant_id)` in `tenantSettingsService.ts`
- NEW TanStack Query hook `useTenantIdentity(tenant_id)` in `tenant-settings/hooks/`
- `GeneralTab.tsx` refactor: drop `IDENTITY_FIXTURE` import; consume hook data via `data` from `useTenantIdentity(tenantId)`
- Loading state placeholder (mirror Sprint 57.49 5-tab pattern — Card-level loading or row-level skeleton)
- Error state fallback (mirror Sprint 57.49 patterns)
- Optional shape adapter (if backend returns `scim_enabled: bool` but UI displays "enabled" string → adapter projects to UI-display string per Sprint 57.49 D-DAY0-1 pattern)
- ≥3 NEW Vitest tests covering hook + GeneralTab Identity section render with real data

### US-3: `_fixtures.ts` cleanup + validation + documentation

```
AS the parent AI assistant maintaining sprint workflow discipline
I WANT `_fixtures.ts` purged to retain DANGER_OPS only + clean validation sweep +
   retro + memory + 1 CHANGE record + sprint-workflow.md 2nd-validation entry
SO THAT Sprint 57.50+ has 2 data points to confirm/refine the NEW
   `mechanical-single-domain` 0.45 sub-class agent_factor.
```

**Acceptance**:
- `_fixtures.ts` shrinks: IDENTITY_FIXTURE removed; SEATS_FIXTURE removed (Sprint 57.49 follow-up); DANGER_OPS retained only with refreshed comment
- Standard validation chain: ESLint + tsc + Vitest + Vite build + V2 lints 9/9 preserved + pytest backend
- 1 CHANGE record `CHANGE-024-tenant-settings-identity-fixture-cleanup.md`
- retrospective.md Q1-Q7 with **2nd validation under `mechanical-single-domain` 0.45 sub-class** logged in Q4 (ratio + decision per rollback rule)
- sprint-workflow.md updates (file MHist + matrix MHist `medium-backend` 5th data point + §Active Activation history 2nd validation)
- `memory/project_phase57_50_*.md` subfile
- MEMORY.md pointer entry
- CLAUDE.md Current Sprint row + Last Updated footer (navigator-only)

---

## 4. Technical Specification

### 4.1 Backend pattern (Sprint 57.48 Track D RateLimits Option A mirror)

```python
# backend/src/api/v1/admin/tenants.py (or sub-module)

class TenantIdentityResponse(BaseModel):
    provider: str
    scim_enabled: bool
    allowed_domains: list[str]
    mfa_required: bool

DEFAULT_IDENTITY = {
    "provider": "SAML 2.0 · WorkOS",
    "scim_enabled": True,
    "allowed_domains": ["acme.com", "acme.io"],
    "mfa_required": True,
}

@router.get("/{tenant_id}/identity", response_model=TenantIdentityResponse)
async def get_tenant_identity(
    tenant_id: UUID,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantIdentityResponse:
    # Multi-tenant: admin can access any tenant; non-admin already 403 via dependency
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    identity_data = (tenant.meta_data or {}).get("identity") or DEFAULT_IDENTITY
    return TenantIdentityResponse(**identity_data)
```

### 4.2 Frontend pattern (Sprint 57.49 5-hook pattern reuse)

```typescript
// frontend/src/features/tenant-settings/services/tenantSettingsService.ts (extension)
export async function fetchTenantIdentity(tenantId: string): Promise<TenantIdentity> {
  const res = await fetchWithAuth(`/admin/tenants/${tenantId}/identity`);
  if (!res.ok) throw new ServiceError(...);
  return res.json();
}

// frontend/src/features/tenant-settings/hooks/useTenantIdentity.ts (NEW)
export function useTenantIdentity(tenantId: string | undefined) {
  return useQuery({
    queryKey: ['tenant-identity', tenantId],
    queryFn: () => fetchTenantIdentity(tenantId!),
    enabled: !!tenantId,
  });
}
```

### 4.3 GeneralTab.tsx refactor (4 Badge rows)

Adapter projection if needed (per Sprint 57.49 D-DAY0-1 pattern):
- Backend `scim_enabled: bool` → UI display: `scim_enabled ? "enabled" : "disabled"`
- Backend `allowed_domains: list[str]` → UI display: `.join(", ")`
- Backend `mfa_required: bool` → UI display: `mfa_required ? "required" : "optional"`

Adapter lives either (a) in the hook return projection or (b) inline in GeneralTab JSX. Decision at Day 0 三-prong.

### 4.4 No new DB schema; no Alembic migration

Pure Option A fixture-projection. Future Phase 58.x persistence model (dedicated `tenant_identity` table + admin PATCH endpoint) deferred — new carryover AD likely.

---

## 5. File Change List

### Backend
- `backend/src/api/v1/admin/tenants.py` (or new sub-module) — add `TenantIdentityResponse` + `DEFAULT_IDENTITY` + `GET /{tenant_id}/identity` endpoint
- `backend/tests/integration/api/test_admin_tenant_identity.py` (NEW) — 4-6 NEW pytest tests

### Frontend
- `frontend/src/features/tenant-settings/_fixtures.ts` — remove IDENTITY_FIXTURE + SEATS_FIXTURE; retain DANGER_OPS only with refreshed comment
- `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` — add `fetchTenantIdentity` function + `TenantIdentity` type
- `frontend/src/features/tenant-settings/hooks/useTenantIdentity.ts` (NEW) — TanStack Query hook
- `frontend/src/features/tenant-settings/components/tabs/GeneralTab.tsx` — drop `IDENTITY_FIXTURE` import; consume `useTenantIdentity(tenantId)`; update 4 Badge rows
- `frontend/src/features/tenant-settings/__tests__/useTenantIdentity.test.ts` (NEW) — 1-2 tests
- `frontend/src/features/tenant-settings/__tests__/GeneralTabIdentity.test.tsx` (NEW or extension) — 2-3 tests

### Documentation
- `claudedocs/4-changes/feature-changes/CHANGE-024-tenant-settings-identity-fixture-cleanup.md`

---

## 6. Workload

**Bottom-up est**: ~3.5 hr
- Backend endpoint + Pydantic + tests: ~1.5 hr
- Frontend hook + service + GeneralTab refactor + Vitest: ~1.5 hr
- Day 0 三-prong: ~0.3 hr
- Day 2 closeout: ~0.2 hr

**Class-calibrated commit** (`medium-backend` 0.80):
- 3.5 × 0.80 = **~2.8 hr committed**

**Agent-adjusted commit** (`agent_factor = 0.45` NEW sub-class `mechanical-single-domain`):
- 2.8 × 0.45 = **~1.3 hr agent-adjusted**

**4-segment form**:
> Bottom-up est ~3.5 hr → class-calibrated commit ~2.8 hr (mult 0.80) → agent-adjusted commit ~1.3 hr (`agent_factor` 0.45 — 2nd validation of NEW `mechanical-single-domain` sub-class)

**2nd validation prediction**:
- If sub-class table calibrated correctly → ratio ~0.85-1.20 (actual ~1.1-1.6 hr)
- If observed speedup ~24× (Sprint 57.49 pattern-reuse-heavy precedent) → actual ~0.15 hr → ratio ~0.12 → still below band; tier-2 refinement evidence ✅
- If observed speedup ~5-11× (Sprint 57.40-48 single-domain precedent) → actual ~0.3-0.7 hr → ratio ~0.23-0.54 → still below band but less so
- Mid-prediction: actual ~0.5-1 hr → ratio ~0.38-0.77 → lower edge of band or below

---

## 7. Acceptance Criteria

| # | Criterion | Verify |
|---|---|---|
| AC-1 | NEW backend endpoint `GET /{tenant_id}/identity` shipped + admin-gated | curl + pytest |
| AC-2 | NEW Pydantic `TenantIdentityResponse` + `DEFAULT_IDENTITY` constant | grep |
| AC-3 | Fixture-projection from `tenants.meta_data['identity']` with DEFAULT fallback | pytest test_default_fallback |
| AC-4 | NEW service func `fetchTenantIdentity` + hook `useTenantIdentity` | grep + Vitest |
| AC-5 | GeneralTab.tsx 4 Identity Badge rows consume hook data (no IDENTITY_FIXTURE import) | grep IDENTITY_FIXTURE in GeneralTab.tsx → 0 matches |
| AC-6 | `_fixtures.ts` retains DANGER_OPS only (IDENTITY_FIXTURE + SEATS_FIXTURE removed) | grep export const in _fixtures.ts → 1 match |
| AC-7 | ≥4 NEW pytest tests (success + 404 + 403 cross-tenant + DEFAULT fallback) | pytest count delta |
| AC-8 | ≥3 NEW Vitest tests | Vitest count delta |
| AC-9 | ESLint + tsc clean | exit 0 |
| AC-10 | Vite build successful (size delta ±2 KB acceptable) | npm run build |
| AC-11 | 9 V2 lints preserved (9/9 from Sprint 57.49) | run_all.py exit 0 |
| AC-12 | pytest backend full suite passing | exit 0 |
| AC-13 | 1 CHANGE record | ls |
| AC-14 | Day 0 三-prong report logged | Read progress.md |

---

## 8. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Existing `/{tenant_id}/feature-flags` or `/rate-limits` endpoint pattern doesn't match Sprint 57.48 retro Q4 description | Low-Medium | Day 0.8 Prong 2 read Sprint 57.48 Track D RateLimits route + Pydantic to confirm |
| `Tenant.meta_data` JSONB column doesn't exist (Sprint 57.48 Track D may have used different mechanism) | Medium | Day 0.8 Prong 2 read `Tenant` ORM model; if no meta_data field, fall back to hardcoded DEFAULT_IDENTITY without JSONB lookup |
| Frontend `tenant-settings/hooks/` directory doesn't follow Sprint 57.49 5-hook layout | Low | Day 0.8 Prong 1 + 2 confirm |
| GeneralTab.tsx has additional Identity-related logic beyond the 4 Badge rows | Low-Medium | Day 0.8 Prong 2.5 read GeneralTab.tsx full content |
| Adapter projection shape mismatch (backend bool vs UI string) | Medium | Day 0 D-DAY0-N: decide projection location (hook return vs inline JSX) and document |
| **2nd validation lands < 0.7 (predicted)** | High | Tier-2 refinement evidence (propose split `mechanical-pattern-reuse-heavy` 0.30 vs `mechanical-greenfield` 0.50); single-data-point accumulates into 2-consecutive trigger |
| **2nd validation lands > 1.20** | Low | Roll back `agent_factor` 0.45 → 0.65 (per rollback rule single-data-point caution) |
| Backend admin auth dependency name varies across endpoints | Low | Day 0.8 Prong 2 grep existing endpoint dependency imports |
| pytest test_admin_tenant_identity.py naming collides with existing test file | Low | Check during Prong 1 |
| Existing GeneralTab tests rely on IDENTITY_FIXTURE values | Medium | Day 0 Prong 2 grep IDENTITY_FIXTURE in `__tests__/`; update if found |

---

## 9. Carryover ADs (for Sprint 57.51+ pickup)

- `AD-AgentFactor-Sub-Class-Validation-Sprint-57.51` (3rd data point under new sub-class — only if Sprint 57.50 ratio lands < 0.7 OR > 1.20 single-data-point trigger)
- `AD-AgentFactor-Tier-2-Refinement-Activation` (escalate ONLY if Sprint 57.50 2nd validation also < 0.7; propose split mechanical-pattern-reuse-heavy 0.30 vs mechanical-greenfield 0.50)
- `AD-medium-frontend-Baseline-Recalibration` (Sprint 57.49 carryover continues; 3rd data point pending — Sprint 57.50 generates `medium-backend` 5th data point NOT medium-frontend; this AD continues to next medium-frontend sprint)
- `AD-Lint-Detector-Code-Aware-Masking-Rule` (Sprint 57.48 carryover — `.claude/rules/` codification; recommended as Sprint 57.51 scope per user direction)
- `AD-TenantSettings-Identity-Persistence-Phase58` (NEW from this sprint — full SSO admin schema: dedicated `tenant_identity` table + admin PATCH endpoint + audit chain WORM; Phase 58.x)
- `AD-MockupCapture-Frontend-Visual-Diff-Pipeline` (Phase 58+ deferred — carryover continues)
- `AD-TenantSettings-RateLimits-Persistence` (Phase 58.x deferred — carryover continues)
- Potential NEW from Sprint 57.50 Day 0.8

---

**Modification History**:
- 2026-05-26: Sprint 57.50 Day 0.1 — Initial draft (single-track Identity fixture cleanup; 2nd validation of NEW `mechanical-single-domain` 0.45 sub-class from Sprint 57.48 Option B activation + Sprint 57.49 1st validation)
