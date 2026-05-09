# Sprint 57.9 — Checklist (Governance Real Ship + TanStack Query 4-page Migration)

[Plan link](./sprint-57-9-plan.md)

> Format mirror: Sprint 57.8 checklist (Day 0-4, 5 days, ~388 lines). Per
> `.claude/rules/sprint-workflow.md` §Step 2: same Day count, same per-task detail
> depth (3-6 sub-bullets each with DoD / Verify command), same closing 重要備註.

---

## Day 0 — Setup + Branch + Pre-flight + 三-prong + Calibration

### 0.1 Branch creation
- [x] **Create feature branch** ✅
  - DoD: `feature/sprint-57-9-governance-ship-tquery-migration` from latest main `caf95706`
  - Command: `git checkout main && git pull && git checkout -b feature/sprint-57-9-governance-ship-tquery-migration`
  - Verify: `git branch --show-current` matches ✅

### 0.2 Pre-flight baseline capture
- [x] **pytest baseline** ✅ post D-PRE-1 cleanup
  - DoD: full suite pass count = 1622 (Sprint 57.8 baseline; 1618 passed + 4 skipped) — **post-cleanup matches** (initial -3 D13-class pollution)
- [x] **Vitest baseline** ✅
  - DoD: 57/57 (19 files / 2.54s) — matches
- [x] **Playwright baseline** ✅
  - DoD: 27/27 (7.6s) — matches
- [x] **mypy + lint baseline** ✅
  - mypy: 0/300 source files — matches
  - 9 V2 lints: 9/9 green (4.19s via `python scripts/lint/run_all.py`)
- [x] **Vite bundle baseline** ✅
  - 246.19 kB main + 13 lazy chunks (AppShellV2 lazy 34.88 kB) — matches

### 0.3 Day 0 三-prong verify (per AD-Plan-1+3+4 promoted rules)

**Prong 1 — Path Verify (per AD-Plan-2)**
- [ ] **Glob/ls every NEW file path in plan §File Change List**
  - DoD: 16 NEW files all return 0 results (don't exist yet) — confirm fresh creation
  - Sample: `ls frontend/src/features/governance/hooks/useApprovals.ts 2>&1 | head -1` (expect "No such file")
  - Sample: `ls frontend/src/features/cost-dashboard/hooks/useCostSummary.ts 2>&1 | head -1`
- [ ] **Glob/ls every MODIFY file path**
  - DoD: 15 MODIFY files all return 1 result (exist for editing)
  - Sample: `ls frontend/src/pages/governance/index.tsx frontend/src/features/governance/services/governanceService.ts 2>&1`
- [ ] **Verify admin-tenants page actual file location (Risk I)**
  - DoD: identify the canonical file holding admin-tenants list/filter/pagination (could be `pages/admin-tenants/index.tsx` OR `features/admin-tenants/components/AdminTenantsPage.tsx`)
  - Command: `find frontend/src -path "*admin-tenants*" -name "*.tsx" | head -10`
  - Document path in plan §File Change List MODIFY row "TBD via Day 0"

**Prong 2 — Content Verify (per AD-Plan-3 promoted Sprint 55.6)**
- [ ] **Grep `features/governance/` 5 existing files actually export expected names**
  - DoD: ApprovalsPage / ApprovalList / DecisionModal / governanceService all grep-found
  - Command: `grep -rn "^export " frontend/src/features/governance/ | head -10`
- [ ] **Grep `authService` exports `isAuthenticated` + `setPostLoginRedirect` + `fetchWithAuth`**
  - DoD: all 3 function signatures grep-found in `frontend/src/features/auth/services/authService.ts`
  - Command: `grep -n "isAuthenticated\|setPostLoginRedirect\|fetchWithAuth" frontend/src/features/auth/services/authService.ts`
- [ ] **Grep main.tsx QueryClient setup intact (no regression from 57.8)**
  - DoD: `<QueryClientProvider client={queryClient}>` wrap present
  - Command: `grep -n "QueryClientProvider\|QueryClient" frontend/src/main.tsx`
- [ ] **Grep governanceService.ts current fetch pattern (Risk D — claims mismatch detect)**
  - DoD: confirm raw `fetch` (not yet `fetchWithAuth`); identify Authorization header handling
  - Command: `grep -n "fetch\|fetchWithAuth\|Authorization" frontend/src/features/governance/services/governanceService.ts`
- [ ] **Grep IAM JWT claim shape (Risk D)**
  - DoD: confirm `_to_internal_jwt` claims output includes `tenant_id` + `roles`; verify backend `require_approver_role` / `require_audit_role` checks expected claims
  - Backend: `grep -n "require_approver_role\|require_audit_role\|roles\b" backend/src/platform_layer/identity/auth.py`
  - Frontend: `grep -n "_to_internal_jwt\|claims\|roles" backend/src/api/v1/auth/oidc.py 2>/dev/null` (Sprint 57.7 OIDC)
- [ ] **Grep `routes.config.ts` governance entry current state**
  - DoD: confirm `name: "Governance"` exists with `active: false` + `category: "admin"` + icon `ShieldCheck`
  - Command: `grep -n "Governance\|governance" frontend/src/routes.config.ts`
- [ ] **Grep 4 page services current fetch pattern (US-6 baseline)**
  - DoD: confirm direct `fetch` not yet TanStack; identify any partial migrations
  - Command: `grep -n "fetch\|useQuery\|useMutation" frontend/src/features/cost-dashboard/services/costService.ts frontend/src/features/sla-dashboard/services/slaService.ts frontend/src/features/admin-tenants/services/adminTenantsService.ts frontend/src/features/tenant-settings/services/tenantSettingsService.ts`
- [ ] **Grep Zustand store current state surface (US-6 baseline)**
  - DoD: identify which stores hold server state (data/loading/error) vs UI-only state (filter/draft)
  - Command: `grep -A 3 "interface.*State\b" frontend/src/features/cost-dashboard/store/costStore.ts frontend/src/features/sla-dashboard/store/slaStore.ts frontend/src/features/admin-tenants/store/adminTenantsStore.ts frontend/src/features/tenant-settings/store/tenantSettingsStore.ts | head -40`
- [ ] **Grep shadcn `<Dialog>` usage existing (Risk C — bundle weight)**
  - DoD: count Dialog imports across frontend; if 0 elsewhere, prefer Tailwind Modal impl
  - Command: `grep -rln "from.*shadcn.*dialog\|@/components/ui/dialog" frontend/src/`

**Prong 3 — Schema Verify**
- [ ] N/A — frontend-only sprint, no DB schema changes

**Drift findings catalog**
- [x] **Catalog all D-findings to progress.md Day 0 entry** ✅
  - 7 D-findings catalogued (D-PRE-1 RED resolved + D-PRE-2..6 GREEN + D-PRE-5 YELLOW)
  - Risk D resolution: 57.7 IAM `roles` claim ↔ 53.5 backend `_require_role` JWT consumption MATCH ✅
  - go/no-go: ✅ GO Day 1 (D-PRE-1 RED was Sprint 57.8 carryover not regression; baseline restored to 1622)

### 0.4 Calibration baseline confirmation
- [x] **Workload baseline written to progress.md** ✅
  - bottom-up est ~22 hr / committed ~10.5 hr / multiplier HYBRID 0.50 / class `frontend-feature-with-migration` (NEW 1-data-point opens; AD-Sprint-Plan-10 extension)

### 0.5 User decision points cleared (pre-confirmed via plan Q1-Q4)
- [x] Branch name confirmed: `feature/sprint-57-9-governance-ship-tquery-migration` (Q1 select A)
- [x] Audit log viewer scope confirmed: filter form + paginated table (Q2 select A)
- [x] Tab UX confirmed: URL-based 2 sub-routes (Q3 select A)
- [x] NEW calibration class `frontend-feature-with-migration` 0.50 baseline confirmed (Q4 select A)
- [ ] shadcn `<Dialog>` decision pending Day 0 Prong 2 bundle-weight grep (default Tailwind per YAGNI)

---

## Day 1 — US-1 AppShellV2 + Auth Gate + Tabs + US-2 Tailwind Migration

### 1.1 US-1: Pages governance/index.tsx composition
- [ ] **Modify `frontend/src/pages/governance/index.tsx`**
  - DoD: 40-line placeholder → composed real ship per plan §Technical Specifications
  - Auth gate: `if (!isAuthenticated()) { setPostLoginRedirect("/governance"); return <Navigate to="/auth/login" replace />; }`
  - Wrap: `<AppShellV2 pageTitle="Governance">` outside Routes
  - Tab nav: 2 NavLink components (Pending Approvals / Audit Log) above Routes
  - Routes: `<Route index element={<Navigate to="approvals" replace />} />` + `<Route path="approvals" element={<ApprovalsPage />} />` + `<Route path="audit-log" element={<AuditLogViewer />} />`
  - File header per `.claude/rules/file-header-convention.md`; MHist with Sprint 57.9 US-1 reason
- [ ] **Verify TypeScript strict pass**
  - Command: `npm run typecheck 2>&1 | tail -5`
  - Note: AuditLogViewer import will fail until US-4 creates the file — gate Day 1 to ApprovalsPage import only OR create stub `AuditLogViewer.tsx` returning `<div>TODO</div>`

### 1.2 US-1: routes.config.ts update
- [ ] **Modify `frontend/src/routes.config.ts`**
  - DoD: governance entry `active: false` → `active: true` + add `component: () => import("./pages/governance")`
  - Verify: sidebar shows Governance as active link (not grayed out)
  - Manual: dev server `npm run dev` + visit `/governance` → AppShellV2 renders

### 1.3 US-2: ApprovalsPage Tailwind migration
- [ ] **Modify `frontend/src/features/governance/components/ApprovalsPage.tsx`**
  - DoD: drop `pageStyle / headerRow / buttonStyle` const objects
  - Replace with Tailwind: `p-6 font-sans` for page + `flex items-baseline justify-between mb-4` for header row + shadcn `<Button variant="outline">` or Tailwind `border border-primary text-primary px-3 py-1 rounded` for refresh button
  - Preserve all behavior (polling 30s + AbortController + error state) — ONLY style change
  - MHist entry with Sprint 57.9 US-2 reason
- [ ] **Verify Vitest unit tests pass unchanged**
  - Command: `npm run test -- ApprovalsPage 2>&1 | tail -3`

### 1.4 US-2: ApprovalList Tailwind migration
- [ ] **Modify `frontend/src/features/governance/components/ApprovalList.tsx`**
  - DoD: drop inline `style={{}}` objects
  - Use Tailwind table utilities (`w-full border-collapse text-sm` etc.) OR shadcn `<Table>` if already in bundle (verify per Day 0 Prong 2)
  - Risk badge palette preserved via Tailwind utilities OR arbitrary values (`text-[#b71c1c]`)
  - MHist entry
- [ ] **Verify Vitest unit tests pass unchanged**

### 1.5 US-2: DecisionModal Tailwind migration
- [ ] **Modify `frontend/src/features/governance/components/DecisionModal.tsx`**
  - DoD: drop inline styles
  - Modal impl: per Day 0 Prong 2 decision (Tailwind `fixed inset-0 z-50 bg-black/50` + `<div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 ...">` portal pattern, OR shadcn `<Dialog>` if 0 bundle weight cost)
  - Preserve all submit/close behavior
  - MHist entry
- [ ] **Verify Vitest unit tests pass unchanged**

### 1.6 Day 1 wrap
- [ ] **Vite bundle size check**
  - DoD: total JS ≤ 280 kB (baseline 246.19 kB + 30 kB headroom)
  - Command: `npm run build 2>&1 | tail -5`
- [ ] **Update progress.md Day 1 entry**
  - Format: actual hr per task + drift findings + remaining for Day 2
- [ ] **Commit + push**
  - Message format: `feat(frontend, sprint-57-9): Day 1 — US-1 governance AppShellV2 + auth gate + tabs + US-2 Tailwind migration (3 components)`
  - Co-Authored-By line per `.claude/rules/git-workflow.md`

---

## Day 2 — US-3 TanStack Governance Hooks + Refactor

### 2.1 US-3: governanceService fetchWithAuth swap
- [ ] **Modify `frontend/src/features/governance/services/governanceService.ts`**
  - DoD: 2 fetch sites (`listPending` + `decide`) swap raw `fetch` → `fetchWithAuth`
  - Pattern mirror Sprint 57.8 D3 chatService: `import { fetchWithAuth } from "../../auth/services/authService";`
  - Preserve AbortSignal + headers + body
  - MHist entry with Sprint 57.9 US-3 reason
- [ ] **Verify existing Vitest unit tests pass unchanged**

### 2.2 US-3: useApprovals hook
- [ ] **Create `frontend/src/features/governance/hooks/useApprovals.ts`**
  - DoD: per plan §Technical Specifications snippet
  - Export `APPROVALS_QUERY_KEY` const for invalidation reuse
  - File header per convention
- [ ] **Vitest unit test `frontend/tests/unit/governance/useApprovals.test.tsx`**
  - DoD: ≥3 tests (initial fetch / refetch on stale / error state)
  - Use `@tanstack/react-query` test utilities + `QueryClient` per-test isolation

### 2.3 US-3: useApprovalDecide mutation hook
- [ ] **Create `frontend/src/features/governance/hooks/useApprovalDecide.ts`**
  - DoD: per plan §Technical Specifications snippet
  - `onSuccess` invalidates `APPROVALS_QUERY_KEY`
  - File header per convention
- [ ] **Vitest unit test `frontend/tests/unit/governance/useApprovalDecide.test.tsx`**
  - DoD: ≥3 tests (mutate success → invalidate query / error state / rapid double-click race per Risk B)

### 2.4 US-3: ApprovalsPage refactor
- [ ] **Modify `frontend/src/features/governance/components/ApprovalsPage.tsx`**
  - DoD: drop useEffect/useState/setInterval/AbortController/refresh callback
  - Use `const { data: items = [], isLoading, error, refetch } = useApprovals();`
  - Preserve loading/error UI; refresh button calls `refetch()`
  - MHist entry "Sprint 57.9 US-3 — drop manual polling, consume useApprovals hook"
- [ ] **Verify existing Vitest unit tests pass unchanged**
  - Note: tests may need wrapper `<QueryClientProvider>` (mirror cost-dashboard 57.7 pattern if exists)

### 2.5 US-3: DecisionModal refactor
- [ ] **Modify `frontend/src/features/governance/components/DecisionModal.tsx`**
  - DoD: drop manual `await onSubmit(decision, reason); refresh()` pattern
  - Use `const decideM = useApprovalDecide();` + `decideM.mutate({ id, decision, reason }, { onSuccess: onClose })`
  - Loading state via `decideM.isPending`; error via `decideM.error`
  - MHist entry
- [ ] **Verify existing Vitest unit tests pass unchanged**

### 2.6 Day 2 wrap
- [ ] **Vite bundle size check**
  - DoD: total JS ≤ 285 kB (small headroom for 3 hooks + service swap)
- [ ] **Update progress.md Day 2 entry**
- [ ] **Commit + push**
  - Message: `feat(frontend, sprint-57-9): Day 2 — US-3 TanStack governance hooks + ApprovalsPage/DecisionModal refactor + governanceService fetchWithAuth`

---

## Day 3 — US-4 Audit Log Viewer + US-5 Chain Verify Badge

### 3.1 US-4: auditService.ts NEW
- [ ] **Create `frontend/src/features/governance/services/auditService.ts`**
  - DoD: 2 functions:
    - `fetchAuditLog(filter: AuditLogFilter): Promise<AuditLogPage>` consuming GET `/api/v1/audit/log` with query params
    - `verifyChain(): Promise<ChainVerifyResult>` consuming GET `/api/v1/audit/verify-chain`
  - Both use `fetchWithAuth` for IAM JWT
  - URLSearchParams for filter (omit-undefined helper; mirror Sprint 57.4 buildListSearchParams pattern)
  - File header per convention
- [ ] **Modify `frontend/src/features/governance/types.ts`**
  - DoD: extend with `AuditLogFilter` (matching backend Query params) + `AuditLogEntry` (matching DTO 12 fields) + `AuditLogPage` (items + has_more + next_offset + page_size) + `ChainVerifyResult` (valid + broken_at_id + total_entries)

### 3.2 US-4: useAuditLog hook
- [ ] **Create `frontend/src/features/governance/hooks/useAuditLog.ts`**
  - DoD: `useQuery({ queryKey: ['governance', 'audit-log', filter], queryFn: ({ signal }) => auditService.fetchAuditLog(filter, signal) })`
  - QueryKey includes filter object for auto-refetch on change
  - File header per convention
- [ ] **Vitest unit test `frontend/tests/unit/governance/useAuditLog.test.tsx`**
  - DoD: ≥2 tests (queryKey structure / refetch on filter change)

### 3.3 US-4: AuditLogViewer component
- [ ] **Create `frontend/src/features/governance/components/AuditLogViewer.tsx`**
  - DoD: per plan §Audit log filter UI sketch
  - Filter form: 4 fields (operation dropdown / resource_type dropdown / user_id input / date range pickers)
  - State: `const [filter, setFilter] = useState<AuditLogFilter>({ offset: 0, page_size: 50 })`
  - Apply button updates filter; Reset button clears to default
  - Paginated table: 6 columns (timestamp / operation / resource_type / resource_id / user_id / current_log_hash truncated)
  - Next/Prev buttons; disabled at boundaries; `has_more` indicator
  - Loading skeleton + error retry UX (mirror cost-dashboard CostOverview pattern)
  - Tailwind utilities only (no inline styles)
  - File header per convention
- [ ] **Vitest unit test `frontend/tests/unit/governance/AuditLogViewer.test.tsx`**
  - DoD: ≥2 tests (renders empty state / filter form interaction triggers refetch)

### 3.4 US-5: AuditChainBadge component
- [ ] **Create `frontend/src/features/governance/components/AuditChainBadge.tsx`**
  - DoD: useQuery({ queryKey: ['governance', 'verify-chain'], queryFn: auditService.verifyChain }) — no `refetchInterval` (heavy operation per backend docstring)
  - 3 states rendered: `⏳ Verifying chain…` / `✅ Chain valid (N entries)` / `⚠️ Chain broken at row {broken_at_id}` / `❌ Verify failed: {error}`
  - Manual `Re-verify` button calls `refetch()`
  - Tailwind badge styling (no inline)
  - File header per convention
- [ ] **Wire AuditChainBadge into AuditLogViewer header**
  - DoD: top-right of filter form area
- [ ] **Vitest unit test `frontend/tests/unit/governance/AuditChainBadge.test.tsx`**
  - DoD: ≥1 test (renders 3 states via mock)

### 3.5 US-1 stub fixup (post-US-4 complete)
- [ ] **If Day 1 created stub AuditLogViewer.tsx, ensure now real component**
  - DoD: pages/governance/index.tsx import resolves to real US-4 implementation; TypeScript strict pass

### 3.6 Day 3 wrap
- [ ] **Vite bundle size check**
  - DoD: total JS ≤ 290 kB (audit log viewer + chain badge + 2 services + 2 hooks budget)
- [ ] **Update progress.md Day 3 entry**
- [ ] **Commit + push**
  - Message: `feat(frontend, sprint-57-9): Day 3 — US-4 AuditLogViewer + auditService + useAuditLog + US-5 AuditChainBadge`

---

## Day 4 — US-6 4-page TanStack Migration + Closeout

> **MANDATORY discipline per Sprint 57.7 + 57.8 lessons (PR #116 + #118 carry-forward)**:
> Day 4 closeout MUST run **full pytest suite + full Vitest + full Playwright + 9 V2 lints + 3 backend lint sweep** BEFORE pushing any closeout commit. NOT subset.
> See plan §Risks H + §Sprint 57.7+57.8 lesson carry-forward.

### 4.1 US-6: 4-page TanStack hook creation
- [ ] **Create 4 hook files**
  - `frontend/src/features/cost-dashboard/hooks/useCostSummary.ts` (~30 LOC; queryKey `['cost', 'summary', tenantId, month]`)
  - `frontend/src/features/sla-dashboard/hooks/useSLAOverview.ts` (~30 LOC; queryKey `['sla', 'overview', tenantId]`)
  - `frontend/src/features/admin-tenants/hooks/useTenantList.ts` (~40 LOC; queryKey `['admin-tenants', 'list', filter]`)
  - `frontend/src/features/tenant-settings/hooks/useTenant.ts` (~30 LOC; queryKey `['tenant-settings', 'tenant', tenantId]`)
  - All use `fetchWithAuth` via existing service layer
  - File headers per convention with US-6 MHist

### 4.2 US-6: 4-page component refactor
- [ ] **Modify `frontend/src/features/cost-dashboard/components/CostOverview.tsx`**
  - DoD: drop `useEffect + useCostStore.loadData`; use `useCostSummary` hook
  - Keep `currentMonth` from store (UI state)
- [ ] **Modify `frontend/src/features/sla-dashboard/components/SLAOverview.tsx`**
  - DoD: same pattern
- [ ] **Modify admin-tenants list page (path TBD via Day 0 Prong 1)**
  - DoD: drop loadList; use useTenantList hook
- [ ] **Modify `frontend/src/features/tenant-settings/components/TenantSettingsView.tsx`**
  - DoD: drop loadTenant; use useTenant hook

### 4.3 US-6: 4 Zustand store reductions
- [ ] **Modify 4 store files to UI-only state**
  - costStore: keep `currentMonth + setMonth`; drop `data + loading + error + loadData`
  - slaStore: keep UI selectors only; drop server state
  - adminTenantsStore: keep `filter + offset + setFilter + setOffset`; drop list server state
  - tenantSettingsStore: keep `editDraft + setEditDraft`; drop server state
  - Each store MHist entry with Sprint 57.9 US-6 reason

### 4.4 Full validation sweep (BLOCKER for Day 4 commit)
- [ ] **Backend pytest full suite**
  - DoD: 1622 baseline maintained (no backend changes this sprint)
  - Sprint 57.8 D13 carry-forward: if pre-existing pollution, document delta
- [ ] **Vitest full suite**
  - DoD: 57 → ≥65 (+8 from 8 new unit tests: 3 governance hooks + 2 audit + 1 AuditChainBadge + ApprovalsPage smoke + DecisionModal smoke)
- [ ] **Playwright full suite**
  - DoD: 27 → ≥31 (+4 from chat-v2-style governance e2e cases)
- [ ] **mypy + 9 V2 lints**
  - mypy: `python -m mypy src --strict` 0/300 unchanged
  - 9 V2 lints: `python scripts/lint/run_all.py` 9/9 green
- [ ] **Frontend full lint sweep**
  - ESLint silent + Vite build OK + bundle ≤ 280 kB main
- [ ] **Backend full lint sweep**
  - flake8 silent + black --check + isort --check-only all silent
- [ ] **LLM SDK leak check**
  - 0 `import openai` / `import anthropic` in `agent_harness/` (covered by check_llm_sdk_leak.py)

### 4.5 US-6 stretch: Playwright e2e cases NEW (governance-real-ship.spec.ts)
- [ ] **Create `frontend/tests/e2e/governance/governance-real-ship.spec.ts`**
  - DoD: 4 cases per plan §US-1 acceptance:
    1. **auth gate**: clearAuthJwt + goto `/governance` → assert URL becomes `/auth/login`
    2. **happy path render**: seedAuthJwt + goto → assert AppShellV2 h1 "Governance" + tab nav (Pending Approvals + Audit Log) + default redirect to /governance/approvals
    3. **tab switch**: click "Audit Log" → URL becomes `/governance/audit-log` + AuditLogViewer renders + AuditChainBadge visible
    4. **decision flow** (mocked): mock 1 pending approval → click row → DecisionModal opens → click Approve → mock decide POST captured → list refreshes (invalidate query)
  - Mock backend via Playwright `page.route()` (mirror Sprint 53.6 D11 + 57.8 D11 pattern)
  - Use `seedAuthJwt` / `clearAuthJwt` from Sprint 57.8 fixtures
- [ ] **Verify e2e pass via Vite build sentinel**
  - Vite build + ts -b passes; full Playwright run on PR CI

### 4.6 Retrospective.md (Q1-Q7 mandatory format per Sprint 57.7+57.8 + sprint-workflow.md)
- [ ] **Create `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-9/retrospective.md`**
  - Q1 What went well: existing 53.5 components rich reuse / TanStack 4-page closure / 6 USs delivered
  - Q2 calibration ratio: actual_hr / 10.5 commit = ratio (target [0.85, 1.20] band)
  - Q3 lessons: governance HITL ship is V2 core differentiation visible / TanStack migration = mechanical pattern reuse confirmation / NEW class `frontend-feature-with-migration` 1st-app data point
  - Q4 audit debt: closures (AD-Cost-Dashboard-UseQuery + AD-Front-1 partial via TanStack interim) + new ADs if any
  - Q5 Phase 57.10+ candidates: verification real ship (~10-12 hr — same pattern reuse) / 5 deferred pages from 16.md V2 Ship Timeline / SOC 2 + SBOM ~12-15 hr / Status Page + APAC ~10-12 hr / Tier 1 IaC ~15-20 hr
  - Q6 solo-dev policy held; 5 active CI checks
  - Q7 N/A SKIP — feature ship sprint NOT spike (no design note required)

### 4.7 Memory snapshot
- [ ] **Create `~/.claude/projects/.../memory/project_phase57_9_governance_ship.md`** (~120 lines)
- [ ] **Update MEMORY.md index entry** (~200 chars target)

### 4.8 Doc syncs (3/4; CLAUDE.md deferred to post-merge closeout PR per 57.7+57.8 pattern)
- [ ] **`.claude/rules/sprint-workflow.md` calibration matrix +1 row**
  - NEW row `frontend-feature-with-migration` 0.50 HYBRID 1-data-point baseline + Modification History entry
  - Status: KEEP 0.50 baseline opens per `When to adjust` 3-sprint window rule
- [ ] **`CLAUDE.md` 3 surgical edits** 🚧 DEFERRED to post-merge closeout PR
  - Per Sprint 57.7+57.8 pattern (PR #115/#117/#119 mirror): main HEAD row needs merged commit SHA which is unknown until PR merges → all 3 CLAUDE.md edits bundled in post-merge closeout PR
- [ ] **`SITUATION-V2-SESSION-START.md` §9 + §11 update**
  - §9 milestone +1 row Sprint 57.9 entry inserted before 57.8 row (newest-first)
  - §11 Last Updated header refreshed; Previous = 57.8 demoted to 1-paragraph summary
- [ ] **`16-frontend-design.md` V2 Ship Timeline update**
  - "5 已 ship pages" → **"6 已 ship pages"** (governance promoted from "2 priority")
  - "2 priority Phase 57.9+ ship" → **"1 priority Phase 57.10 ship"** (governance closed; verification remaining)
  - Sprint slot mapping: Phase 57.7 + 57.8 + 57.9 ✅ DONE; Phase 57.10 = verification real ship
  - Modification History entry; Reality framing notes Sprint 57.9 closes AD-Cost-Dashboard-UseQuery via 4-page TanStack migration

### 4.9 PR + closeout sync (post-merge)
- [ ] **Open main PR** 🚧 PENDING USER INSTRUCT
  - Per CLAUDE.md "破壞性操作前必問" + rolling planning gate
  - Draft prepared: Title `Sprint 57.9 — Governance Real Ship + TanStack Query 4-page Migration (6 USs + frontend-feature-with-migration calibration class)`
- [ ] **Wait CI green** 🚧 PENDING — after PR open
- [ ] **Solo-dev squash merge** 🚧 PENDING — wait user explicit "merge"
- [ ] **Post-merge: closeout PR for CLAUDE.md sync** 🚧 PENDING — mirror PR #115/#117/#119 pattern

### 4.10 User decision points pending Day 4.6
- [ ] **Phase 57.10+ direction** 🚧 PENDING USER INSTRUCT
  - Top candidates per Q5 retrospective: verification real ship (highest ROI — same pattern reuse as 57.9) / 5 deferred pages from 16.md / SOC 2 / Status Page / Tier 1 IaC

---

## 重要備註

### Rolling planning 紀律自檢(每 day 結束 + Day 4 closeout 必檢)

- ☐ 沒預寫多個未來 sprint plan(Phase 57.10 plan/checklist 留 user 選定 scope 才起草;只列 5 candidate)
- ☐ 沒跳過 plan/checklist 直接 code(全在 sprint-57-9-{plan,checklist}.md 框架內)
- ☐ 沒刪除未勾選的 [ ] 項目(US-1 stub fix 若延後 + reason)
- ☐ 沒在 retrospective.md 寫具體未來 sprint task(Q5 only candidate list)

### V2 紀律 9 項自檢(每 commit + 每 PR)

per plan §Sprint 57.7+57.8 lesson carry-forward + `.claude/rules/anti-patterns-checklist.md`:
1. Server-Side First — N/A frontend sprint
2. LLM Provider Neutrality — frontend 不 import LLM SDK(N/A; backend 維持 0 leak)
3. CC Reference 不照搬 — N/A
4. 17.md Single-source — useApprovals queryKey APPROVALS_QUERY_KEY single-source export;auditService 不重複 backend contract
5. 11+1 範疇歸屬 — frontend 不在 11 範疇;features/* 結構維持
6. 04 anti-patterns — AP-2 (no orphan):routes.config.ts governance entry active 後 pages/governance 必 reachable;AP-9 (verification):governance ship 含 ApprovalCard pipeline 不 bypass HITL;AP-3 (no scattering):governance components 集中 features/governance/
7. Sprint workflow — plan → checklist → Day 0 三-prong → code → progress → retro
8. File header convention — 全新 file 必有 header + MHist;1-line max per MHist entry
9. Multi-tenant rule — frontend tenant_id 從 JWT 解(consume 57.7 IAM);backend governance/audit endpoints enforce via require_approver_role / require_audit_role + get_current_tenant

### Sprint 57.7 D19 + 57.8 D13 cascade lesson 強制執行(此 sprint 必行)

**Day 4 closeout pre-push checklist**(plan §Risks H):
1. ☐ 跑 full `python -m pytest`(NOT `tests/unit/` only)
2. ☐ 跑 full `npm run test`(Vitest 全量)
3. ☐ 跑 full `npm run e2e`(Playwright 全量)
4. ☐ 跑 full backend 3 lint(flake8 + black + isort on `src` + `tests`)
5. ☐ 跑 full frontend lint + typecheck + build
6. ☐ 跑 V2 9 lints(`scripts/lint/run_all.py`)
7. ☐ Vite bundle size 確認 ≤ 290 kB main
8. ☐ Pre-existing dev DB pollution check (Sprint 57.8 D13 carry-forward)

**只跑 1+2+3+4+5+6+7+8 全綠才 push closeout commit**;single test scope shortcut 禁止。

### Open Items / Carry-forward(填入 retrospective Q4 + Q4.1)

- [ ] AD-Sprint-Plan-10 NEW class `frontend-feature-with-migration` 0.50 baseline 1-data-point opens(此 sprint 1st app)
- [ ] AD-Front-1 polling-vs-SSE: TanStack refetchInterval = interim solution; SSE upgrade 仍 candidate Phase 58.x carryover
- [ ] AD-Cat10-VisualVerifier+Frontend-Panel(verification real ship Phase 57.10 候選)
- [ ] AD-Cat11-Multiturn / SSEEvents / ParentCtx(54.2 deferred 仍 open Phase 56+)
- [ ] AD-CI-6 Phase 58 production launch
- [ ] AD-RBAC-FullDBOnly Phase 58.x(57.7 carryover)
- [ ] AD-IAM-{SAML, MFA, RefreshToken, SCIM} Phase 58.x(57.7 carryover)
- [ ] AD-Frontend-{AuthUX, Sentry} Phase 58.2+(57.7 carryover)
- [ ] AD-Frontend-h1-Convention(57.8 carryover)
- [ ] AD-Test-Tenant-Code-Pollution(57.8 carryover)
- [ ] AD-Plan-3-h1-Grep meta-rule(57.8 carryover)
- [ ] AD-Cost-Dashboard-ChildrenTailwind(57.8 carryover — admin-tenants error block batch)

### Sprint workflow §Step 5 expansion candidate

Per Sprint 57.7 D19 + 57.8 D13 lessons:在 `.claude/rules/sprint-workflow.md` §Step 5(Day 4 closeout)新增:
> Day 4 closeout 必須 full suite 跑 backend pytest + frontend Vitest + Playwright + 3 lint sweep + V2 9 lints,**禁止只跑 `tests/unit/` 或單檔 lint**;另須檢查 dev DB pre-existing pollution。違反 = closeout commit 拒絕 push。

此 expansion 候選 fold-in Phase 57.10 closeout(若 57.9 retro Q3 確認 lesson 仍 generalizable)。
