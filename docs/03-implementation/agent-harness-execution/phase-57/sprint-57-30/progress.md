# Sprint 57.30 Progress — Day 0 (2026-05-23)

> Plan: [`../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-30-plan.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-30-plan.md)
>
> Checklist: [`../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-30-checklist.md`](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-30-checklist.md)
>
> Branch: `feature/sprint-57-30-chatv2-shell-repoint`
>
> Base SHA: `2d9d9e9f` (main; Sprint 57.29 squash-merge — PR #163)

---

## Day 0 — Plan + Checklist + 三-prong + before-baseline (PRE-WORK)

### Today's Accomplishments

- §0.1 Plan + Checklist drafted (`sprint-57-30-plan.md` 11 sections + `sprint-57-30-checklist.md` Day 0-5 mirror 57.29 format) — actual ~75 min (template re-read + plan ~50 min + checklist ~25 min)
- §0.2 Day-0 三-prong verify — actual ~25 min (Prong 1 path verify Glob 24 paths; Prong 2 content verify 4 batched greps; Prong 3 N/A; Prong 4 visual-baseline strategy decided)
- §0.3 before-baseline screenshots — **pending dev-server smoke** (need `:3007` + auth `dev-login` to land Day-0 traffic; will run end of Day 0 once frontend mounts cleanly)

### Drift findings

**Prong 1 — Path verify (Glob batched)**:

| # | Finding | Status |
|---|---------|--------|
| — | 23 plan-listed MODIFIED paths all exist in real repo | ✅ no drift |
| — | 1 plan-listed NEW path `hooks/useDismiss.ts` correctly absent | ✅ no drift |

**Prong 2 — Content verify (grep)**:

| ID | Finding | Severity | Action |
|----|---------|----------|--------|
| **D1** | Radix `<DropdownMenu>` consumer = **only** `UserMenu.tsx` (the other 2 results — `ui/dropdown-menu.tsx` + `ui/index.ts` — are wrapper + re-export). CommandPalette + NotificationsPanel + Sidebar do NOT use Radix `<DropdownMenu>`. | 🟢 GREEN | Radix-drop scope contained — Sprint 57.30 only touches `UserMenu.tsx` to drop Radix; the wrapper `ui/dropdown-menu.tsx` becomes orphan candidate after Day 1 — defer cleanup to Day 5 (Karpathy §3: only clean orphans your own changes create). |
| **D2** | `avatarStyle` (36×36, font-size 13) defined once in `UserMenu.tsx:75-80`; reused at **2 distinct semantic sites**: L147 `<button style={avatarStyle}>` (topbar trigger — should be 26×26 per mockup `.avatar` class) + L161 `<div style={avatarStyle}>{initial}</div>` (in-panel identity card — should remain 36×36 per mockup `topbar-overlays.jsx:347-360`). | 🔴 RED | Day 1 US-B2 splits into trigger (use `.avatar` CSS class) + identity (keep inline `identityAvatarStyle` 36×36). Confirmed user-reported bug root cause. |
| **D3** | Topbar Icon sizes — production all match mockup verbatim: ⌘K search `size={13}` matches mockup `shell.jsx:179`; locale globe `size={12}` matches mockup L195; theme + bell `<Icon size={14}>` matches `mockup-ui.tsx Button` default `<Icon size={14}>` (L436). User-reported "icon 大一點" perception **is 100% the avatar 36→26 effect alone** (38% larger avatar inflates the whole topbar visual rhythm). | 🟢 GREEN | No icon size correction needed. US-B3 audit can close as "0 drift discovered; user perception explained by D2". |
| **D4** | Production Topbar uses raw `<button className="btn ghost" data-size="sm"><Icon size={14} /></button>` (Topbar.tsx:186-198 theme + L205-219 bell) instead of mockup `<Button variant="ghost" size="sm" icon=... />`. The rendered DOM is **byte-identical** (mockup-ui.tsx `Button` renders the same `.btn.ghost[data-size="sm"]` + `<Icon size={14}>` shell). Semantic-only divergence: mockup uses the `Button` primitive as the canonical interaction layer. | 🟡 YELLOW | Defer — not a visual drift; promoting raw `<button>` to `<Button>` is a refactor that adds zero PARITY value. Open candidate `AD-Topbar-Use-Button-Primitive` for future cleanup sprint (low ROI; cosmetic-code-style only). |
| **D5** | (NEW finding not in plan §Risks) Production Topbar **missing** the `<Button variant="ghost" size="sm" icon="sliders" onClick={onToggleTweaks} title="Open Tweaks" />` (mockup `shell.jsx:218`). The Tweaks panel is a mockup-only design feature; production has no Tweaks panel implementation. | 🟡 YELLOW | Defer — intentional production scope omission (no Tweaks panel exists yet). Open candidate `AD-Topbar-Tweaks-Panel-Phase58+` for when Tweaks panel ships. Not a Sprint 57.30 blocker; flag in REPOINT-REPORT.md as known structural delta. |
| **D6** | chat-v2 mockup CSS classes (`.chat-shell` outer 3-col grid; `.chat-list` left rail; `.chat-stream` center; `.chat-inspector` right rail; `data-list="open/hidden"` + `data-insp="open/hidden"` collapse attrs; responsive `@media` breakpoints at 1280px + 980px) **all exist in `styles-mockup.css` lines 669-708**. ChatLayout re-point = replace translated-Tailwind `grid grid-cols-[...]` with these mockup class + data attrs verbatim. | 🟢 GREEN | Day 2 US-C1 ChatLayout re-point ready — verbatim foundation already in place from Sprint 57.28. |

**Prong 3 — Schema verify**: N/A (frontend-only sprint; no DB schema / Alembic migration / ORM model in scope).

**Prong 4 — Visual baseline strategy**:

- Affected baselines: Sprint 57.30 shell hotfix touches `<AppShellV2>` indirectly (the UserMenu trigger avatar 36→26 changes pixel layout at the topbar right edge) → **all 22 AppShellV2 routes' `visual-regression.spec.ts` `toHaveScreenshot` baselines could go stale**. Plus the 4 routes Sprint 57.29 already regenerated (`/cost-dashboard` `/governance` `/verification/recent` `/admin-tenants`) need regen again. Plus `/chat-v2` specific visual baselines (Day 4) need regen.
- Decision: **accept Day 5 regen overhead** (same workaround as Sprint 57.29). Rationale: pre-emptive regen before Day 1 has nothing-to-regen-against; baselines must be captured against the after-Day-4 state. Workaround per `AD-CI-7-GHA-PR-Permission`: trigger `playwright-e2e.yml visual-baseline` workflow_dispatch; manually ff-merge baseline-regen commit into feature branch when auto-PR step fails.
- Expected stale baseline count: 22 AppShellV2 routes × 1 spec + chat-v2-specific = ~22-25 baselines need regen on Day 5.

### Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UserMenu architecture | **Drop Radix `<DropdownMenu>` entirely; port mockup `useDismiss` hook verbatim** | User-approved 2026-05-23 (AskUserQuestion Option A). Only way to honour mockup `position: absolute; top: 50; right: 12` verbatim positioning. Closes `AD-UserMenu-Mockup-Structural-Deltas` clean. |
| `useDismiss` extraction | **Inline inside `UserMenu.tsx` first; defer extraction** to `frontend/src/hooks/useDismiss.ts` until 2nd consumer needs it | Karpathy §2 simplicity-first — no abstraction without 2nd usage. CommandPalette + NotificationsPanel don't use `useDismiss` today (they use Radix `<Dialog>`); when those get re-pointed Phase 57.31+, then extract. |
| Visual baseline regen | **Day 5 regen (accept workaround overhead)** | See Prong 4 above. |

### Open items / blockers

- None. Proceed to before-baseline screenshot capture once dev-server confirmed running.

### Remaining for Day 0

- §0.3 before-baseline screenshots — needs dev frontend at `:3007` + backend at `:8000`; user noted from session memory 3 dev servers still running. Will capture 22 routes + UserMenu states (avatar closed + dropdown open showing current drift gap) + chat-v2 inspector states.
- §0.4 Day 0 commit (plan + checklist + this progress.md + before-baseline screenshots) — after §0.3 done.

### Notes

- Sprint 57.30 plan + checklist drafting time (~75 min) was higher than 57.29's similar phase — accounted for by (a) the bundled scope (hotfix + page) requiring HYBRID class breakdown in §Background; (b) explicit user-decision call-out for the Radix-drop architectural choice; (c) more risks (R1-R7 vs 57.29's 6). Acceptable per format-consistency rule (more content within same structure).
- D5 (Tweaks button) is a new finding the plan §Risks didn't anticipate. Added to progress.md as YELLOW deferred rather than re-revising plan — preserves audit trail per `AD-Plan-1`. Will fold into Day 5 REPOINT-REPORT.md "Known structural deltas" section.
- D3 explains the user's perception of "topbar icons bigger" cleanly: the icons are correct; the avatar inflation alone creates the visual rhythm distortion. This is good news — Day 1 US-B3 audit reduces to "0 fix discovered + scope close" (~15 min saved vs plan's ~30 min estimate).
