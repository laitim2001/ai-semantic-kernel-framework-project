# Sprint 57.40 — Retrospective

**Sprint id**: 57.40
**Sprint name**: `/governance` Approvals view Full Mockup-Fidelity Rebuild (Domain A only — closes drift audit 2026-05-25 #3 priority)
**Branch**: `feature/sprint-57-40-governance-full-rebuild`
**Plan**: [`sprint-57-40-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-40-plan.md)
**Closed**: 2026-05-25
**Commits** (branch ahead of main `1b9093d6`): 7 on branch
- `fa7cac66` Day 0 plan + checklist + progress.md + route-sweep OUT_DIR
- `fc4636e3` Day 1 ship — 5 NEW components + KvRow primitive + ApprovalsPage restructure + ApprovalList 7-col upgrade + DecisionModal retire
- `bb5d7cc0` Day 1 progress.md chronicle (D-DAY1-1/2/3)
- `e1b87a06` Day 2 ship — +15 NEW Vitest specs + route-sweep `/governance/approvals` envelope mock + mockup-fidelity baseline 45→46 + drift audit report `/governance` PARITY update
- `fc7ea4c7` Day 2 docs follow-up (checklist tick + progress SHA back-fill)
- `afa51be9` Day 2.5 — after-baseline 24 PNGs + 19 IDENTICAL/5 CHANGED diff + `/governance` ✅ PARITY verdict + 3-way evidence pair
- `<TBD>` Day 3 closeout (this commit)

---

## Q1 — What was the goal? What was actually shipped?

### Goal (per plan §0)

Single-domain `frontend-mockup-strict-rebuild` sprint to close the **drift audit 2026-05-25 #3 priority** (`/governance` 🔴 CATASTROPHIC verdict) via full structural rebuild of the HITL Approvals view per mockup `page-governance.jsx:283 Approvals` (4-KPI strip + 5-tab nav + 2-col Pending/Detail layout). 6th data point for `frontend-mockup-strict-rebuild` 0.60 baseline (5-pt window 57.23/24/25/27/37 = mean 0.96 in-band middle).

### Shipped

- **5 NEW components** in `frontend/src/features/governance/components/`:
  - `ApprovalsPageHeader.tsx` — header strip with title + meta + Teams sync / Export buttons
  - `ApprovalsStatsStrip.tsx` — 4-KPI grid (Active queue real + 3 fixture) + AP-2 BackendGapBanner
  - `ApprovalsFilterTabs.tsx` — 5-tab nav (Active / Approved / Rejected / Expired / Policies) wrapping mockup-ui `Tabs` primitive
  - `ApprovalDetailPane.tsx` — right-col rich Detail pane (request_id mono + 7 KvRow stack + tool input payload + agent rationale + 4-button col Approve & continue / Approve-with-edits / Reject / Escalate)
  - `ApprovalsEmptyTab.tsx` — AP-2 BackendGapBanner placeholder for the 4 non-active tabs
- **1 NEW primitive** added to `frontend/src/components/mockup-ui.tsx`: `KvRow` (verbatim port of `page-governance.jsx:265-272` key-value row component)
- **`ApprovalsPage.tsx` rebuild** (73 → 115 lines): replaced simple 4-element layout with 5-component composition + selected state (`useState<string | null>`)
- **`ApprovalList.tsx` upgrade** (102 → 131 lines): 6-col → 7-col table (SevDot + Session + Tool + Risk + Policy + Operator + SLA); `selected` prop + row highlight; row `onClick` calls parent's `onSelect(approval)` instead of triggering DecisionModal
- **`DecisionModal.tsx` deleted** per Karpathy §3 orphan delete (Detail pane covers Approve/Reject; AP-2 stubs for Approve-with-edits + Escalate)
- **+15 NEW Vitest specs** across 4 spec files (target was +4-8 → **188-375%** over) — see Q3
- **`route-sweep.mjs` envelope mock fix** for `/governance/approvals` (D-DAY0-1 closes audit's false-red-banner artifact)
- **`HEX_OKLCH_BASELINE` bump 45 → 46** for ApprovalList row-highlight literal (mockup-token vocabulary; well within plan §3.6 ≤51 envelope)
- **Drift audit report update** — `/governance` verdict 🔴 CATASTROPHIC → ✅ PARITY; verdict summary 16→17 PARITY / 5→4 CATASTROPHIC; Key finding #5 RESOLVED with root cause; Carryover ADs cleaned
- **3-way evidence pair** staged (BEFORE day0 / AFTER day1 / MOCKUP reference) in `before-after/` for future audit traceability
- **0 backend code changes** (frontend-only sprint as planned)
- **0 spec adapts needed** for Day 1 re-point (Vitest 478 remained 478 stable on Day 1; +15 NEW Day 2 took total to 493)

### Not shipped (scope discipline)

- **`useApprovals` / `useApprovalDecide` / `governanceService` UNCHANGED** per plan §1.3 (preserved real backend wiring)
- **Outer 2-tab shell** in `pages/governance/index.tsx` PRESERVED unchanged per plan §1.3 (Audit Log tab is its own sibling, not yet ported to mockup design)
- **`Approve with edits…` + `Escalate to L2` Detail-pane buttons** — AP-2 alert stubs only; backend gap deferred Phase 58+
- **4 non-active tabs functional** (Approved / Rejected / Expired / Policies) — AP-2 BackendGapBanner placeholders; backend filter endpoints deferred Phase 58+
- **3 KPI real values** (p50 / Approved 24h / Rejected 24h) — fixture with AP-2 banner; backend stats endpoint deferred Phase 58+
- **5 audit-found CATASTROPHIC drifts remaining**: `/memory` / `/verification` / `/admin-tenants` / `/tenant-settings` (post Sprint 57.40 reduced from 5 → 4 with `/governance` closed)

---

## Q2 — Calibration ratio + 6th data point evaluation for `frontend-mockup-strict-rebuild` 0.60 baseline

### Time accounting (best-estimate breakdown)

| Day | Calibrated commit (plan §8) | Actual hr (estimated) | Notes |
|-----|-----------------------------|----------------------:|-------|
| Day 0 | ~1.5 hr | ~0.7 hr | Plan + checklist (mirror 57.39 §0-9 / Day 0-3) + 三-prong + audit + before sweep + commit |
| Day 1 (agent ship) | ~4.8 hr | ~1.2 hr | `code-implementer` agent ~40 min wall-clock for 5 NEW components + KvRow + ApprovalsPage + ApprovalList upgrade + DecisionModal delete; me ~30 min context-setup + verify visual + mock fixture investigation (D-DAY1-1/2 root cause) |
| Day 2 | ~3.0 hr | ~0.85 hr | +15 NEW Vitest specs + route-sweep envelope mock + mockup-fidelity baseline bump + drift audit report update; NOT agent-delegated, surface was narrow |
| Day 2.5 | ~0.9 hr | ~0.4 hr | After sweep 24 PNGs + sha256 diff + verdict + 3-way evidence pair |
| Day 3 (closeout) | ~0.6 hr | ~0.7 hr | Retro + matrix + memory + candidates + CLAUDE.md + push + PR — slight over-plan from full Q1-Q6 narrative depth |
| **Total** | **~10.8 hr (single-class 0.60)** | **~3.85 hr** | |

**Sprint-aggregate `actual_total / committed_total` ratio = 3.85 / 10.8 ≈ 0.36** (BELOW band [0.85, 1.20] by 0.49).

### 6th data point evaluation for `frontend-mockup-strict-rebuild` 0.60 baseline

| App | Sprint | Ratio | Within band? |
|-----|--------|------:|:-------------:|
| 1st | 57.23 (auth-flow rebuild) | 0.59 | ❌ below by 0.26 |
| 2nd | 57.24 v2 (cost-dashboard rebuild) | 1.19 | ✅ top of band |
| 3rd | 57.25 (sla-dashboard rebuild) | 0.88 | ✅ lower middle |
| 4th | 57.27 (overview rebuild) | ~0.95 | ✅ middle |
| 5th | 57.37A (loop-debug rebuild) | ~1.18 | ✅ top of band |
| **6th** | **57.40 (governance rebuild)** | **~0.36** | ❌ **below by 0.49** |

**6-pt mean**: (0.59 + 1.19 + 0.88 + 0.95 + 1.18 + 0.36) / 6 = **5.15 / 6 ≈ 0.86** — drops below the [0.85, 1.20] band lower edge by 0.01 vs prior 5-pt mean 0.96.

**Per `When to adjust` rule** (3+ consecutive < 0.7 required for lower trigger):
- Last 3 ratios: 57.27 ≈ 0.95 (NOT < 0.7) / 57.37A ~1.18 (NOT) / 57.40 ~0.36 (YES)
- Only **1 of last 3** below 0.7 → **lower-trigger NOT met**
- **Decision: KEEP 0.60 baseline** per 3-sprint window rule

### Root cause analysis — 6th data point ratio 0.36 (deepest below-band of class history)

1. **Agent-delegation factor (PRIMARY — same root cause as Sprint 57.39 1st deliberate-test of `-with-extras` 0.65)** — Day 1 was 100% delegated to `code-implementer` agent (7th consecutive code-implementer invocation in epic). Agent wall-clock ~40 min for **5 NEW components + KvRow primitive + ApprovalsPage restructure + ApprovalList 7-col upgrade + DecisionModal delete**. Human-equivalent rewrite would conservatively be ~6-8 hr (5 NEW + 1 primitive + 2 restructures). Bottom-up plan estimate (~12 hr) was based on human-rewrite-time; calibrated 0.60 multiplier doesn't model agent-delegation speedup. Plan §8 calibrated 4.8 hr for Day 1 → actual 1.2 hr → **Day-1-isolated ratio ≈ 0.25**.

2. **Reusable primitive pattern maturity** — Sprint 57.24-57.27 epic extracted 7 reusable primitives (PageHead / Spark / StatCard / AreaChart / BarTrack / CardShell / BackendGapBanner). Sprint 57.40 reused 5 of them + added only 1 new (`KvRow`). Pattern-reuse acceleration vs greenfield estimate.

3. **D-DAY1-1/2 investigation paid off** — The audit's "data is undefined red banner" turned out to be a sweep-mock artifact, not a production bug. Estimated 2-3 hr fix in audit report was reduced to 30 min mock fixture edit. Saved ~1.5-2.5 hr from plan budget.

4. **Day 2 Vitest specs surface was narrow** — 4 stateless / pure-presentation components (StatsStrip / DetailPane / FilterTabs / EmptyTab) all decomposed cleanly into 2-5 tests each via existing `useApprovals.test.tsx` + `QuickActionsStrip.test.tsx` patterns. Bottom-up est ~3.0 hr → actual ~50 min.

### Cross-class pattern note

Sprint 57.40 is the **3rd consecutive sprint with code-implementer agent delegation as primary Day 1 mechanism producing significantly below-band ratio**:

| Sprint | Class | Baseline | Actual ratio | Agent-delegated? |
|--------|-------|---------:|-------------:|:----------------:|
| 57.39 | `-with-extras` | 0.65 | 0.41 | YES (6th+7th consecutive) |
| FIX-015 | bundled FIX | n/a | n/a (~0.04 bottom-up) | YES |
| 57.40 | `mockup-strict-rebuild` | 0.60 | **~0.36** | YES (7th consecutive) |

This is **3 data points** for `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` proposal evidence (logged Sprint 57.39 retro Q4 #4). Per existing proposal's activation rule (3+ consecutive sprints with agent-delegated ratio < 0.7 AND consistent delegation pattern ≥ 80% of Day 1 work via agent), the trigger is now technically met. However:

- 3 data points span **2 different classes** (`-with-extras` + `mockup-strict-rebuild`) — same root cause manifesting across the matrix
- The proposal advocated for a **global multiplicative `agent_factor` coefficient** (Option A) rather than per-class sub-class split (Option B)
- Recommendation: **promote `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` from PROPOSAL to active candidate** for next sprint plan §Workload Calibration; defer activation 1 more sprint to gather a 4th data point before changing the matrix structurally

---

## Q3 — What went well

1. **Agent delegation pattern maturity (7th consecutive code-implementer invocation)** — agent autonomously created 5 NEW components + 1 NEW primitive (`KvRow`) + restructured ApprovalsPage + upgraded ApprovalList from 6-col to 7-col + deleted DecisionModal (Karpathy §3 orphan) in ~40 min wall-clock. Zero corrections required post-agent.

2. **Mockup-fidelity verdict PARITY confirmed via 3-way evidence pair** — production AFTER (115,832 bytes) vs mockup reference (210,672 bytes) structural compare: 7/7 elements match (page-head / AP-2 banner / 4 KPI / 5-tab / 2-col grid / outer 2-tab preserved / sidebar). Differences are data-driven (mock empty list vs hardcoded 4 rows) and AP-2 honesty addition, not structural drift.

3. **D-DAY1-2 root cause investigation prevented wasted effort** — the audit-reported "red banner runtime error" was investigated and traced to `route-sweep.mjs` default `[]` fallback not matching `PendingListResponse {items, ...}` envelope shape; production with real backend is unaffected. Saved ~2-3 hr originally estimated for "data fetch bug fix" in the audit report.

4. **Vitest spec target overshoot** — plan target +4-8 NEW specs → actual **+15** (188-375%). All 15 passing in 1.46s; 1 mid-flight failure (`PII access` text appearing in 2 places per Card subtitle truncation + rationale field) was caught by Vitest and fixed via `getAllByText(...).length >= 1` adjustment.

5. **Mockup-fidelity threshold within envelope** — plan §3.6 envelope was ≤51; actual 46 (+1 from baseline 45 for ApprovalList row-highlight `oklch(from var(--primary) l c h / 0.08)` literal). Mockup-token vocabulary precedent extended (4th consecutive matrix-class app per same convention: 57.30/57.35/57.37/57.38).

6. **0 unintended regressions across 22-route sweep** — 19 IDENTICAL + 1 expected `/governance` CHANGED + 4 noise CHANGED (all sub-300 bytes; topbar live-clock + chat-v2 SSE merge buffer variation; well within historical envelope).

7. **Drift audit report ATA-style closure update** — audit's 6 carryover ADs updated with: 1 CLOSED via Sprint 57.40 (`AD-Governance-Catastrophic-Rebuild-And-Bug-Fix`) + Recommendations 1+3 struck + Key finding #5 marked RESOLVED with root cause + new `AD-RouteSweep-Envelope-Mock-Convention` carryover added for tooling lesson.

8. **Format mirror discipline** — plan + checklist + retrospective mirror Sprint 57.39 structure (10 sections / Day 0-3 numbering with Day 2.5 / Q1-Q5 narrative depth) per sprint-workflow.md §Step 1 format-consistency rule.

---

## Q4 — What to improve next sprint

1. **`AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` — 3rd data point evidence accumulation should promote** (per Q2). The proposal logged Sprint 57.39 retro Q4 #4 has now accumulated 3 data points (57.39=0.41 + FIX-015 outlier + 57.40=0.36). Activation rule's "3+ consecutive sprints with agent-delegated ratio < 0.7" is technically met; however, since these span 2 classes, recommend defer 1 more sprint for a 4th data point in either class before structurally changing the matrix. **AD-action**: keep `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` as active candidate; revisit at Sprint 57.41/42 retrospective Q2.

2. **D-DAY1-1 mock fixture investigation conventions** — the 30-min investigation that traced the audit's "red banner" to a sweep-mock artifact (not a production bug) is a re-usable pattern. When a screenshot or e2e test fails in a way that looks production-bug-like, **first check the mock-fixture layer before assuming production code is broken**. **AD candidate**: codify into `docs/rules-on-demand/testing.md` §Mock Fixture Investigation Pattern.

3. **3 D-DAY1 carryover ADs from Day 1 investigation** (per memory subfile) — `AD-Shell-Defensive-Guards-For-Malformed-AuthMe` (FIX-019 candidate; hypothetical hardening for `/auth/me` shape divergence — not a real bug today but the Sprint 57.33 pattern precedent suggests it's worth pre-emptive guards), `AD-Playwright-Mock-LIFO-Fixture-Convention` (codify `r.fallback()` LIFO pattern in `.claude/rules/testing.md`), and `AD-DecisionModal-Doc-References-Mop-Up` (3 stale doc refs after Karpathy §3 orphan delete: dialog.tsx / useApprovalDecide.ts / guardrails README).

4. **Day 0 Prong 2 child-component tree depth audit** — Sprint 57.40 was simpler than 57.39 in this regard (ApprovalsPage's children were all owned by the same governance feature, and the rebuild was 1st-time mockup-aligned not Phase-2 re-point), so the new Prong 2.5 from sprint-workflow.md (AD-Plan-5 Sprint 57.40 fold-in) didn't surface a drift here. **But the Prong is now codified** for future Phase-2 sprints. **Not an improvement deferment; a confirmation that the Prong codification was timely.**

5. **Plan §8 / checklist `Day 3 actual ~0.7 hr` over-plan` (vs plan ~0.6 hr)** — closeout deliverables (retro narrative depth + 6-doc sync) consistently absorb more hours than estimated. Pattern across 5+ sprints. **Defer**: not actionable until accumulated 8-10 closeout data points then re-baseline closeout from 0.6 → 0.8-1.0 hr.

---

## Q5 — Carryover candidates (next-phase-candidates.md additions)

### 🔚 CLOSED in Sprint 57.40

1. **`AD-Governance-Catastrophic-Rebuild-And-Bug-Fix`** (audit-time 2026-05-25 carryover) — closed via Day 1 agent-delegated rebuild + Day 2 envelope mock fix. Both halves resolved.
2. **drift audit `/governance` red banner false signal** — closed via D-DAY1-2 investigation + Day 2 `/governance/approvals` envelope mock entry.
3. **`AD-Phase-2-Epic-Progress-Bookkeeping`** (audit recommendation #8) — partial close; CLAUDE.md will reflect Sprint 57.40 closure in Day 3 §3.5 minimal touch.

### 🆕 NEW carryover (Sprint 57.41+ candidates)

1. **`AD-Verification-Catastrophic-Rebuild`** (carried from audit + accelerated by Sprint 57.40 pattern reuse) — `/verification` full rebuild to mockup 4-KPI + 2-col Recent + Failure modes/Policy checks sidebar. Class `frontend-mockup-strict-rebuild` 0.60. Est ~8-10 hr. **Pattern-reuse candidate**: 4 of Sprint 57.40's 5 NEW components (StatsStrip / FilterTabs / DetailPane / EmptyTab pattern) transfer with mild rename to verification surface.
2. **`AD-Memory-Layers-Matrix-Rebuild`** (carried from audit) — `/memory` Memory Layers 5×N matrix design rebuild. Est ~10-15 hr.
3. **`AD-AdminTenants-Tenants-Table-Rebuild`** (carried from audit; known CLAUDE.md 🟡 STRUCTURAL Phase 58+ #1) — Tenants table + 4 KPI + 9-col table 9 rows. Est ~12-15 hr.
4. **`AD-TenantSettings-6-Tab-Rebuild`** (carried from audit; known CLAUDE.md 🟡 STRUCTURAL Phase 58+ #2) — 6-tab settings architecture. Est ~15-20 hr (largest scope).
5. **`AD-ChatV2-Inspector-Tab-Rename`** (carried from audit NEAR-PARITY) — Inspector tab rename `Turn/Trace/Memory/Tree` → mockup `Run/Tools/Memory/Verify`. Class `frontend-refactor-mechanical` 0.50. Est ~30 min (quick win).
6. **`AD-Shell-Defensive-Guards-For-Malformed-AuthMe`** (D-DAY1-1 investigation byproduct) — pre-emptive hardening of Sidebar / Topbar / OverviewPage / UserMenu against hypothetical malformed `/auth/me` shape. Sprint 57.33 pattern precedent. FIX-019 candidate. Est ~30 min.
7. **`AD-Playwright-Mock-LIFO-Fixture-Convention`** (D-DAY1-2 investigation byproduct) — codify `r.fallback()` LIFO pattern + envelope-shape mock requirement into `.claude/rules/testing.md`. Est ~30 min.
8. **`AD-DecisionModal-Doc-References-Mop-Up`** (Day 1 Karpathy §3 orphan delete follow-up) — clean 3 stale doc refs to deleted DecisionModal.tsx (dialog.tsx / useApprovalDecide.ts / guardrails README). Est ~15 min.
9. **`AD-RouteSweep-Envelope-Mock-Convention`** (Day 2 audit-report carryover) — codify in `frontend-mockup-fidelity.md` or `testing.md`: any endpoint returning envelope shape (e.g. `{items, total, has_more}`) needs explicit sweep mock entry; default `[]` is only safe for list-shaped endpoints. Grep-pattern + example. Est ~30 min.
10. **`AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` PROMOTION CANDIDATE** (Q2 + Q4 #1 of this retro) — accumulated 3 data points (57.39 + FIX-015 + 57.40 all < 0.7 with agent delegation as primary Day 1 mechanism). Activation rule technically met but spans 2 classes. Defer 1 more sprint for 4th data point before structurally changing matrix. Est ~2 hr to activate.

### Phase-2 epic progress

- **Pre-Sprint 57.40 (post 57.39)**: 15/17 Phase-2 routes shipped / 2 🟡 Phase 58+ STRUCTURAL remaining (`/memory` + `/tenant-settings`)
- **Drift audit 2026-05-25 (uncovered hidden CATASTROPHIC drifts)**: corrected post-audit reality was **~14 PARITY + 1 NEAR-PARITY + 5 CATASTROPHIC + 12 PROP stubs unshipped + 4 DRAFT inactive**
- **Post Sprint 57.40**: **17 PARITY + 1 NEAR-PARITY + 4 CATASTROPHIC** remaining (`/memory` + `/verification` + `/admin-tenants` + `/tenant-settings`); honest 4-of-22 STRUCTURAL count
- **Next sprint candidates (ordered by ROI per audit recommendations 1-6)**:
  1. `AD-Verification-Catastrophic-Rebuild` (highest pattern-reuse ROI from Sprint 57.40 primitives)
  2. `AD-ChatV2-Inspector-Tab-Rename` (30-min quick win)
  3. `AD-Memory-Layers-Matrix-Rebuild`
  4. `AD-AdminTenants-Tenants-Table-Rebuild`
  5. `AD-TenantSettings-6-Tab-Rebuild`

---

## Q6 — Verbatim-CSS protocol compliance check (per plan §3.6)

- **Layer 2 styles-mockup.css diff guard**: 0 (byte-identical to `reference/design-mockups/styles.css` per 57.28 verbatim-CSS foundation)
- **Layer 4 token collision check**: 0 (no new `--sc-X` overrides introduced)
- **`HEX_OKLCH_BASELINE` bump within envelope**: 45 → 46 (+1 ApprovalList row-highlight; plan §3.6 envelope ≤51 — actual +1 well within)
- **mockup-fidelity guard**: `✓ grep guard: 46 hardcoded hex/oklch lines (baseline 46)` PASS
- **Layer 2 diff verbatim guard**: `diff reference/design-mockups/styles.css frontend/src/styles-mockup.css` returns empty (byte-equal)

---

## Q7 — N/A (feature ship NOT spike, per Sprint 57.38 precedent)

No design note extract; this is a Phase 57+ ship sprint, not a spike. 8-Point Quality Gate does not apply.

---

## Modification History

- 2026-05-25: Initial Day 3 closeout retrospective (Sprint 57.40)
