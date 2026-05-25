# Sprint 57.40 — Progress

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-40-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-40-checklist.md)

---

## Day 0 — 2026-05-25 — Plan + Checklist + 三-prong verify + before baseline

### Scope confirmation

Single-domain `frontend-mockup-strict-rebuild` (6th data point post Sprint 57.23/24/25/27/37; 5-pt mean 0.96 in-band middle).

Resolves drift audit 2026-05-25 `/governance` CATASTROPHIC verdict via full structural rebuild per mockup `page-governance.jsx:283 Approvals` (HITL Approvals 4-KPI + 5-tab + 2-col Pending/Detail).

### Drift findings

#### D-DAY0-1 — route-sweep mock artifact (NOT real bug) — scope reduction

**Finding**: The "Failed to load approvals: ["governance","approvals"] data is undefined" red banner observed in the 2026-05-25 drift audit `/governance` screenshot is a **route-sweep mock artifact**, NOT a real production bug.

**Root cause**: `frontend/scripts/route-sweep.mjs` default mock returns `[]` (array) for unmatched `/api/v1/*` URLs. `governanceService.listPending` parses response as `PendingListResponse { items: ApprovalSummary[] }` then returns `body.items`. When the mock returns `[]` (array), `[].items === undefined` → TanStack Query treats `undefined` data as an error and surfaces `["governance","approvals"] data is undefined` message.

**Real backend**: `backend/src/api/v1/governance/router.py` `GET /approvals` returns proper `PendingListResponse{items, count}` shape (verified Day 0). Production with real backend never triggers this banner.

**Implication / scope adjustment**:
- Original audit estimate "fix data-fetch runtime error 2-3 hr" reduced to "add specific `/governance/approvals` mock to route-sweep.mjs returning `{items: []}` shape — 30 min"
- Saves ~2 hr from sprint budget
- Production code change: **0 lines** (the bug doesn't exist in real backend path)
- Test infrastructure change: **1 line in route-sweep.mjs** Day 2

#### D-DAY0-2 — E2E approvals.spec.ts will break on rebuild

**Finding**: `frontend/tests/e2e/governance/approvals.spec.ts` asserts modal-flow:
- `getByRole("button", { name: "Review" })` — row-level "Review" buttons will be REMOVED in rebuild (mockup uses row `onClick` → updates Detail pane in-place; no "Review" button)
- `getByRole("dialog")` + `getByRole("textbox").fill(...)` — DecisionModal dialog assertions will FAIL if DecisionModal is deleted OR is only triggered from "Approve with edits" / "Reject" in Detail pane (different button labels)
- `getByRole("heading", { name: "Pending Approvals" })` — mockup uses **"HITL Approvals"** as primary title; "Pending approvals" becomes a Card subtitle in the 2-col grid (assertion needs update)

**Implication**: Day 2 e2e migration required. Either:
- **Option A** (delete DecisionModal): e2e rewritten to use in-place Detail pane interaction (`getByRole("row")` → click → wait for Detail pane content → click "Approve & continue" / "Reject" button in pane)
- **Option B** (keep DecisionModal for "Approve with edits" + "Reject" reason capture): e2e mostly preserved; "Review" button click replaced with click "Approve with edits" or "Reject" button in Detail pane → dialog still opens

**Decision deferred to Day 1** — agent will make call based on actual Detail pane mockup interaction (Approve & continue button vs Reject button) — see Plan §1.4 + US-6.

#### D-DAY0-3 — `ApprovalSummary` type lacks several mockup fields

**Finding**: Production `ApprovalSummary` (`features/governance/types.ts`) has:
- `request_id` ✅ (mockup `id`)
- `session_id` ✅ (mockup `session`)
- `requester` ✅ (mockup `operator` proxy)
- `risk_level` ✅ (mockup `risk`)
- `payload.tool_name` ✅ (mockup `tool`)
- `payload.tool_arguments` ✅ — used as `Tool input payload` JSON pre block
- `payload.reason` ✅ — usable as `Agent rationale`
- `sla_deadline` ✅ (mockup `sla`)

Mockup uses additional fields **NOT in production type**:
- `session_title` (e.g. "payment-gateway 5xx spike") — derived field, NOT in ApprovalSummary
- `agent` (e.g. "incident-responder") — not in type; may be derivable from `context_snapshot`
- `policy` (e.g. "always_ask", "ask_once") — not in type
- `scope` (e.g. "tenant.acme-prod") — `tenant_id` available but as ID not scope label
- `since` / `age` (e.g. "0m 14s") — computable from `sla_deadline` vs now BUT not exposed as a direct field
- `domain` (e.g. "incident", "audit") — not in type

**Implication**: Per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint: "後端尚未支援的 widget → 仍依 mockup 視覺實作，data 用 fixture". Approach:
- Render mockup-equivalent visual using deterministic fixture values derived from available fields (e.g. `session_title` = first 40 chars of `payload.summary ?? payload.reason ?? session_id`; `agent` = "incident-responder" default; `policy` = "always_ask" default; `scope` = `tenant_id`; `since` computed from `Date.now() - (Date.parse(sla_deadline) - duration_default)`; `domain` = "incident" default)
- Mount AP-2 BackendGapBanner explaining the fixture origin (carryover AD for next backend-pair sprint to extend `ApprovalSummaryDTO`)
- NO blocking on backend — sprint proceeds frontend-only per CLAUDE.md §1.4

#### D-DAY0-4 — mockup-ui primitives 7/8 present, only `KvRow` missing

**Finding**: `frontend/src/components/mockup-ui.tsx` exports:
- `Badge` (L453) ✅
- `Card` (L473) ✅
- `Stat` (L510) ✅
- `SevDot` (L577) ✅
- `RiskBadge` (L582) ✅
- `Tabs` (L611) ✅
- `Field` (L649) ✅

**Missing**: `KvRow` (mockup `page-governance.jsx:265-272`) — needed by Detail pane (7 KvRow for tool/risk/policy/scope/operator/age/SLA remaining).

**Implication**: Day 1 includes +15 min KvRow lift to `mockup-ui.tsx`. Plan §3.4 already anticipates this.

#### D-DAY0-5 — Prong 2.5 child component tree CLEAN

**Finding**: `grep "bg-card|text-foreground|border-border|bg-muted|text-muted-foreground"` on `features/governance/components/*.tsx` returns 3 hits — all are FIX-015 MHist historical reference comments (line 20/25/36), NOT real shadcn-utility residue.

**Implication**: Post FIX-015 child component tree is verbatim-aligned. Rebuild starts from clean baseline.

#### D-DAY0-6 — NO existing component-level Vitest specs

**Finding**: `grep` revealed only **hook** + **e2e** specs (`useApprovals.test.tsx` + `useApprovalDecide.test.tsx` + `approvals.spec.ts`). No `ApprovalList.test.tsx` or `ApprovalsPage.test.tsx`.

**Implication**: Day 2 NEW Vitest specs are **all greenfield** — no migration of existing component specs needed. +4-8 NEW specs targets: `ApprovalsStatsStrip` / `ApprovalDetailPane` / `ApprovalsFilterTabs` / `ApprovalsEmptyTab`. Existing hook specs (`useApprovals` / `useApprovalDecide`) unchanged — wiring preserved per Plan §1.2.

### Day 0 go/no-go

Scope shift sum: ~5% reduction from audit estimate (D-DAY0-1 saves ~2 hr; D-DAY0-4 KvRow adds ~15 min net). Within ≤20% threshold → **CONTINUE Day 1**.

### Day 0 actual hr vs ~2.1 calibrated est

Planning + verify totalled ~2 hr (within 5% of estimate). Calibration calibrated baseline 0.60 holds.

---

## Day 1 — 2026-05-25 — Primitives + 5 NEW components + ApprovalsPage restructure + ApprovalList upgrade (agent-delegated 7th consecutive)

### Outcome

**Agent ship**: 5 NEW components + 1 NEW primitive lift + 2 REBUILD + 1 DELETE — committed as `fc4636e3` in ~40 min agent wall-clock.

| File | Type | Lines | Note |
|------|------|-------|------|
| `ApprovalsPageHeader.tsx` | NEW | ~30 | mockup `.page-head` |
| `ApprovalsStatsStrip.tsx` | NEW | ~50 | 4 KPI; Active real / 3 fixture + AP-2 banner above strip |
| `ApprovalsFilterTabs.tsx` | NEW | ~50 | 5-tab nav controlled component; exports `TabId` |
| `ApprovalDetailPane.tsx` | NEW | ~170 | KvRow × 7 + Tool input payload + Agent rationale + 4 buttons; empty state |
| `ApprovalsEmptyTab.tsx` | NEW | ~55 | 4-tab × AP-2 placeholder |
| `mockup-ui.tsx` | MODIFY | +21 | `<KvRow>` primitive added |
| `ApprovalsPage.tsx` | REBUILD | 73→115 | 5-component composition + `selected` state for in-place Detail pane |
| `ApprovalList.tsx` | REBUILD | 102→131 | 6-col → 7-col (+ SevDot + selected highlight + row onClick replaces Review modal + RiskBadge usage); `RISK_COLOR_CLASS` deleted (moved into RiskBadge primitive) |
| `DecisionModal.tsx` | DELETE | -186 | orphan per Karpathy §3 (Detail pane covers Approve/Reject; "Approve with edits" deferred Phase 58+) |

**Verification status post agent commit**:
- TypeScript strict: 0 errors ✅
- ESLint: clean (3 pre-existing `TSSatisfiesExpression` warnings unrelated) ✅
- Vitest 478/478 (96 files) ✅ — D-DAY1-1 positive surprise: NO spec migration needed (validates Sprint 57.37 D-DAY3-1 class-swap-resilient text/role/data-testid convention)
- Vite build: clean 3.25s ✅

### Drift findings

#### D-DAY1-1 — Browser smoke check exposes apparent `roles[0]` undefined crash (revised root cause to mock fixture bug)

**Initial symptom**: Browser-rendering /governance after agent commit showed ErrorBoundary banner "Something went wrong — Cannot read properties of undefined (reading '0')". Stack trace pointed to `Sidebar.tsx:59:25` then later iterations to `Topbar.tsx:88:26` + `OverviewPageInner.tsx:88:18` + `UserMenu.tsx:137:22`. All these are unrelated to Sprint 57.40 scope (rebuild only touched `features/governance/` + `mockup-ui.tsx` KvRow add).

**Investigation chronicle**:
1. Hypothesis A: agent broke something — `git diff fc4636e3^ fc4636e3` confirms ONLY governance + KvRow touched; Sidebar/Topbar/OverviewPage untouched
2. Hypothesis B: HMR stale state — git checkout HEAD~2 restore + retest → SAME crash → not HMR
3. Hypothesis C: Sidebar/Topbar/OverviewPage all do `const userRole = roles[0] ?? "operator"`; if `roles` undefined → throws; defensive guards applied (Sprint 57.33 page-bug-fix pattern) → still crashed with same error on a different component
4. ROOT CAUSE (D-DAY1-2 below): my Playwright mock fixture was LIFO-naive — broader regex `/\/api\/v1\//` shadowed specific `/auth/me/` handler

**Resolution**: NOT a real production bug. After fixing the Playwright fixture per route-sweep.mjs `r.fallback()` pattern → production renders cleanly (see `day1-rebuild-success.png` evidence). Defensive guards reverted to keep Sprint 57.40 commit scope clean. Tracked as carryover AD for hardening sprint (defensive guards on shell components for hypothetical malformed `/auth/me` response — separate FIX scope).

#### D-DAY1-2 — Playwright `ctx.route()` matching is LIFO (last-registered-wins)

**Finding**: When multiple `ctx.route()` handlers match the same URL, Playwright invokes the **last registered** one first. My Day 1 smoke-check fixture registered `/\/api\/v1\/auth\/me/` first then `/\/api\/v1\//`. The broader regex (registered later) matched `/api/v1/auth/me` requests first, returning `[]` instead of the proper `AuthMeResponse` shape. Auth store then set `roles: undefined` from the malformed response → downstream components accessing `roles[0]` crashed.

**Resolution pattern** (mirrors `frontend/scripts/route-sweep.mjs:170-185`):
```js
ctx.route(/\/api\/v1\/auth\/me/, /* specific handler */);
ctx.route(/\/api\/v1\//, r => {
  const url = r.request().url();
  if (/\/auth\/me/.test(url)) return r.fallback();  // ← fall through to specific
  // ... other URL-specific branches
  return r.fulfill({ /* default */ });
});
```

**Implication for Sprint 57.40 Day 2 + future audits**:
- The 2026-05-25 drift audit's `/governance` red banner "Failed to load approvals: data is undefined" was ALSO this same Playwright mock artifact (D-DAY0-1 + D-DAY1-1 same root cause)
- The route-sweep.mjs `r.fallback()` pattern is the canonical reference for any new Playwright-based audit fixture
- Day 2 task: add specific `/governance/approvals` mock returning `{items: [...], count: N}` shape so future audits don't show the false-positive red banner (this was a misdiagnosis in the drift audit report — `/governance` does have a backend, not a bug)

#### D-DAY1-3 — DecisionModal disposition: Option A (delete) chosen

Agent chose Option A: deleted `DecisionModal.tsx` per Karpathy §3 "你的改動產生的 orphan 才清". Rationale:
- Detail pane fully covers Approve & Reject buttons via existing `useApprovalDecide` mutation
- "Approve with edits" + "Escalate to L2" are Phase 58+ features rendered as AP-2 stubs (`alert(...)` placeholder); when shipped will use new lightweight inline form OR re-introduce a modal at that time
- 3 stale doc-only references remain in `src/components/ui/dialog.tsx:22` + `src/features/governance/hooks/useApprovalDecide.ts:3,12,29` + `src/features/guardrails/README.md:13` — non-blocking; Day 2 mop-up cleanup OR leave for future sprint (low priority)

### Day 1 actual hr vs ~4.8 calibrated est

- **Calibrated commit**: ~4.8 hr (Day 1 per plan §8)
- **Agent wall-clock**: ~40 min (1 code-implementer session)
- **Investigation overhead** (D-DAY1-1 / D-DAY1-2 debug cycle): ~30 min by human pilot
- **Total actual**: ~1.2 hr
- **Ratio actual/calibrated**: ~0.25 (well below 0.60 baseline; 3rd consecutive data point for `AD-Sprint-Plan-Agent-Delegation-Factor-Modifier` proposal — Sprint 57.39 `-with-extras` 0.41 + FIX-015 ~0.04 + Sprint 57.40 Day 1 ~0.25)

**Note**: agent delegation effective speedup ~5-7× vs human-rewrite cadence; the modifier proposal continues to accumulate evidence

### Day 1 verification screenshots

- `screenshots/day1-rebuild-success.png` — production /governance/approvals with `r.fallback()` mock pattern; mockup-fidelity verdict ✅ PARITY (matches mockup `#approvals` 4-KPI + 5-tab + 2-col Pending list + Detail pane empty state)

### Carryover ADs

1. **`AD-Shell-Defensive-Guards-For-Malformed-AuthMe`** — defensive `(roles ?? [])[0] ?? "operator"` + `user?.display_name?.charAt(0) ?? "?"` patterns on Sidebar / Topbar / OverviewPage / UserMenu hardening for hypothetical malformed backend response. Not a real bug today; Sprint 57.33 page-bug-fix class precedent suggests this is good practice but out of scope for Sprint 57.40 rebuild. ~30 min FIX-019 candidate.
2. **`AD-Playwright-Mock-LIFO-Fixture-Convention`** — codify the `r.fallback()` pattern in `.claude/rules/testing.md` so future audit scripts don't repeat the LIFO-naive mistake. Cross-ref `frontend/scripts/route-sweep.mjs:170-185` canonical example.
3. **`AD-DecisionModal-Doc-References-Mop-Up`** — clean 3 stale doc-only references in dialog.tsx + useApprovalDecide.ts + guardrails README. Low priority; bundle with next governance touch.

### Day 1 commit references

- `fc4636e3` — agent ship: 5 NEW components + KvRow + ApprovalsPage + ApprovalList rebuild + DecisionModal delete
- `fa7cac66` — Day 0 docs sync (plan + checklist + progress.md initial + route-sweep OUT_DIR)

---

## Day 2 — 2026-05-25 (planned) — Vitest specs + route-sweep mock fix + threshold update + drift audit report update

*To be filled during/after Day 2 work.*
