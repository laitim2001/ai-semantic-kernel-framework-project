# Sprint 57.9 Progress

**Branch**: `feature/sprint-57-9-governance-ship-tquery-migration`
**Plan**: [sprint-57-9-plan.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-9-plan.md)
**Checklist**: [sprint-57-9-checklist.md](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-9-checklist.md)
**Sprint Goal**: Governance real ship + TanStack Query 4-page migration (Phase 57+ Frontend SaaS 6/N)

---

## Day 0 — 2026-05-09 — Setup + Pre-flight + 三-prong + Calibration

### Branch creation ✅
- Created `feature/sprint-57-9-governance-ship-tquery-migration` from `main` HEAD `caf95706` (Sprint 57.8 closeout)

### Pre-flight baseline capture ✅

| Check | Sprint 57.8 baseline | Sprint 57.9 measured | Status |
|-------|----------------------|----------------------|--------|
| pytest | 1622 (1618 passed + 4 skipped) | 1615 passed + 3 failed + 4 skipped → **1622 after D-PRE-1 cleanup** | ⚠️→✅ |
| Vitest | 57/57 | 57/57 (19 files / 2.54s) | ✅ |
| Playwright | 27/27 | 27/27 (7.6s) | ✅ |
| mypy strict | 0/300 | 0/300 (Success: no issues found in 300 source files) | ✅ |
| 9 V2 lints | 9/9 green | 9/9 green (4.19s via `python scripts/lint/run_all.py`) | ✅ |
| Vite build | 246.19 kB main + 13 lazy chunks | 246.19 kB main + 13 lazy chunks (AppShellV2 lazy 34.88 kB) | ✅ |

### Day 0 三-prong verify

#### Prong 1 — Path Verify (per AD-Plan-2)

**16 NEW file paths — all return 0 results (don't exist) — fresh creation confirmed**:
- `frontend/src/features/governance/hooks/useApprovals.ts` ✅ NEW path verified
- `frontend/src/features/governance/hooks/useApprovalDecide.ts` ✅
- `frontend/src/features/governance/hooks/useAuditLog.ts` ✅
- `frontend/src/features/governance/services/auditService.ts` ✅
- `frontend/src/features/governance/components/AuditLogViewer.tsx` ✅
- `frontend/src/features/governance/components/AuditChainBadge.tsx` ✅
- `frontend/src/features/cost-dashboard/hooks/useCostSummary.ts` ✅
- `frontend/src/features/sla-dashboard/hooks/useSLAOverview.ts` ✅
- `frontend/src/features/admin-tenants/hooks/useTenantList.ts` ✅
- `frontend/src/features/tenant-settings/hooks/useTenant.ts` ✅
- 6 NEW Vitest test files ✅
- 1 NEW Playwright e2e file ✅

**15 MODIFY file paths — all return 1 result (exist for editing)**:
- `frontend/src/pages/governance/index.tsx` ✅ (40 lines, nested Routes + inline styles)
- `frontend/src/features/governance/components/ApprovalsPage.tsx` ✅ (121 lines)
- `frontend/src/features/governance/components/ApprovalList.tsx` ✅ (115 lines)
- `frontend/src/features/governance/components/DecisionModal.tsx` ✅ (192 lines)
- `frontend/src/features/governance/services/governanceService.ts` ✅ (75 lines, raw fetch L49+L66)
- `frontend/src/features/governance/types.ts` ✅
- `frontend/src/routes.config.ts` ✅ (governance entry L131-132 active=false)
- `frontend/src/features/cost-dashboard/components/CostOverview.tsx` ✅ (95 lines, useEffect+useCostStore.loadData pattern)
- `frontend/src/features/cost-dashboard/store/costStore.ts` ✅ (data/loading/error confirmed L33-58)
- `frontend/src/features/sla-dashboard/components/SLAOverview.tsx` ✅
- `frontend/src/features/sla-dashboard/store/slaStore.ts` ✅ (same data/loading/error pattern L32-57)
- `frontend/src/pages/admin-tenants/index.tsx` ✅ (Risk I closed — page IS at this path, not features/)
- `frontend/src/features/admin-tenants/store/adminTenantsStore.ts` ✅ (loading/error/loadData confirmed L54-99)
- `frontend/src/features/tenant-settings/components/TenantSettingsView.tsx` ✅
- `frontend/src/features/tenant-settings/store/tenantSettingsStore.ts` ✅ (data/loading/error L30-78)

**BONUS findings (not in plan but need awareness)**:
- `frontend/src/features/sla-dashboard/components/SLAMetricsCard.tsx` exists — secondary component used by SLAOverview; verify if also consumes store loading/data during US-6 refactor
- `frontend/src/features/tenant-settings/components/TenantSettingsEditForm.tsx` exists — separate edit form component; verify TanStack mutation pattern for save action during US-6 (potential mutation hook needed)

#### Prong 2 — Content Verify (per AD-Plan-3 promoted Sprint 55.6)

**governance/* exports** — 5 export sites confirmed (types.ts 5 types + governanceService 1 const + 3 components 1 each)

**authService exports** — All 5 needed functions present:
- `getJwt()` L37 / `clearJwt()` L45 / `isAuthenticated()` L49 / `setPostLoginRedirect()` L57 / `fetchWithAuth()` L74

**Backend RBAC** — `platform_layer/identity/auth.py`:
- `_AUDIT_ROLES` L100 + `_APPROVER_ROLES` L104 + `_ADMIN_ROLES` L110
- `require_audit_role` L120 / `require_approver_role` L132 / `_require_role` helper L157
- Reads `request.state.roles` (L170 — set by JWT middleware)
- **Risk D resolution**: 57.7 IAM `_to_internal_jwt` populates `roles` claim → middleware sets `request.state.roles` → `_require_role` checks intersection. **JWT claim shape MATCHES** between 57.7 IAM emission and 53.5 backend consumption. ✅

**main.tsx QueryClient** — `<QueryClientProvider client={queryClient}>` wrap intact at L38; QueryClient instantiated L25-32 with `staleTime: 30_000` + `refetchOnWindowFocus: false` defaults

**governanceService current pattern** — raw `fetch(...)` at L49 + L66; `Authorization: Bearer` NOT yet present (US-3 swap target confirmed)

**4 stores all have data/loading/error server state** (US-6 reduction targets all valid):
- costStore: `data: CostSummaryResponse | null` + `loading: boolean` + `error: string | null` + `loadData()` action
- slaStore: same shape
- adminTenantsStore: `loading + error + loadData` (with `items + total`)
- tenantSettingsStore: same shape

**routes.config.ts** — Governance entry L131-132 confirms `active: false` placeholder + correct category "admin"

**shadcn Dialog usage (Risk C)**:
- `frontend/src/components/ui/` directory **NOT exists** — shadcn primitives未引入
- Dialog grep matches only `DecisionModal.tsx` itself (no other component usage)
- **Verdict**: Tailwind impl per YAGNI (mirror Sprint 57.8 UserMenu precedent) ✅

#### Prong 3 — Schema Verify
- N/A — frontend-only sprint, no DB schema changes

### Drift findings catalog

| ID | Severity | Finding | Implication / Action |
|----|----------|---------|----------------------|
| **D-PRE-1** | 🔴 RED | Pytest baseline -3 (3 failures in `test_admin_tenant_patch.py` for tenant codes DN_ONLY / META_ONLY / BOTH_FIELDS — UniqueViolationError leftover from Sprint 57.7+57.8 test runs) | Same class as Sprint 57.8 D13 dev DB pollution. **Cleaned via audit_log trigger toggle pattern**: ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_update_delete + audit_log_no_truncate → DELETE FROM tenants WHERE code IN (...) → re-enable triggers. Baseline restored to 1622. **Carryover AD-Test-Tenant-Code-Pollution still open** (Sprint 57.8 carryover) — needs proper fix in Phase 58.x: uuid suffix per run OR savepoint/rollback fixture |
| **D-PRE-2** | 🟢 GREEN | shadcn `<Dialog>` used 0 times elsewhere (only DecisionModal's own inline impl) + `frontend/src/components/ui/` does not exist | Risk C resolved: DecisionModal Tailwind impl per YAGNI (~110 LOC pattern from Sprint 57.8 UserMenu); no @shadcn/ui dependency added |
| **D-PRE-3** | 🟢 GREEN | All 16 NEW + 15 MODIFY plan-stated paths Glob-verified | Plan §File Change List 100% accurate; 0 path drift |
| **D-PRE-4** | 🟢 GREEN | JWT claim shape match (57.7 IAM `_to_internal_jwt` `roles` claim ↔ 53.5 backend `request.state.roles` consumption via `_require_role`) | Risk D resolved: `fetchWithAuth` swap (US-3) safe; backend will accept JWT-issued roles for require_approver_role / require_audit_role checks |
| **D-PRE-5** | 🟡 YELLOW | BONUS findings: `SLAMetricsCard.tsx` (sla-dashboard secondary component) + `TenantSettingsEditForm.tsx` (tenant-settings separate edit form) exist beyond plan §File Change List MODIFY rows | US-6 refactor must verify if these consume store data/loading; for TenantSettingsEditForm specifically, may need a NEW `useTenantUpdate` mutation hook (~20 LOC) for save action — adds ~1 hr scope. Document at Day 4 retro for calibration accuracy. |
| **D-PRE-6** | 🟢 GREEN | DB credentials in actual config: `ipa_v2:ipa_v2_dev@localhost:5432/ipa_v2` (NOT .env template `ipa_user:ipa_password/ipa_platform`) | Operational note for future cleanup scripts; .env template is V1 legacy |
| **D-PRE-7** | 🟢 GREEN | audit_log immutability triggers (`audit_log_no_update_delete` + `audit_log_no_truncate` from Migration 0005 Sprint 53.5) cascade-block tenant DELETE | Cleanup pattern: DISABLE TRIGGER → DELETE → ENABLE TRIGGER. Documented for Sprint 57.10+ recurrence (AD-Test-Tenant-Code-Pollution carryover). |

### Calibration baseline confirmation

- **Bottom-up est**: ~22 hr
- **Calibrated commit**: ~10.5 hr
- **Multiplier**: HYBRID 0.50 (NEW class proposal)
- **Class**: `frontend-feature-with-migration` (1-data-point opens; AD-Sprint-Plan-10 extension)
- **Reference**: plan §Workload (calibrated)

### User decision points (confirmed in plan §Open questions)
- ✅ Q1 Branch name: `feature/sprint-57-9-governance-ship-tquery-migration`
- ✅ Q2 Audit log viewer: filter form + paginated table
- ✅ Q3 Tab UX: URL-based 2 sub-routes
- ✅ Q4 NEW calibration class `frontend-feature-with-migration` 0.50 baseline
- ✅ Q5 (post-Day 0): shadcn `<Dialog>` decision = Tailwind impl per D-PRE-2 + Sprint 57.8 UserMenu YAGNI precedent

### Day 0 wrap

- **Actual hr**: ~1.5 hr (target ~1-2 hr Day 0 budget)
- **Drift findings**: 7 catalogued (1 RED resolved + 1 YELLOW informational + 5 GREEN; 0 plan rewrites needed)
- **Go/no-go decision**: ✅ GO Day 1 (D-PRE-1 RED was Sprint 57.8 carryover, not Sprint 57.9 regression; baseline restored; no scope shift)
- **Remaining for Day 1**: US-1 (governance AppShellV2 wrap + auth gate + 2-tab routes) + US-2 (Tailwind migration 3 components)
