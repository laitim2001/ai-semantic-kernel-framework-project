# Sprint 57.40 — AD-Governance-Full-Mockup-Fidelity-Rebuild

**Phase**: 57 (Frontend SaaS)
**Sprint id**: 57.40
**Drafted**: 2026-05-25 (Day 0)
**Branch**: `feature/sprint-57-40-governance-full-rebuild`
**Class**: `frontend-mockup-strict-rebuild` (6th data point; 5-pt mean 0.96 in [0.85, 1.20] band middle — class healthy). **NOT** `frontend-verbatim-css-repoint` because production page has fundamentally different architecture (simple 2-tab + table) vs mockup (4-KPI + 5-tab + 2-col Pending/Detail rich UI) — needs structural rebuild, not just CSS swap.
**Mirror template**: Sprint 57.39 plan (§ structure 0-9, 10 main sections; 5-day Day-numbering Day 0/1/2/2.5/3)

---

## 0. Sprint Goal

Single-domain sprint to **fully rebuild `/governance` Approvals view from mockup `page-governance.jsx:283 Approvals`** (HITL Approvals 4-KPI + 5-tab + 2-col Pending list + Detail pane + Approve/Reject/Escalate buttons). Resolves the 2026-05-25 22-page drift audit's #1 priority CATASTROPHIC drift verdict on `/governance`. Existing `useApprovals` / `useApprovalDecide` / `useAuditLog` TanStack Query wiring + service layer preserved; only the visual/structural layer rebuilt.

### Drift audit context

Per `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md`:

- **Mockup design** (`reference/design-mockups/page-governance.jsx:283 Approvals`, ~125 lines): `.page-head` (HITL Approvals title + actions) + `.grid-stats` 4 KPI (Active queue / p50 approval time / Approved 24h / Rejected 24h) + 5-tab nav (Active / Approved / Rejected / Expired / Policies) + 2-col grid (Pending list 7-col table left + Detail pane right with 7 KvRow + Tool input payload + Agent rationale + 4 action buttons).
- **Production reality** (`frontend/src/pages/governance/index.tsx` 83 lines + `features/governance/components/ApprovalsPage.tsx` 73 lines + `ApprovalList.tsx` 102 lines): only **2-tab** (Pending Approvals + Audit Log) + simple 6-col `<table>` + no KPI + no detail pane + Approve/Reject only via modal-flow.
- **D-DAY0-1 finding** (caught during plan-drafting Day 0): the "Failed to load approvals: ["governance","approvals"] data is undefined" red banner observed in 2026-05-25 audit screenshots is a **route-sweep mock artifact**, NOT a real production bug. Mock default returns `[]` for unmatched `/api/v1/*` URLs; `governanceService.listPending` expects `PendingListResponse{items}` shape — `[].items` returns `undefined` → TanStack throws "data is undefined". Real backend `GET /governance/approvals` returns proper `{items: [...]}` shape (verified `backend/src/api/v1/governance/router.py`). **Scope adjustment**: original audit estimate "fix runtime bug 2-3 hr" is reduced to "add specific mock for `/governance/approvals` in route-sweep.mjs (~30 min)" — saves ~2 hr vs original audit estimate.

---

## 1. Background

### 1.1 Why a strict-rebuild not a verbatim-css-repoint

Sprint 57.39 + FIX-015 + FIX-017 already swapped tokens on the EXISTING simple `/governance` page (Tailwind utility → mockup verbatim `--risk-X` tokens; shadcn-utility residue removed). The token surface is already mockup-aligned. The remaining drift is **structural** — the production page does not have:
- 4-KPI strip
- 5-tab nav (it has 2-tab containing /approvals + /audit-log nested routes)
- 2-col grid with Pending list + Detail pane
- Detail pane's 7-KvRow + Tool input payload + Agent rationale + 4-action button stack

These cannot be added via a CSS swap — they require new React components. Hence `frontend-mockup-strict-rebuild` 0.60 class (per Sprint 57.23-57.27 + 57.37 epic precedent, 5-pt mean 0.96).

### 1.2 What stays unchanged (preserved wiring)

| Layer | Preserved | Source |
|-------|-----------|--------|
| Auth gate | `<RequireAuth>` wrap | `frontend/src/pages/governance/index.tsx:66` |
| Shell wrap | `<AppShellV2 pageTitle="Governance">` | same |
| Tab routing for `/governance/audit-log` | NavLink-style; `/audit-log` remains the existing `AuditLogViewer` mount | same |
| `useApprovals` TanStack Query | `queryKey: APPROVALS_QUERY_KEY` + 30s `refetchInterval` | `features/governance/hooks/useApprovals.ts` |
| `useApprovalDecide` mutation | invalidates `APPROVALS_QUERY_KEY` on success | `features/governance/hooks/useApprovalDecide.ts` |
| `governanceService.listPending` + `decide` | `fetchWithAuth` JWT injection | `features/governance/services/governanceService.ts` |
| `ApprovalList` table | rebuild: 6-col → mockup 7-col (add SevDot + 12.5px session_title + 10.5px agent·id mono sub) | NEW props shape may need refactor |
| `DecisionModal` | KEEP behavior (Approve/Reject form) but **may be retired** if mockup detail pane fully replaces modal flow — Day 1 decision |
| `RISK_COLOR_CLASS` | preserved post FIX-017 (`var(--risk-X)` tokens) | `features/governance/components/ApprovalList.tsx:39-44` |
| Backend `/governance/approvals` endpoint | no change | `backend/src/api/v1/governance/router.py` |

### 1.3 What changes (rebuild scope)

| Layer | Old | New (per mockup) |
|-------|-----|------------------|
| Page shell | `Tabs items=[Pending Approvals, Audit Log]` | `Tabs items=[Active, Approved, Rejected, Expired, Policies]` for **the Approvals view itself**; `/governance/audit-log` remains a separate sub-route accessed differently (TBD Day 1; see §1.4 routing decision) |
| Page intro | `<h2>Pending Approvals</h2>` + Refresh button | `.page-head` 結構 (title + sub + route-pill + Teams sync / Export actions) |
| KPI | none | `.grid-stats` 4 cards: Active queue (count) / p50 approval time / Approved 24h / Rejected 24h |
| Filtering | none | 5-tab + (active tab only wired to real `useApprovals`; other 4 tabs render `<AP2BackendGapBanner>` per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint) |
| Layout | single column table | 2-col grid `(1fr 420px)` Pending list + Detail pane |
| Selected approval visualization | DecisionModal popup | persistent right-side Detail pane (selected row highlighted; pane shows 7 KvRow + Tool input payload + Agent rationale + 4 buttons) |
| Row interaction | "Review" button → opens modal | row `onClick` → `setSelected(id)` updates the persistent Detail pane in-place |
| Action buttons | Approve / Reject (in modal) | 4 buttons in Detail pane (Approve & continue / Approve with edits / Reject / Escalate to L2) |

### 1.4 Audit Log tab routing decision (Q for Day 0 final)

**Mockup** says 5 tabs (Active / Approved / Rejected / Expired / Policies); `/audit-log` is NOT one of those 5. But current production has `/governance/audit-log` as a sub-route. **Decision**: keep `/governance/audit-log` as a SEPARATE sub-route NOT inside the 5-tab nav; the 5 tabs are ALL about approvals filtering. Audit Log is a different concept entirely (per mockup, `AuditPage` is its own component at `page-governance.jsx:670` — distinct from `Approvals`). This means:
- `/governance` (default) → Approvals 5-tab view
- `/governance/audit-log` → existing AuditLogViewer (no change)
- Top-level navigation between the two: keep current 2-tab outer NavLink as parent shell; inner 5-tab is for filtering approvals within /approvals

OR alternative: drop the outer 2-tab and access /audit-log via a separate sidebar entry (already exists in `routes.config.ts` as a DRAFT entry). Decision **A** (preserve current outer 2-tab outer Tabs as-is + add inner 5-tab Approvals view) is the lower-risk choice — minimal change to outer page structure; only `ApprovalsPage` body rebuilt.

→ **Selected: A** (outer 2-tab preserved; inner 5-tab added inside ApprovalsPage).

### 1.5 Class baseline + calibration evaluation criteria

`frontend-mockup-strict-rebuild` 0.60 (6th application; 5-pt mean 0.96 in [0.85, 1.20] band middle — class healthy):

| Sprint | Page | Ratio | Notes |
|--------|------|-------|-------|
| 57.23 | auth flow rebuild (7 routes) | 0.59 | 1st app below band 0.26 |
| 57.24 v2 | cost-dashboard rebuild | 1.19 | 2nd app top of band |
| 57.25 | sla-dashboard rebuild | 0.88 | 3rd app in band |
| 57.27 | overview rebuild | ≈0.95 | 4th app in band |
| 57.37A | loop-debug rebuild | ≈1.18 | 5th app top of band |
| **57.40 (this)** | **governance rebuild** | **TBD** | **6th app — single-domain, mid-scope (4-KPI + 5-tab + 2-col)** |

Evaluation thresholds:
- **PASS**: ratio in [0.85, 1.20] → KEEP 0.60 baseline; class confirmed healthy at 6th app
- **ABOVE band** (>1.20): single data point in 6-pt window; KEEP per `When to adjust` 3-sprint rule unless 3rd consecutive
- **BELOW band** (<0.85): same — KEEP per rule

### 1.6 Phase-2 epic progress impact

Pre-sprint (per `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md`):
- **Honest** Phase-2 status: ~10/17 PARITY, **5 🟡 CATASTROPHIC drift** (`/memory`, `/governance`, `/verification`, `/admin-tenants`, `/tenant-settings`), 1 🟡 NEAR-PARITY (`/chat-v2` tab vocab)
- CLAUDE.md previously said `15/17 routes shipped / 2 🟡 STRUCTURAL Phase 58+` — audit revealed reality is 5 catastrophic drifts

Post-sprint (if Sprint 57.40 ships):
- **Phase-2: 11/17 PARITY / 4 🟡 CATASTROPHIC remaining** (`/memory`, `/verification`, `/admin-tenants`, `/tenant-settings`)
- This is sprint #1 of the 6-sprint epic to close all 5 catastrophic drifts (#2 `/verification` ~8-10 hr, #3 `/memory` ~10-15 hr, #4 `/admin-tenants` ~12-15 hr, #5 `/tenant-settings` ~15-20 hr, #6 `/chat-v2` tab rename ~30 min)

---

## 2. User Stories

### Domain — `/governance` Approvals view full rebuild

#### US-1 — `.page-head` mockup-aligned
As the operator, I want `/governance/approvals` to show a proper page header (`HITL Approvals` title + sub-text + `/governance/approvals` route-pill + Teams sync / Export buttons) matching mockup, so the page identity is clear.

#### US-2 — 4 KPI strip
As the operator, I want 4 KPI cards at the top of the Approvals view (Active queue / p50 approval time / Approved · 24h / Rejected · 24h) so I have an at-a-glance overview of HITL queue health. Active queue count derived from `useApprovals.data.length`; other 3 KPIs use fixture data with `<AP2BackendGapBanner>` until Cat 9 backend stats endpoint ships.

#### US-3 — 5-tab nav (Active / Approved / Rejected / Expired / Policies)
As the operator, I want to filter approvals by status across 5 tabs. Tab `active` is wired to real `useApprovals` (pending queue). Tabs `approved` / `rejected` / `expired` / `policies` render placeholder content with `<AP2BackendGapBanner>` per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint (backend filter endpoints deferred to next sprint).

#### US-4 — 2-col Pending list + Detail pane layout
As the operator, I want a `1fr 420px` 2-col grid where the left column shows the Pending approvals table (7 columns: SevDot / Session / Tool / Risk / Policy / Operator / SLA) and the right column shows the selected approval's detail pane. Selected row highlighted with `oklch(from var(--primary) l c h / 0.08)` background.

#### US-5 — Detail pane (KvRow / Tool input payload / Agent rationale / 4 action buttons)
As the reviewer, when I click an approval row, I want the right Detail pane to update with:
- Title: SevDot + approval ID + Audit button
- Subtitle: session_title
- 7 KvRow: tool / risk / policy / scope / operator / age / SLA remaining
- Field "Tool input payload" with monospace `<pre>` of the JSON
- Field "Agent rationale" with narrative text
- 4 action buttons stacked (Approve & continue / Approve with edits / Reject / Escalate to L2)
- Approve & Reject buttons wire to existing `useApprovalDecide` mutation hook
- `Approve with edits` + `Escalate to L2` render `<AP2BackendGapBanner>` for now (backend deferred)

#### US-6 — DecisionModal retirement decision
As the developer, if the new Detail pane fully replaces the old modal flow (which was the only Approve/Reject path), I want `DecisionModal.tsx` either deleted (orphan delete per Karpathy §3) OR kept ONLY for the `Approve with edits` flow (modal opens with reason textarea). Day 1 decision after Detail pane built.

#### US-7 — Vitest baseline preserved (≥478/478)
After all sprint changes, Vitest must remain green at or above the 478 baseline (Sprint 57.39 close). NEW specs allowed for new components (target +4-8 NEW specs).

#### US-8 — 22-route sweep clean + route-sweep mock fix
22-route Playwright sweep `before` vs `after`: only `/governance` expected CHANGED (rebuild). Other 21 routes IDENTICAL. **D-DAY0-1 fix**: add `/governance/approvals` specific mock in `route-sweep.mjs` returning `{items: []}` shape to eliminate the misleading "Failed to load approvals" red banner in mock captures.

#### US-9 — mockup-fidelity guard + HEX_OKLCH_BASELINE bump
`node frontend/scripts/check-mockup-fidelity.mjs` exit 0; baseline may bump +3-6 (4 KPI badges + 5-tab + selected row highlight `oklch(from var(--primary) l c h / 0.08)` + Tool input payload pre + SevDot palette).

#### US-10 — Audit report verdict update
After sprint, update `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` to mark `/governance` verdict ✅ **PARITY** post-rebuild; carryover list shrinks 5 → 4 🟡 CATASTROPHIC.

---

## 3. Technical Specifications

### 3.1 Component refactor map

```
frontend/src/pages/governance/index.tsx (83 lines, UNCHANGED structure: RequireAuth + AppShellV2 + outer 2-tab + Routes)
  └─ <Route path="approvals" element={<ApprovalsPage />} />
       ↓
       frontend/src/features/governance/components/ApprovalsPage.tsx (REBUILD ~150-180 lines)
        ├─ <ApprovalsPageHeader /> — NEW (mockup `.page-head`)
        ├─ <ApprovalsStatsStrip /> — NEW (mockup `.grid-stats` 4 KPI)
        ├─ <ApprovalsFilterTabs /> — NEW (mockup 5-tab using mockup-ui `<Tabs>`)
        ├─ <div className="grid grid-cols-[1fr_420px] gap-[14px]"> — 2-col grid
        │    ├─ <ApprovalsListCard /> — REBUILD `ApprovalList.tsx` → wraps in Card with mockup-ui pattern
        │    └─ <ApprovalDetailPane /> — NEW (the right column rich detail)
        └─ {selected && /* OR DecisionModal if kept for "Approve with edits" */}
```

### 3.2 NEW components inventory

| Component | File | Lines (est) | Purpose |
|-----------|------|-------------|---------|
| `ApprovalsPageHeader` | `features/governance/components/ApprovalsPageHeader.tsx` | ~30 | mockup `.page-head` + Teams sync / Export buttons |
| `ApprovalsStatsStrip` | `features/governance/components/ApprovalsStatsStrip.tsx` | ~45 | 4 Stat cards (Active queue derived from `useApprovals.data?.length`; other 3 KPIs fixture + AP-2 banner) |
| `ApprovalsFilterTabs` | `features/governance/components/ApprovalsFilterTabs.tsx` | ~25 | wraps mockup-ui `<Tabs>` with 5-tab items |
| `ApprovalDetailPane` | `features/governance/components/ApprovalDetailPane.tsx` | ~120 | KvRow + Field + Tool input payload pre + Agent rationale + 4 buttons; consumes `useApprovalDecide` for Approve/Reject |
| `ApprovalsEmptyTab` | `features/governance/components/ApprovalsEmptyTab.tsx` | ~20 | placeholder for approved/rejected/expired/policies tabs with AP-2 banner |

### 3.3 REBUILD components inventory

| Component | File | Change |
|-----------|------|--------|
| `ApprovalsPage` | `features/governance/components/ApprovalsPage.tsx` | Restructure (1 col → 2-col grid + KPI strip + filter tabs); add `selected` state + `setSelected` for Detail pane interaction |
| `ApprovalList` | `features/governance/components/ApprovalList.tsx` | 6-col → 7-col (add SevDot first column + 12.5px session_title + 10.5px agent·id mono sub); add `selected` prop + row highlight; row `onClick` → `onSelect(approval.id)` (was already so; now updates Detail pane in-place not modal) |
| (optional) `DecisionModal` | `features/governance/components/DecisionModal.tsx` | DECISION pending: retire entirely (orphan delete) IF Detail pane covers all; OR keep ONLY for "Approve with edits" reason capture flow |

### 3.4 mockup-ui primitives used

Per `frontend/src/components/mockup-ui.tsx` (post Sprint 57.34 promotion):
- `<Tabs>` — already used in outer governance page (line 45 import); 5-tab inner usage adds `count` items
- `<Stat>` (4 KPI cards) — confirm exists per `frontend/src/components/mockup-ui.tsx` exports; if not, lift from Sprint 57.24 cost-dashboard rebuild's `<StatCard>` primitive
- `<Card>` — confirm; lift from Sprint 57.24's `<CardShell>` if not in mockup-ui
- `<Field>` — confirm; lift from Sprint 57.34 orchestrator promotion
- `<Badge>` — confirm; lift from Sprint 57.24's `<RiskBadge>` if not in mockup-ui
- `<KvRow>` — NEW (from mockup `page-governance.jsx:265`); add to `mockup-ui.tsx` for reusability

### 3.5 D-DAY0-1: route-sweep mock fix

`frontend/scripts/route-sweep.mjs` line ~177-185: in the default `[]` mock branch, add a specific check:
```js
if (/\/governance\/approvals/.test(url)) return json({ items: [] });
```
This eliminates the mock artifact "Failed to load approvals" banner in future audits. Document as MHist entry + commit message rationale.

### 3.6 HEX_OKLCH_BASELINE envelope

Current baseline 45 (post FIX-017). Sprint 57.40 bump estimate:
- Selected row highlight `oklch(from var(--primary) l c h / 0.08)`: +1
- 4 KPI deltaDir up/down arrows + colors: +2
- 5-tab count badges (active/approved/rejected colored): +2
- Detail pane `var(--warning)` SLA highlight + `var(--tool)` mono tool name: +0 (already token-based)

Total expected: **+3-6** → target ≤51 (set `check-mockup-fidelity.mjs` `HEX_OKLCH_BASELINE` to 51 max).

---

## 4. File Change List

### NEW files (5 components + 0-2 specs)

- `frontend/src/features/governance/components/ApprovalsPageHeader.tsx` — ~30 lines
- `frontend/src/features/governance/components/ApprovalsStatsStrip.tsx` — ~45 lines
- `frontend/src/features/governance/components/ApprovalsFilterTabs.tsx` — ~25 lines
- `frontend/src/features/governance/components/ApprovalDetailPane.tsx` — ~120 lines
- `frontend/src/features/governance/components/ApprovalsEmptyTab.tsx` — ~20 lines
- (NEW Vitest specs) `frontend/tests/unit/features/governance/ApprovalsStatsStrip.test.tsx` — +1 spec
- (NEW Vitest specs) `frontend/tests/unit/features/governance/ApprovalDetailPane.test.tsx` — +2-3 specs

### MODIFIED files

- `frontend/src/features/governance/components/ApprovalsPage.tsx` — restructure to 5-component composition (current 73 lines → ~80 lines)
- `frontend/src/features/governance/components/ApprovalList.tsx` — 6-col → 7-col; add `selected` prop + row highlight; refactor `onSelect(id)` semantics (current 102 lines → ~120 lines)
- `frontend/src/components/mockup-ui.tsx` — add `<KvRow>` primitive (+ verify Stat / Card / Field / Badge presence; lift from Sprint 57.24 if missing)
- `frontend/src/features/governance/types.ts` — confirm `ApprovalSummary` has `tool / risk / policy / scope / operator / age / sla_deadline / payload.tool_input / payload.rationale` fields; add types if mockup demands new fields beyond current ApprovalSummary shape
- `frontend/scripts/route-sweep.mjs` — D-DAY0-1 fix: specific `/governance/approvals` mock returning `{items: []}` + re-point `OUT_DIR` to `sprint-57-40-governance-full-rebuild`
- `frontend/scripts/check-mockup-fidelity.mjs` — `HEX_OKLCH_BASELINE` 45 → ≤51 (set actual on Day 2 close)
- `frontend/tests/unit/features/governance/ApprovalList.test.tsx` (if exists) — adapt to 7-col + new SevDot column
- `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` — Day 3 closeout: mark `/governance` verdict ✅ PARITY post-rebuild

### DELETED files (decided Day 1)

- (optional) `frontend/src/features/governance/components/DecisionModal.tsx` — orphan delete per Karpathy §3 IF Detail pane fully replaces modal flow

### Cross-domain

- `memory/project_phase57_40_governance_full_rebuild.md` — sprint subfile
- `memory/MEMORY.md` — quality pointer (~300 char)
- Sprint plan + checklist + progress.md + retrospective.md (this file + checklist + execution files)
- `.claude/rules/sprint-workflow.md` — §Scope-class multiplier matrix `frontend-mockup-strict-rebuild` row: append Sprint 57.40 as 6th data point
- `claudedocs/1-planning/next-phase-candidates.md` — mark Sprint 57.40 rebuild complete; carryover list 5 → 4 🟡 CATASTROPHIC

---

## 5. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | `/governance/approvals` visual matches mockup `localhost:8080/#approvals` | Day 2.5 fidelity verdict ✅ PARITY (or worst-case 🟡 NEAR-PARITY with minor cosmetic notes) |
| AC2 | `.page-head` shows "HITL Approvals" title + sub + route-pill + Teams sync / Export | Day 2.5 PNG visual |
| AC3 | 4 KPI cards visible: Active queue / p50 approval time / Approved 24h / Rejected 24h | Same |
| AC4 | 5-tab nav: Active(N) / Approved / Rejected / Expired / Policies | Same |
| AC5 | 2-col grid (1fr 420px): Pending list left + Detail pane right | Same |
| AC6 | Row click updates Detail pane in-place (highlight + content swap) — NO modal popup | Manual interaction test or Vitest spec |
| AC7 | Detail pane 7 KvRow + Tool input payload + Agent rationale + 4 buttons | Same |
| AC8 | Approve button wires to `useApprovalDecide` mutation; invalidates `APPROVALS_QUERY_KEY` | Vitest mock + manual click |
| AC9 | Reject button same wire | Same |
| AC10 | Approve with edits + Escalate render AP-2 banner | Manual visual |
| AC11 | 4 empty tabs (Approved/Rejected/Expired/Policies) render AP-2 banner placeholder | Manual click each tab |
| AC12 | route-sweep `/governance/approvals` mock returns `{items: []}` (D-DAY0-1 fix) | Re-run sweep → no red banner in mock capture |
| AC13 | Vitest ≥478/478 (+4-8 NEW specs allowed) | `npm test -- --reporter=dot` last line |
| AC14 | 22-route sweep: only `/governance` CHANGED; 21 IDENTICAL | progress.md Day 2.5 entry |
| AC15 | mockup-fidelity guard exit 0 (HEX_OKLCH_BASELINE ≤51) | `node frontend/scripts/check-mockup-fidelity.mjs` exit 0 |
| AC16 | DecisionModal disposition decided (delete OR keep for "Approve with edits") | Day 1 D-DAY1-X log entry |
| AC17 | `useApprovals` / `useApprovalDecide` / `governanceService` UNCHANGED | grep diff: 0 lines changed in those 3 files |
| AC18 | Outer 2-tab (Pending Approvals / Audit Log) PRESERVED in `pages/governance/index.tsx` | unchanged outer shell |
| AC19 | Per-domain calibration ratio recorded in retrospective.md §Q2 | 6th data point + matrix update note |
| AC20 | Drift audit report updated `/governance` ✅ PARITY post-rebuild | `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` edited |

---

## 6. Deliverables

- [ ] `ApprovalsPageHeader` + `ApprovalsStatsStrip` + `ApprovalsFilterTabs` + `ApprovalDetailPane` + `ApprovalsEmptyTab` components shipped
- [ ] `ApprovalsPage` restructured to 5-component composition
- [ ] `ApprovalList` upgraded to 7-col with SevDot + selected highlight
- [ ] `mockup-ui.tsx` extended with `<KvRow>` primitive (+ any other lifts)
- [ ] DecisionModal disposition: deleted OR kept for "Approve with edits" (decision recorded D-DAY1-X)
- [ ] route-sweep.mjs D-DAY0-1 fix applied + OUT_DIR re-pointed
- [ ] 22-route sweep before/after diff reviewed; verdict logged
- [ ] retrospective.md Q1-Q7 with calibration ratio computed (6th data point)
- [ ] `.claude/rules/sprint-workflow.md` §matrix `frontend-mockup-strict-rebuild` row updated
- [ ] Memory subfile + MEMORY.md pointer entry per Sprint Closeout Update Policy
- [ ] PR opened against main; CI green; squash-merge ready
- [ ] Drift audit report `/governance` verdict updated ✅ PARITY

---

## 7. Risks & Mitigations

| Risk | Class | Mitigation |
|------|-------|-----------|
| Mockup `<Stat>` / `<Card>` / `<Field>` / `<Badge>` / `<KvRow>` primitives missing from `mockup-ui.tsx` → lift overhead | Primitive lift scope blowout | Day 0 Prong 2 grep `mockup-ui.tsx` exports; pre-budget +30 min per missing primitive in Day 1 |
| `ApprovalSummary` type lacks `payload.tool_input` / `payload.rationale` / `policy` fields → backend response shape mismatch | Data model gap | Day 0 Prong 2 grep `types.ts` + `backend/src/api/v1/governance/router.py` response schema; if missing, accept fixture for those fields with AP-2 banner OR Day 0 backend extend (defer per CLAUDE.md §1.4 Hard Constraint) |
| Vitest specs assert old class names → break on rebuild | Spec fragility | Prefer `getByRole` / `getByText` / `data-testid` selectors over class-based assertions (per Sprint 57.37 D-DAY3-1 class-swap-resilient convention) |
| Detail pane in-place interaction breaks DecisionModal-asserting specs | Spec adaptation | Day 2 spec migration: replace modal-open assertions with detail-pane content assertions |
| 5-tab approved/rejected/expired/policies require backend filter endpoints not yet shipped | Feature-completeness | Accept AP-2 BackendGapBanner per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint; log carryover AD for next backend-pair sprint |
| Route-sweep mock fix accidentally breaks other endpoints | CI regression | Specific URL regex; non-matching falls back to default `[]`; smoke test before commit |
| HEX_OKLCH_BASELINE bump exceeds +6 envelope | Mockup-fidelity guard | Update guard threshold to actual count; document in commit; bump >6 = signal for primitive consolidation (carryover AD candidate) |
| Day 0 Prong 1/2 path drift → plan §Technical Spec inaccurate | Plan-vs-repo drift (Sprint 53.7 D4-D12 class) | Drift catalogue + plan §1.x amend in progress.md; scope confirm with user before Day 1 |
| Risk Class A: paths-filter vs `required_status_checks` | CI infra (recurring per sprint-workflow §Common Risk Classes A) | Touch `.github/workflows/backend-ci.yml` header comment if backend-ci skips on frontend-only PR |
| Single-domain agent-delegation budget overruns | Agent-delegation scope | Day 1 = primitives + components (1 agent invocation); Day 2 = Detail pane + Vitest specs + route-sweep fix (2nd agent invocation OR human-direct) |
| Per AD-Plan-5 Prong 2.5: child-component-tree depth audit | Child tree drift | Day 0 enumerate `features/governance/components/*` + grep shadcn-utility residue (post FIX-015 should be 0); confirm no AP-Phase2-A/B/C anti-patterns |

---

## 8. Workload

**Bottom-up est** ~19 hr → **calibrated commit ~11.5 hr** (multiplier 0.60 per `frontend-mockup-strict-rebuild` 6th app baseline; 5-pt mean 0.96)

### Day-by-day allocation

| Day | Focus | Bottom-up | Calibrated |
|-----|-------|-----------|------------|
| Day 0 | Plan + checklist drafted (mirror 57.39) + 三-prong (Prong 1 path + Prong 2 content + Prong 2.5 child tree + Prong 3 N/A) + before baseline + D-DAY0-1 mock-fix decision + DecisionModal disposition Q | ~3.5 hr | ~2.1 hr |
| Day 1 | NEW primitives (KvRow + lift any missing) + 5 NEW components (ApprovalsPageHeader / StatsStrip / FilterTabs / DetailPane / EmptyTab) + ApprovalsPage restructure + ApprovalList 7-col upgrade. Agent-delegated (7th consecutive code-implementer pattern). | ~8 hr | ~4.8 hr |
| Day 2 | Vitest spec migration (+4-8 NEW specs); DecisionModal disposition execute (delete or keep-and-refactor); route-sweep D-DAY0-1 mock fix; mockup-fidelity guard threshold update; drift audit report `/governance` verdict update | ~5 hr | ~3.0 hr |
| Day 2.5 | Capture after baseline + 22-route sweep diff review + fidelity verdict for /governance | ~1.5 hr | ~0.9 hr |
| Day 3 (closeout) | Retro Q1-Q7 + calibration ratio (6th data point) + matrix update + memory subfile + push + PR | ~1 hr | ~0.6 hr |

---

## 9. Dependencies

- Sprint 57.39 merged main (closed by PR — `/governance` + `/verification` + `/redaction` + `/error-policy` Phase-2 token re-point); PREREQUISITE for the "existing Tailwind utility classes already token-aligned" baseline state of `pages/governance/index.tsx`
- FIX-015 merged main (closed by PR #183) — child components shadcn-utility residue removed; PREREQUISITE for clean rebuild starting point
- FIX-017 merged main (closed by PR #187) — risk colour map normalized to `var(--risk-X)` tokens; PREREQUISITE — `ApprovalList` RISK_COLOR_CLASS lookups already token-based, no rework needed
- FIX-018 merged main (closed by PR #188) — route-sweep auto-derive from routes.config.ts; PREREQUISITE — future PROP→real promotions in /governance category auto-sync to sweep
- 2026-05-25 drift audit `claudedocs/5-status/drift-audit-2026-05-25/audit-report.md` — Sprint 57.40 selected as priority #1 (or #3 if AC1/2 "fix data-fetch + chat-v2 rename" done first); user 2026-05-25 confirmed Option 2 (full rebuild)
- mockup source `reference/design-mockups/page-governance.jsx:283 Approvals` (~125 lines) — frozen reference design
- 4-layer mockup-fidelity protocol (Sprint 57.28 foundation) intact: `styles-mockup.css` byte-identical; tailwind bridge; theme toggle; CI guard
- `mockup-ui.tsx` primitives (per Sprint 57.34 promotion) — `<Tabs>` confirmed; `<Stat>` / `<Card>` / `<Field>` / `<Badge>` / `<KvRow>` to confirm Day 0 Prong 2 / lift Day 1 if missing
- next-phase-candidates.md updated 2026-05-25 to reflect drift audit findings

---

**Status**: drafted Day 0; awaiting user review of plan + checklist before Day 1 code start

**Modification History**:
- 2026-05-25: Initial draft Day 0 (Sprint 57.40)
