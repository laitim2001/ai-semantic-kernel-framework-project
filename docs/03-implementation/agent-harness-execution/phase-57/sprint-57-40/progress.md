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

## Day 1 — 2026-05-25 (planned) — Primitives + 5 NEW components + ApprovalsPage restructure + ApprovalList upgrade

*To be filled during/after Day 1 work.*
