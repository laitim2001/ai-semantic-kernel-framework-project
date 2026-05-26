# Sprint 57.54 — HITLPolicies Admin Write Endpoint + Frontend Edit Mode (Phase 58.x WRITE side)

**Phase**: 57+ Frontend SaaS / Phase 58.x portfolio (HITLPolicies WRITE-side ship; backend admin upsert + frontend edit mode)
**Goal**: Ship the Phase 58.x WRITE side for HITLPolicies — close the existing BackendGapBanner copy ("policy edit API: backend extension Phase 58+") by adding `PUT /admin/tenants/{tenant_id}/hitl-policies` upsert endpoint + DBHITLPolicyStore.put() method + frontend HITLPoliciesTab edit mode + useHITLPoliciesSave mutation hook. This is a true `mechanical-greenfield` single NEW component-pair (one new endpoint + one new mutation hook + one tab edit-mode UI), feeding tier-3 sub-class `mechanical-greenfield` 0.50 1st validation data point per Sprint 57.52 retro Q4 SPLIT ACTIVATION.
**Branch**: `feature/sprint-57-54-hitl-policies-full-persistence`
**Class**: `medium-backend` 0.80 (6-data-point baseline: 55.5=1.14 + 55.6=0.92 + 57.47=0.16 + 57.48=0.11 + 57.50=0.27 + 57.53=0.83; 6-pt mean 0.57; KEEP per Sprint 57.50/57.53 retro `confound-resolved-by-sub-class-split` discipline — class baseline calibrates human-pace, agent residual captured at sub-class layer)
**Sub-class** (agent_factor): `mechanical-greenfield` 0.50 (**tier-3 1st validation** under NEW table effective Sprint 57.53+ per Sprint 57.52 retro Q4 tier-3 SPLIT ACTIVATION; closes Sprint 57.53 carryover `AD-AgentFactor-Tier-3-Validation-Sprint-57.54`)
**Agent-delegated** (per AD-Plan-Workload-AgentDelegation-Explicit-Field NEW from Sprint 57.53): **yes — backend + frontend via code-implementer agent delegation** (≥ 80% of Day 1 work; required to generate 1st validation data point under `mechanical-greenfield` 0.50)
**Date**: 2026-05-26 (Sprint 57.53 closeout same-day continuation; PR #203 still BLOCKED by GitHub Actions degraded_performance global outage; Sprint 57.54 branch from Sprint 57.53 tip `dc4c1680` per Path A)
**Prior sprint reference**: Sprint 57.53 (closeout 2026-05-26) carried `AD-AgentFactor-Tier-3-Validation-Sprint-57.54` as renamed Sprint 57.53 carryover (1st validation NOT generated in Sprint 57.53 due to parent-assistant-direct execution → `agent_factor = 1.0` per Sprint 57.45 Path B precedent; need agent-delegated sprint for `mechanical-greenfield` 0.50 1st validation data point).

---

## 1. Sprint Goal

```
AS the project maintainer of the Phase 58.x SaaS portfolio (HITLPolicies /
   FeatureFlags / Quotas / RateLimits / Identity persistence ADs) AND
   the V2 calibration matrix maintainer with `mechanical-greenfield` 0.50
   tier-3 sub-class table effective Sprint 57.53+ but ZERO validation
   data points so far
I WANT the HITLPolicies WRITE-side gap closed (PUT upsert endpoint +
   DBHITLPolicyStore.put() + Pydantic write schema + frontend edit mode +
   mutation hook + service func) — selected from Phase 58.x portfolio
   per user direction 2026-05-26 — executed via code-implementer agent
   delegation (backend track + frontend track sequential) such that the
   sprint generates the FIRST validation data point for `mechanical-
   greenfield` 0.50 sub-class baseline
SO THAT (a) Sprint 57.53 carryover `AD-AgentFactor-Tier-3-Validation-
   Sprint-57.54` is closed with a clean 1st validation data point under
   agent-delegated mode; (b) the existing BackendGapBanner copy ("policy
   edit API: backend extension Phase 58+") is softened to admit only the
   remaining gap (off-platform channel routing) which stays Phase 58+;
   (c) Sprint 57.49 frontend tab migration (read-only) is extended into
   full read+write parity matching the other 4 Sprint 57.48-49 tabs that
   already have edit-mode patterns (FeatureFlags/Quotas/Members) for
   future consistency; (d) `medium-backend` 0.80 class gets its 7th data
   point continuing post-confound-resolution tracking (per Sprint 57.50/
   57.53 retro discipline); (e) the AD-medium-frontend-Baseline-
   Recalibration Sprint 57.49 carryover gets its 3rd data point (Sprint
   57.13=0.95-1.0 / Sprint 57.49=0.064 / Sprint 57.54=TBD; confound
   resolved at tier-3 sub-class layer); (f) Phase 58.x portfolio
   progresses from 4 open ADs (HITLPolicies/FeatureFlags/Quotas/
   RateLimits-Backend-Persistence) to 3 open (HITLPolicies WRITE side
   closed; off-platform channel routing remains as separate deferred AD)
```

## 2. Background & Context

### 2.1 HITLPolicies baseline state (verified Sprint 57.54 Day 0 Prong 2 content verify at plan-drafting time)

**Sprint 57.54 Day 0 critical pivot finding**: The original plan framing ("Phase 58.x = NEW hitl_policies table + Alembic migration + ORM model") was **WRONG**. Plan-time grep + read of repo reality reveals:

- ✅ `backend/src/infrastructure/db/migrations/versions/0013_hitl_policies.py` (Sprint 55.3 / AD-Hitl-7) **already creates** `hitl_policies` table with 8 columns + UNIQUE (tenant_id) + 2 CHECK constraints + RLS policy `hitl_policies_tenant_isolation`
- ✅ `backend/src/infrastructure/db/models/governance.py::HitlPolicyRow` ORM model already exists
- ✅ `backend/src/platform_layer/governance/hitl/policy_store.py::DBHITLPolicyStore` exists as **READ-ONLY** (only `get(tenant_id) → HITLPolicy | None`; NO `put()` / `upsert()` / `delete()`)
- ✅ `backend/src/api/v1/admin/tenants.py` L666-791 (Sprint 57.48 Track A) already implements `GET /admin/tenants/{tenant_id}/hitl-policies` — projects composite `HITLPolicy` into list of per-RiskLevel `HITLPolicyItem` entries
- ✅ `frontend/src/features/tenant-settings/hooks/useHITLPolicies.ts` (Sprint 57.49) read hook with `HITL_POLICIES_QUERY_KEY_BASE`
- ✅ `frontend/src/features/tenant-settings/components/tabs/HITLPoliciesTab.tsx` (Sprint 57.49) reads + displays via the hook + `BackendGapBanner` copy: "Off-platform channel routing + policy edit API: backend extension Phase 58+"

**Actual Sprint 57.54 scope** = the WRITE side referenced explicitly in the existing BackendGapBanner copy:

### 2.2 True Phase 58.x gap for HITLPolicies

**Backend gaps** (Sprint 57.54 closes):
1. ❌ `DBHITLPolicyStore.put(tenant_id, policy)` upsert method
2. ❌ `PUT /admin/tenants/{tenant_id}/hitl-policies` admin endpoint
3. ❌ `HITLPolicyUpsertRequest` Pydantic write schema (composite shape)
4. ❌ Pytest tests covering upsert/multi-tenant isolation/invalid risk enum/RLS-enforced/idempotency

**Frontend gaps** (Sprint 57.54 closes):
1. ❌ `saveHITLPolicies(tenantId, payload)` service func
2. ❌ `useHITLPoliciesSave(tenantId)` TanStack mutation hook (with invalidation of `HITL_POLICIES_QUERY_KEY_BASE`)
3. ❌ `HITLPoliciesTab` edit-mode toggle (Edit/Cancel/Save buttons + per-row editable policy dropdown + sla_seconds input + reviewers input)
4. ❌ Vitest tests (mutation hook + tab edit mode)
5. ❌ BackendGapBanner copy soften (remove "policy edit API" — only off-platform channels remain Phase 58+)

**Deferred (REMAINS Phase 58+)**:
- ❌ Off-platform channel routing (Slack / email / SMS notification) — broader scope; NOT in this sprint
- ❌ Optimistic concurrency / If-Match (Sprint 57.50 Identity Phase 58.x precedent — also deferred)
- ❌ Audit log entry on policy change (track AD-Sprint-57.54-HITLPolicies-AuditLog if user requests separately)

### 2.3 Why `mechanical-greenfield` 0.50 1st validation (NOT pattern-reuse-heavy 0.30)

Per Sprint 57.50 retro Q4 ESCALATION decision + `sprint-workflow.md §Active Agent Delegation Factor Modifier` tier-2 sub-class table:

| Sub-class | Trigger | Sprint 57.54 fit? |
|-----------|---------|--------------------|
| `mechanical-pattern-reuse-heavy` 0.30 | ≥ 4 mechanical repetitions of same template in 1 sprint | ❌ Sprint 57.54 = 1 NEW endpoint pair + 1 NEW mutation hook + 1 tab edit mode (counts as 1 component-pair, not 4) |
| **`mechanical-greenfield` 0.50** | Single NEW component-pair; < 4 mechanical repetitions | ✅ MATCH |
| `mixed-multidomain-bundle-mechanical` 0.65 | 3+ independent tracks WITH mechanical pattern reuse | ❌ Sprint 57.54 = single HITLPolicies domain |
| `mixed-multidomain-bundle-non-mechanical` 1.0 | 3+ independent tracks; pure audit/docs/rules | ❌ |

**1st validation prediction**:
- If implementation lands cleanly (~45-75 min agent wall-clock) → ratio ~0.5-1.1 IN/BELOW band (single-data-point caution rule: KEEP 0.50 regardless of direction)
- If hits ≥ 1.20 → 1st rollback-trigger > 1.20 data point → KEEP per single-data-point rule
- If hits < 0.7 → 1st rollback-trigger < 0.7 data point → KEEP per single-data-point rule

Per Sprint 57.52 retro Q4 rollback rule: need 2 consecutive same-direction data points to trigger structural action. Sprint 57.54 1st validation alone → KEEP 0.50; flag for Sprint 57.55+ 2nd validation tracking via `AD-AgentFactor-Tier-3-Validation-Sprint-57.55`.

### 2.4 Pattern-reuse capture (Sprint 57.50 IDENTITY GET precedent — single-record/composite endpoint)

Sprint 57.50 IDENTITY_FIXTURE → real backend established the composite single-record pattern:
- `GET /admin/tenants/{tenant_id}/identity` returns single composite `TenantIdentityResponse`
- `useTenantIdentity(tenantId)` hook for single composite read
- GeneralTab Identity Card refactor via shape adapters

Sprint 57.54 mirrors the WRITE side using a similar single-composite shape (UNLIKE Sprint 57.48 Track A which projects composite → list for UI; the WRITE endpoint takes composite directly).

### 2.5 Sprint 57.53 carryover chain (`AD-AgentFactor-Tier-3-Validation-Sprint-57.54`)

- Sprint 57.52 retro Q4 (2026-05-26): tier-3 SPLIT ACTIVATED — `mixed-multidomain-bundle-mechanical` 0.65 + `mixed-multidomain-bundle-non-mechanical` 1.0
- Sprint 57.53 was first sprint under new tier-3 sub-class table effective Sprint 57.53+
- Sprint 57.53 Day 1 execution = parent-assistant-direct (0% code-implementer delegation) → per Sprint 57.45 Path B precedent `agent_factor = 1.0 (human)` applied → **`mechanical-greenfield` 0.50 1st validation NOT generated**
- Sprint 57.53 carryover renamed: `AD-AgentFactor-Tier-3-Validation-Sprint-57.53` → `AD-AgentFactor-Tier-3-Validation-Sprint-57.54`
- Sprint 57.54 = mandated agent-delegated mode to deliver the 1st validation data point

### 2.6 Class baseline tracking continuation

- `medium-backend` 0.80: Sprint 57.53 was 6th data point (ratio 0.83 in band lower edge, 6-pt mean 0.57); Sprint 57.54 = 7th data point continuing post-confound-resolution tracking
- `medium-frontend` 0.65: Sprint 57.49 was 2nd data point (ratio 0.064 — confound resolved by sub-class split); Sprint 57.54 frontend portion = 3rd data point (3-sprint window evaluation eligible if 57.55+ adds 4th from this class)

---

## 3. User Stories

### US-1: Backend WRITE side — PUT upsert endpoint + DBHITLPolicyStore.put()

```
AS the V2 backend developer extending the existing Sprint 57.48 HITLPolicies
   admin API surface (read-only) to support per-tenant policy override write
I WANT the WRITE side of `DBHITLPolicyStore` (NEW `put()` method) +
   `PUT /admin/tenants/{tenant_id}/hitl-policies` upsert endpoint +
   Pydantic `HITLPolicyUpsertRequest` write schema implemented + integration
   tests covering all critical paths (auth/404/upsert-create/upsert-update/
   multi-tenant isolation/invalid risk enum/RLS-enforced + idempotency)
SO THAT admin operators can configure per-tenant HITLPolicy overrides
   programmatically + the frontend HITLPoliciesTab can ship edit mode in
   US-2 without backend gap.
```

**Acceptance**:
- `DBHITLPolicyStore.put(tenant_id, policy)` async method implemented — uses `ON CONFLICT (tenant_id) DO UPDATE` upsert OR explicit `SELECT + UPDATE/INSERT` pattern; rotates `updated_at` server-side
- `HITLPolicyUpsertRequest` Pydantic model with composite shape (4 fields matching dataclass: `auto_approve_max_risk` / `require_approval_min_risk` / `reviewer_groups_by_risk` / `sla_seconds_by_risk`)
- `PUT /admin/tenants/{tenant_id}/hitl-policies` endpoint returns 200 OK with `HITLPolicyUpsertResponse` (echoes saved composite + projected `items` list matching GET shape)
- Endpoint uses `Depends(require_admin_platform_role)` (matches existing GET endpoint per `tenants.py:769`)
- Endpoint uses `_load_tenant_or_404` for 404 path consistency
- Pytest 10-12 NEW tests added in `backend/tests/integration/api/test_admin_tenant_hitl_policies.py` (extend existing file):
  - `test_put_requires_admin_role` (401/403)
  - `test_put_tenant_not_found` (404)
  - `test_put_creates_new_row` (200; no prior row)
  - `test_put_updates_existing_row` (200; prior row, fields change, `updated_at` rotates)
  - `test_put_response_projects_items_matching_get` (response.items echoes GET shape)
  - `test_put_invalid_risk_level` (422; e.g. `auto_approve_max_risk = "INVALID"`)
  - `test_put_multi_tenant_isolation` (tenant_b PUT does NOT affect tenant_a row)
  - `test_put_idempotent` (PUT twice same payload → same `updated_at` first time; rotates second time — verify behavior)
  - `test_put_rls_enforced` (direct SQL probe confirms RLS policy applies to written row)
- Pytest count delta: +10 to +12 (current 1760 PASS → 1770-1772 PASS); 0 fail; 0 skip change

### US-2: Frontend WRITE side — useHITLPoliciesSave + HITLPoliciesTab edit mode

```
AS the V2 frontend developer extending the Sprint 57.49 HITLPoliciesTab
   (read-only display) to support inline edit mode matching the 4 other
   Sprint 57.48-57.49 tabs (FeatureFlags/Quotas/Members already have edit
   patterns) for tenant-settings admin UX consistency
I WANT a NEW `useHITLPoliciesSave(tenantId)` TanStack mutation hook +
   `saveHITLPolicies` service func + edit-mode UI on HITLPoliciesTab
   (Edit/Cancel/Save buttons + per-row policy dropdown + sla_seconds input +
   reviewers input) + Vitest tests covering mutation success/error/cache
   invalidation
SO THAT the BackendGapBanner copy can be softened (only off-platform
   channel routing remains Phase 58+, edit API now real-backed).
```

**Acceptance**:
- `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` — NEW `saveHITLPolicies(tenantId, payload)` async func using `fetchWithAuth` PUT; matches existing `fetchTenantIdentity` / `fetchTenantMembers` patterns
- `frontend/src/features/tenant-settings/hooks/useHITLPoliciesSave.ts` — NEW TanStack `useMutation` hook with `onSuccess` invalidation of `HITL_POLICIES_QUERY_KEY_BASE` (re-fetches GET); error toast via existing pattern
- `frontend/src/features/tenant-settings/components/tabs/HITLPoliciesTab.tsx` — edit mode:
  - State: `editing: boolean` + `draft: HITLPolicyDraft` (composite shape mirroring write schema)
  - Edit button: top-right of Card, toggles `editing`
  - Edit form: 4-row table with per-RiskLevel rows (LOW/MEDIUM/HIGH/CRITICAL); each row has policy dropdown (auto/ask_once/always_ask) + sla_seconds input (number) + reviewers input (comma-separated string)
  - Save / Cancel buttons: Save calls mutation, Cancel reverts draft + exits edit mode
  - Success → exits edit mode + invalidates HITL_POLICIES_QUERY_KEY_BASE
  - Error → keeps form open + shows error message
  - **Mockup-fidelity discipline**: 0 NEW hex/oklch literals (reuse existing `--info`/`--warning`/`--success`/`--danger` tokens via `Badge` + buttons via `--btn-primary` pattern from existing tabs)
- BackendGapBanner copy update: from "Off-platform channel routing + policy edit API: backend extension Phase 58+ — risk/policy/SLA shown are tenant-effective" → "Off-platform channel routing (Slack/email/SMS): Phase 58+ — risk/policy/SLA shown are tenant-effective + editable via Edit button"
- Vitest 5-8 NEW tests added across:
  - `frontend/src/features/tenant-settings/hooks/__tests__/useHITLPoliciesSave.test.ts` (mutation success → invalidates QUERY_KEY / mutation error → propagates error)
  - `frontend/src/features/tenant-settings/components/tabs/__tests__/HITLPoliciesTab.test.tsx` (extend existing if any; new edit-mode tests)
  - `frontend/src/features/tenant-settings/services/__tests__/tenantSettingsService.test.ts` (extend; saveHITLPolicies PUT shape)
- Vitest count delta: +5 to +8 (current 607 PASS → 612-615 PASS); 0 fail; 0 skip change

### US-3: Sprint 57.50 retro Q3 Lesson 3 codification (CONDITIONAL on user-confirm)

Sprint 57.53 retro Q5 carried `AD-Plan-Workload-AgentDelegation-Explicit-Field` (codify sprint plan §6 pre-commit "agent-delegated: yes/no/partial/TBD-Day-1-decision" field). Sprint 57.54 plan §Workload **already explicitly fills this field** (= "yes — backend + frontend via code-implementer agent delegation").

**This sprint validates the codification value** (Plan-time agent-delegation explicit field) WITHOUT requiring a rule edit in this sprint. If validation succeeds (1st validation data point cleanly landed), Sprint 57.55+ can codify the rule into `sprint-workflow.md §Workload Calibration §Four-segment form when agent_factor applies` as MANDATORY field.

**Acceptance** (this sprint):
- Plan §Workload 4-segment form contains explicit "Agent-delegated: yes" line
- Day 1 retrospective Q2 records actual delegation mode (confirm `yes` vs reclassify `partial` if any track diverges)
- DO NOT edit `sprint-workflow.md` in this sprint (defer codification to Sprint 57.55+ after 1-2 more data points validate the explicit-field pattern works at plan time)

---

## 4. Technical Specification

### 4.1 Backend Track — DBHITLPolicyStore.put() method

**File**: `backend/src/platform_layer/governance/hitl/policy_store.py`

Pattern (mirror Sprint 57.48 Track A pattern + Sprint 57.50 single-record pattern; PostgreSQL `ON CONFLICT` upsert):

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

async def put(self, tenant_id: UUID, policy: HITLPolicy) -> HITLPolicy:
    """Upsert per-tenant HITLPolicy; returns the persisted policy.

    Uses PostgreSQL ON CONFLICT (tenant_id) DO UPDATE upsert for atomicity.
    The `updated_at` column rotates server-side via `func.now()`.
    """
    async with self._session_factory() as session:
        # Convert dict[RiskLevel, V] → dict[str, V] for JSONB storage
        reviewer_groups_jsonb = {
            k.value: v for k, v in policy.reviewer_groups_by_risk.items()
        }
        sla_seconds_jsonb = {
            k.value: v for k, v in policy.sla_seconds_by_risk.items()
        }
        stmt = (
            pg_insert(HitlPolicyRow)
            .values(
                tenant_id=tenant_id,
                auto_approve_max_risk=policy.auto_approve_max_risk.value,
                require_approval_min_risk=policy.require_approval_min_risk.value,
                reviewer_groups_by_risk=reviewer_groups_jsonb,
                sla_seconds_by_risk=sla_seconds_jsonb,
            )
            .on_conflict_do_update(
                index_elements=["tenant_id"],
                set_={
                    "auto_approve_max_risk": policy.auto_approve_max_risk.value,
                    "require_approval_min_risk": policy.require_approval_min_risk.value,
                    "reviewer_groups_by_risk": reviewer_groups_jsonb,
                    "sla_seconds_by_risk": sla_seconds_jsonb,
                    "updated_at": func.now(),
                },
            )
            .returning(HitlPolicyRow)
        )
        result = await session.execute(stmt)
        await session.commit()
        row = result.scalar_one()
        return _row_to_policy(row, tenant_id)
```

### 4.2 Backend Track — PUT endpoint in admin/tenants.py

**File**: `backend/src/api/v1/admin/tenants.py` (extend; ~30 lines added below line 791)

```python
class HITLPolicyUpsertRequest(BaseModel):
    """Composite HITLPolicy upsert payload (matches HITLPolicy dataclass shape)."""

    model_config = ConfigDict(extra="forbid")
    auto_approve_max_risk: str = Field(
        ...,
        description="RiskLevel name: LOW | MEDIUM | HIGH | CRITICAL",
    )
    require_approval_min_risk: str = Field(
        ...,
        description="RiskLevel name: LOW | MEDIUM | HIGH | CRITICAL",
    )
    reviewer_groups_by_risk: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Map RiskLevel name → list of reviewer group names",
    )
    sla_seconds_by_risk: dict[str, int] = Field(
        default_factory=dict,
        description="Map RiskLevel name → SLA seconds (positive int)",
    )

    @field_validator("auto_approve_max_risk", "require_approval_min_risk")
    @classmethod
    def _validate_risk_level(cls, v: str) -> str:
        if v not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError(f"Invalid RiskLevel: {v}")
        return v


class HITLPolicyUpsertResponse(BaseModel):
    """Echoes saved composite + projects items list for cache hydration."""

    saved_policy: HITLPolicyUpsertRequest
    items: list[HITLPolicyItem]


@router.put(
    "/{tenant_id}/hitl-policies",
    response_model=HITLPolicyUpsertResponse,
    dependencies=[Depends(require_admin_platform_role)],
)
async def upsert_tenant_hitl_policies(
    tenant_id: UUID,
    payload: HITLPolicyUpsertRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HITLPolicyUpsertResponse:
    """Upsert per-tenant HITLPolicy composite override.

    - 401/403 via require_admin_platform_role
    - 404 via _load_tenant_or_404
    - 200 with response.saved_policy + response.items (projected for cache hydration)
    """
    await _load_tenant_or_404(db, tenant_id)

    policy = HITLPolicy(
        tenant_id=tenant_id,
        auto_approve_max_risk=RiskLevel(payload.auto_approve_max_risk),
        require_approval_min_risk=RiskLevel(payload.require_approval_min_risk),
        reviewer_groups_by_risk={
            RiskLevel(k): v for k, v in payload.reviewer_groups_by_risk.items()
        },
        sla_seconds_by_risk={
            RiskLevel(k): v for k, v in payload.sla_seconds_by_risk.items()
        },
    )

    store = DBHITLPolicyStore(session_factory=_session_factory_from(db))
    saved = await store.put(tenant_id, policy)

    items = _project_hitl_policy_to_items(saved)
    return HITLPolicyUpsertResponse(saved_policy=payload, items=items)
```

### 4.3 Backend Track — Pytest tests

**File**: `backend/tests/integration/api/test_admin_tenant_hitl_policies.py` (extend existing)

Add 10-12 NEW tests after the existing GET tests (which already establish auth/404/multi-tenant patterns; reuse fixtures verbatim).

### 4.4 Frontend Track — Service func

**File**: `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` (extend)

```typescript
export interface HITLPolicyUpsertRequest {
  auto_approve_max_risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  require_approval_min_risk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  reviewer_groups_by_risk: Record<string, string[]>;
  sla_seconds_by_risk: Record<string, number>;
}

export interface HITLPolicyUpsertResponse {
  saved_policy: HITLPolicyUpsertRequest;
  items: HITLPolicyItem[];
}

export async function saveHITLPolicies(
  tenantId: string,
  payload: HITLPolicyUpsertRequest,
  signal?: AbortSignal
): Promise<HITLPolicyUpsertResponse> {
  return fetchWithAuth<HITLPolicyUpsertResponse>(
    `/api/v1/admin/tenants/${tenantId}/hitl-policies`,
    { method: "PUT", body: JSON.stringify(payload), signal }
  );
}
```

### 4.5 Frontend Track — Mutation hook

**File**: `frontend/src/features/tenant-settings/hooks/useHITLPoliciesSave.ts` (NEW)

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { saveHITLPolicies, HITLPolicyUpsertRequest, HITLPolicyUpsertResponse } from "../services/tenantSettingsService";
import { HITL_POLICIES_QUERY_KEY_BASE } from "./useHITLPolicies";

export function useHITLPoliciesSave(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<HITLPolicyUpsertResponse, Error, HITLPolicyUpsertRequest>({
    mutationFn: (payload) => saveHITLPolicies(tenantId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...HITL_POLICIES_QUERY_KEY_BASE, tenantId],
      });
    },
  });
}
```

### 4.6 Frontend Track — HITLPoliciesTab edit mode

**File**: `frontend/src/features/tenant-settings/components/tabs/HITLPoliciesTab.tsx` (edit)

Edit mode adds:
- State: `const [editing, setEditing] = useState(false); const [draft, setDraft] = useState<HITLPolicyDraft>(...);`
- Edit toggle button (top-right of Card header area)
- Form: 4-row editable table (LOW/MEDIUM/HIGH/CRITICAL) with policy dropdown + sla_seconds input + reviewers input
- Save → call mutation; Cancel → reset draft + exit
- BackendGapBanner copy soften

### 4.7 Verification

- `cd backend && pytest tests/integration/api/test_admin_tenant_hitl_policies.py -v` → all PASS (existing + 10-12 NEW)
- `cd backend && pytest --tb=short -q` → 1770-1772 PASS + 0 fail
- `cd backend && mypy --strict src/` → 0 errors
- `python scripts/lint/run_all.py` → 9/9 GREEN
- `cd frontend && npm run lint && npm run build` → exit 0 / 0 ESLint / 0 tsc errors
- `cd frontend && npm run test` → 612-615 PASS
- LLM SDK leak scan → 0

---

## 5. File Change List

### Backend (NEW + EDIT)
- **EDIT**: `backend/src/platform_layer/governance/hitl/policy_store.py` — add `put()` async method (~30 lines)
- **EDIT**: `backend/src/api/v1/admin/tenants.py` — add `HITLPolicyUpsertRequest` + `HITLPolicyUpsertResponse` + `upsert_tenant_hitl_policies` endpoint (~80 lines after existing GET)
- **EDIT**: `backend/tests/integration/api/test_admin_tenant_hitl_policies.py` — add 10-12 NEW PUT tests (~250 lines)

### Frontend (NEW + EDIT)
- **EDIT**: `frontend/src/features/tenant-settings/services/tenantSettingsService.ts` — add `saveHITLPolicies` service func + types (~30 lines)
- **NEW**: `frontend/src/features/tenant-settings/hooks/useHITLPoliciesSave.ts` — mutation hook (~25 lines)
- **EDIT**: `frontend/src/features/tenant-settings/components/tabs/HITLPoliciesTab.tsx` — add edit mode (~100 lines added; soften BackendGapBanner copy)
- **NEW**: `frontend/src/features/tenant-settings/hooks/__tests__/useHITLPoliciesSave.test.ts` — mutation hook Vitest tests (~70 lines)
- **EDIT**: `frontend/src/features/tenant-settings/components/tabs/__tests__/HITLPoliciesTab.test.tsx` — extend with edit-mode tests (~100 lines if file exists, else NEW)
- **EDIT**: `frontend/src/features/tenant-settings/services/__tests__/tenantSettingsService.test.ts` — extend with saveHITLPolicies test (~30 lines)

### Sprint artifacts (Day 0 + Day 2)
- `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-54-plan.md` (this file)
- `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-54-checklist.md`
- `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-54/progress.md`
- `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-54/retrospective.md`
- `memory/project_phase57_54_hitl_policies_write_endpoint.md`
- `memory/MEMORY.md` (pointer entry)
- `claudedocs/1-planning/next-phase-candidates.md` (Sprint 57.54 closeout note)
- `CLAUDE.md` (Current Sprint row + Last Updated footer)
- `.claude/rules/sprint-workflow.md` (matrix +1 row data point for `mechanical-greenfield` 0.50 1st validation + `medium-backend` 0.80 7th + §Active block 1st validation entry)
- `claudedocs/4-changes/feature-changes/CHANGE-024-hitl-policies-write-endpoint.md` (NEW — per CLAUDE.md `4-changes/` convention)

---

## 6. Workload

**Bottom-up est**: ~3.5 hr
- Day 0 三-prong (Prong 1 path verify on policy_store.py + admin tenants.py + frontend tab/hook/service paths; Prong 2 content verify on baseline ALREADY DONE in this plan §2.1; Prong 3 schema verify on hitl_policies table existing + RLS): ~0.3 hr
- Day 1 Backend track (DBHITLPolicyStore.put() + Pydantic + endpoint + ~10-12 pytest tests, agent-delegated via code-implementer): ~1.5 hr human-equivalent
- Day 1 Frontend track (service func + mutation hook + tab edit mode + ~5-8 Vitest tests + BackendGapBanner copy soften, agent-delegated via code-implementer): ~1.3 hr human-equivalent
- Day 2 closeout (progress + retro + memory + sprint-workflow.md matrix + CLAUDE.md + next-phase-candidates + CHANGE-024 + commit + PR): ~0.4 hr

**Class-calibrated commit** (`medium-backend` 0.80):
- 3.5 × 0.80 = **~2.8 hr committed (~168 min)**

**Agent-adjusted commit** (`agent_factor = 0.50` tier-3 `mechanical-greenfield` — **1st validation**):
- 2.8 × 0.50 = **~1.4 hr agent-adjusted (~84 min)**

**4-segment form**:
> Bottom-up est ~3.5 hr → class-calibrated commit ~2.8 hr (mult 0.80) → agent-adjusted commit ~1.4 hr (agent_factor 0.50 tier-3 `mechanical-greenfield` — **1st validation under NEW tier-3 table** effective Sprint 57.53+)
> **Agent-delegated**: **yes** — backend + frontend via code-implementer agent delegation (sequential: backend first, then frontend with backend types confirmed)

**1st validation prediction (tier-3 `mechanical-greenfield` 0.50)**:
- Single component-pair (1 backend endpoint + 1 frontend mutation hook + 1 tab edit-mode) cleanly scoped; agent-delegated pattern from Sprint 57.49-57.50 internalized (10th-11th consecutive frontend agent)
- Expected actual ~45-75 min wall-clock total (backend ~5-10 min agent + frontend ~5-10 min agent + supervisory ~10 min + Day 0 ~20 min + Day 2 closeout ~30 min)
- Predicted ratio actual/committed-with-agent-factor: **~0.5-1.0** (BELOW band lower edge or in band lower half)
- Per single-data-point caution rule (Sprint 57.52 retro Q4): regardless of direction (in band / below / above), KEEP 0.50; need 2 consecutive same-direction data points (< 0.7 OR > 1.20) to trigger structural action
- Sprint 57.55+ candidate target: 2nd validation under same 0.50 baseline (likely another single-track Phase 58.x persistence sprint: FeatureFlags/Quotas/RateLimits WRITE side using same pattern)

---

## 7. Acceptance Criteria

| # | Criterion | Verify |
|---|---|---|
| AC-1 | `DBHITLPolicyStore.put()` method implemented + unit covered | grep `async def put` in policy_store.py |
| AC-2 | `PUT /admin/tenants/{tenant_id}/hitl-policies` endpoint returns 200 OK with HITLPolicyUpsertResponse | grep `@router.put.*hitl-policies` in admin/tenants.py |
| AC-3 | Pydantic `HITLPolicyUpsertRequest` + `HITLPolicyUpsertResponse` declared + `extra="forbid"` set | grep models in admin/tenants.py |
| AC-4 | RiskLevel field_validator rejects invalid enum names | pytest `test_put_invalid_risk_level` |
| AC-5 | Multi-tenant isolation guarded (tenant_b PUT does not affect tenant_a row) | pytest `test_put_multi_tenant_isolation` |
| AC-6 | RLS policy applies to written rows (direct SQL probe) | pytest `test_put_rls_enforced` |
| AC-7 | Pytest count delta +10 to +12 | `pytest --tb=short -q` count = 1770-1772 |
| AC-8 | Full backend pytest baseline ALL-GREEN | `pytest --tb=short -q` 0 fail |
| AC-9 | mypy --strict 0 errors | `mypy --strict src/` |
| AC-10 | 9 V2 lints preserved | `python scripts/lint/run_all.py` exit 0 |
| AC-11 | LLM SDK leak 0 | covered by `run_all.py` |
| AC-12 | NEW `saveHITLPolicies` service func + `useHITLPoliciesSave` mutation hook implemented | grep files |
| AC-13 | HITLPoliciesTab edit-mode UI (Edit/Cancel/Save + per-row form) functional | manual smoke + Vitest tab tests |
| AC-14 | BackendGapBanner copy softened (remove "policy edit API"; only off-platform channels remain Phase 58+) | grep BackendGapBanner text |
| AC-15 | Vitest count delta +5 to +8 | `npm run test` count = 612-615 |
| AC-16 | Vite build clean | `npm run build` exit 0 |
| AC-17 | tsc strict 0 errors | covered by `npm run build` |
| AC-18 | ESLint 0 errors | `npm run lint` (NOT `--silent`; per AD-Pre-Push-Lint-Silent-Suppression-Anti-Pattern) |
| AC-19 | File MHist updated on edited files (≤100 char budget per AD-Lint-MHist-Verbosity) | grep MHist lines |
| AC-20 | Day 0 三-prong report logged with drift findings | Read progress.md Day 0 |
| AC-21 | retrospective.md Q1-Q6 with **1st validation `mechanical-greenfield` 0.50 ratio** in Q4 + agent-delegation confirmed in Q2 | grep Q2 + Q4 |
| AC-22 | sprint-workflow.md MHist + matrix `medium-backend` 0.80 7th data point + §Active block `mechanical-greenfield` 0.50 1st validation entry | grep |
| AC-23 | CHANGE-024-hitl-policies-write-endpoint.md created | Read claudedocs/4-changes/feature-changes/ |

---

## 8. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **`mechanical-greenfield` 0.50 1st validation lands > 1.20** | Medium | Rollback rule single-data-point caution: KEEP 0.50 + flag Sprint 57.55+ for 2nd validation; if 2 consecutive > 1.20 → propose 0.50 → 0.65 lift in Sprint 57.55 retro Q4 |
| **`mechanical-greenfield` 0.50 1st validation lands < 0.7** | High (Sprint 57.40-44 + 57.46-50 evidence of agent speedup undershooting) | Rollback rule single-data-point caution: KEEP 0.50 + flag Sprint 57.55+ for 2nd validation; if 2 consecutive < 0.7 → propose tier-4 refinement (extreme-mechanical sub-class 0.30) |
| ON CONFLICT clause syntax error (pg dialect-specific) | Low | Reference `pg_insert` import from `sqlalchemy.dialects.postgresql`; existing precedent in repo (per Sprint 57.48 Track A `_session_factory_from`) |
| HITLPolicy dataclass shape divergence between read projection (4 items per RiskLevel) and write composite (1 row) | Low (verified §2.1 Prong 2: Sprint 57.48 already projects composite → list; same composite is the write shape) | §4.2 explicitly defines HITLPolicyUpsertResponse to echo both composite + projected items for cache hydration consistency |
| Frontend edit-mode form draft state divergence on tenant switch | Medium | Use `[editing, draft]` state-pair; reset both on `tenantId` change via `useEffect` |
| Off-platform channel routing field gap in payload (only 4 dataclass fields) | Low | Off-platform channels = Phase 58+ separate AD; NOT in this sprint's write schema |
| RLS policy on hitl_policies table requires `app.tenant_id` setting from middleware | Low (verified §2.1 Prong 3: existing 0013 migration RLS already in place + Sprint 57.48 GET endpoint works without RLS issue) | Endpoint reuses same `_session_factory_from(db)` pattern; RLS continues to work |
| Frontend HITLPoliciesTab.test.tsx may not exist yet (Vitest spec) | Low | Plan §5 file change list marks `.test.tsx` as "extend if exists, else NEW"; verify Day 0 Prong 1 path check |
| Pydantic Field validator pattern may need `mode="before"` or `mode="after"` clarification | Low | Default `@field_validator` uses `mode="after"` (validates after type coercion); appropriate for enum string check |
| Vitest mutation test setup requires QueryClient wrapper | Low | Existing precedent in repo (per Sprint 57.49 `useFeatureFlagsSave` similar mutation hook tests if exists; check Day 0 Prong 2) |
| Agent delegation 2 sequential agents (backend then frontend) may add overhead vs 1 single | Low | Standard pattern (Sprint 57.49/57.50 precedent); type contract handoff between tracks: backend Pydantic shape → frontend TypeScript shape duplicated once, then frontend agent reads backend types from spec |
| BackendGapBanner copy change may break Vitest snapshot tests | Low | Grep existing snapshot tests for HITLPoliciesTab copy assertions Day 0 Prong 2; update if any |
| `medium-backend` 0.80 7th data point continues post-confound tracking | Low | Per Sprint 57.50/57.53 retro: 7th data point feeds matrix for tracking; no class adjustment unless 3-sprint window pattern emerges |
| `medium-frontend` 0.65 3rd data point | Low (post-confound) | 3-sprint window evaluation eligible after Sprint 57.55+ adds 4th data point from this class |

---

## 9. Carryover ADs (for Sprint 57.55+ pickup)

- **`AD-AgentFactor-Tier-3-Validation-Sprint-57.55`** (NEW — 2nd validation under `mechanical-greenfield` 0.50 needed for rollback/lift decision; pending direction-of-drift from Sprint 57.54 1st data point)
- **`AD-Plan-Workload-AgentDelegation-Explicit-Field-Codification`** (Sprint 57.53 carryover continues — if Sprint 57.54 1st validation cleanly lands → propose codification to `sprint-workflow.md §Workload Calibration §Four-segment form` as MANDATORY field; if hits > 1.20 → defer codification until 2nd data point validates pattern)
- **`AD-HITLPolicies-OffPlatformChannelRouting`** (NEW — Phase 58+ deeper extension; Slack/email/SMS notification routing config storage; out of Sprint 57.54 scope)
- **`AD-HITLPolicies-OptimisticConcurrency`** (CONDITIONAL — if Day 1 surfaces concurrent edit race conditions; Phase 58+ If-Match header pattern)
- **`AD-HITLPolicies-AuditLogOnChange`** (CONDITIONAL — if user requests audit_log entry on policy change; Phase 58+ similar to Sprint 57.x audit chain integration)
- **`AD-TenantSettings-{FeatureFlags,Quotas,RateLimits}-Write-Endpoint`** (Phase 58.x portfolio continues; 3 ADs remaining — same mechanical-greenfield pattern as Sprint 57.54 HITLPolicies; if Sprint 57.55+ picks one → 2nd validation candidate for `mechanical-greenfield` 0.50)
- **`AD-TenantSettings-Identity-Persistence-Phase58`** (Sprint 57.50 carryover continues; full SSO admin schema; broader scope than mechanical-greenfield)
- **`AD-Test-Cleanup-Pattern-Shared-Helper`** (Sprint 57.53 carryover continues; Phase 58.x — extract `_clear_committed_test_tenants` to shared helper)
- **`AD-MediumBackend-AICadence-Recalibration`** (Sprint 57.53 carryover continues; Phase 58+ — revisit `medium-backend` 0.80 if next 2-3 human-factor sprints continue at 0.70-0.85)
- **`AD-MockupCapture-Frontend-Visual-Diff-Pipeline`** (Phase 58+ deferred)
- Potential NEW from Sprint 57.54 Day 0 三-prong findings

---

**Modification History**:
- 2026-05-26: Sprint 57.54 Day 0.1 — Initial draft (HITLPolicies WRITE side Phase 58.x ship; corrected scope after Day 0 探勘 Prong 2 reveals table + ORM + RLS + read-only DBHITLPolicyStore.get + GET endpoint + frontend read hook all ALREADY exist; true gap = WRITE side (put method + PUT endpoint + edit mode + mutation hook); `mechanical-greenfield` 0.50 tier-3 1st validation under NEW sub-class table effective Sprint 57.53+; agent-delegated yes via code-implementer; closes Sprint 57.53 carryover AD-AgentFactor-Tier-3-Validation-Sprint-57.54)
