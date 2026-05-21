# Sprint 57.27 Progress — AD-Mockup-Fidelity-Rebuild-Overview

**Class**: `frontend-mockup-strict-rebuild` 0.60 (4th application; rich-dashboard sub-class DECISION sprint)
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-27-plan.md`
**Checklist**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-27-checklist.md`

---

## Day 0 — Plan + Checklist + 三-prong + Prong 5 — 2026-05-21

### Today's Accomplishments

- **Plan + checklist drafted** — 13-section plan + Day 0-3 checklist mirror Sprint 57.25 structure.
- **Branch** `feature/sprint-57-27-overview-rebuild` created from main `fb27df73`.
- **`/overview` drift diagnosis** (pre-sprint, this session) — Playwright MCP computed-style + screenshot comparison confirmed Sprint 57.26 foundation tokens are live on 3007 (`html 13px` / `radius 8px` / `main padding 28-24`) but per-route content fidelity (widget font classes, colours, missing sparklines / axis labels) needs the rebuild. User directed `/overview` as the Sprint 57.27 target.
- **Agent exploration** — mapped mockup `page-overview.jsx` 9-widget inventory + production `OverviewPage.tsx` (728-line all-in-one close port) + 16-drift list (D1-D16).
- **Day 0 三-prong + Prong 5 complete** — 8 D-PRE findings catalogued below.

### Day 0 三-prong findings (D-PRE)

| ID | Prong | Finding | Implication |
|----|-------|---------|-------------|
| D-PRE-1 | 1 path | `frontend/src/features/overview/` directory does NOT exist | All 7 NEW widget components + `__fixtures__/` are genuinely new; Day 1 creates the directory. Plan already anticipated ("exists or needs creation") → confirmed creation. No scope change. |
| D-PRE-2 | 4 selector | `visual-regression.spec.ts` has **NO `/overview` snapshot** (6-route list = app-shell / auth-login / cost-dashboard / governance / verification-recent / admin-tenants) | Plan R5 + AC#11 + checklist 3.3 ("regenerate `/overview` visual baseline") premise is WRONG — `/overview` is not in visual-regression coverage. Consequence: (a) the rebuild will NOT trigger a Sprint-57.26-style visual-regression CI failure (risk REMOVED); (b) Sprint 57.27 MAY optionally ADD `/overview` to the spec to gain coverage. Decision deferred to Day 3 (US-D3). Plan §Risks updated. |
| D-PRE-3 | 1 path | Existing overview spec lives at `tests/unit/pages/overview/OverviewPage.test.tsx`; plan §File Change List wrote NEW specs under `tests/unit/overview/` | NEW widget specs should land under `tests/unit/features/overview/` (aligns with the widget components' `features/overview/components/` location); existing OverviewPage spec stays at `tests/unit/pages/overview/`. Path corrected — catalogued here, not silently rewritten in plan body (§Step 2.5). |
| D-PRE-4 | 2 content | `PageHead` has props `title / subtitle / routePath / badges / actions` — **no dedicated mono-meta slot** | Plan R1 confirmed. mockup `page-overview.jsx:77-81` renders route-pill + mono `acme-prod · operator · {clock}` INSIDE `.page-sub`. Resolution: pass the mono line as part of the `subtitle` ReactNode (PageHead `subtitle` is ReactNode) — no shared-primitive extension needed (Karpathy §2). |
| D-PRE-5 | 2 content | `CardShell` card-title uses `text-sm` (14px); mockup `.card-title` = **12.5px**. `StatCard` padding `px-4 py-3.5` = 16/14px ≈ mockup `.stat` `14px 16px` (OK). `CardShell` radius `rounded-[12px]` = 12px (visually OK vs token-purity). | **D8 (card-title size) lives INSIDE the shared `CardShell` primitive, not in OverviewPage.** Fixing it touches `CardShell.tsx` which `/cost-dashboard` (57.24) + `/sla-dashboard` (57.25) also consume. **Day 1 decision** (new R9): (a) change shared `CardShell` title to `text-[12.5px]` — fixes all 3 dashboards toward mockup, requires Day 2/3 re-verify of cost/sla; or (b) leave `CardShell` and log a shared-primitive token-audit carryover. Default lean: (a) — it is a correction, not a regression; re-verify is cheap (Vitest + Playwright). |
| D-PRE-6 | 2 content | `Loop` type (`features/loops/types.ts`) has `session_id / status / started_at_ms / ended_at_ms / turn_count / token_usage / total_cost_usd` — **NO `agent_name` / `model` / `max_turns`** (backend Session ORM gap; existing `AD-Loop-Session-Enrich-Phase58`) | Plan D4 ("loop row agent + session + tenant + model") CANNOT fully close. ActiveLoopsCard renders the mockup 5-col layout but `agent_name` / `model` are placeholder strings (the existing type-file header already mandates this pattern); `max_turns` stays hardcoded (D15). tenant comes from auth context. D4 reclassified: **layout closed; agent_name/model placeholder pending AD-Loop-Session-Enrich-Phase58**. ActiveLoopsCard gets an inline note or shares the existing AD reference. |
| D-PRE-7 | 4 selector | Existing `OverviewPage.test.tsx` has 6 tests; test 1 asserts page title via `AppShellV2 pageTitle` prop (`data-page-title="Overview"`), test 5 asserts loop row `"11111111…"` truncated id + `"18,420 tok"` | Rebuild changes both: D1 moves the title in-page (test 1 must adapt — and the AppShellV2 topbar-title decision per R7), D4 changes loop-row content (test 5 must adapt). Existing-spec adaptation is larger than a selector tweak — US-D2 scope note. |
| D-PRE-8 | 5 audit | Sprint 57.22 AUDIT-REPORT Unit 7 `/overview`: severity **COSMETIC**, strict score **60%**, est **3-4 hr**. BUT the report's claim "mockup has NONE in main body" + action "Remove h1 Overview" is **WRONG** — mockup `page-overview.jsx:76` has `<div className="page-title">`. | Two takeaways: (1) plan D1 "render in-page title" is CORRECT — the AUDIT-REPORT Unit 7 page-title judgement is a verified error; do NOT follow its "Remove h1" action. (2) AUDIT severity COSMETIC + 3-4 hr vs plan bottom-up ~6.5 hr — the gap is the AP-3 primitive migration + 7-component extraction, which the AUDIT's "cosmetic" lens did not cost; plan workload kept (user directed a full rebuild, not a cosmetic patch). |

### Go / no-go for Day 1

Scope shift from the 8 D-PRE findings is **< 20%** (mostly assumption corrections + path fixes; D-PRE-2 removes a risk, D-PRE-6 slightly narrows D4). **Continue to Day 1.** Plan §Risks updated with D-PRE-5 (R9 shared-primitive decision) + D-PRE-2 + D-PRE-6; plan §Technical Spec / §Drift map / §File Change List bodies NOT silently rewritten (§Step 2.5 audit-trail discipline) — corrections live in this Day 0 catalogue.

### Day 0 commit

- Commit: plan + checklist + 三-prong + DRIFT skeleton + progress.md Day 0 + Sprint 57.26 checklist §3.4 fold
