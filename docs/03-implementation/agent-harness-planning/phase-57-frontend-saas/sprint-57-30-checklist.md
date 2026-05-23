# Sprint 57.30 — Checklist

> Plan: [`sprint-57-30-plan.md`](./sprint-57-30-plan.md)
>
> AD-Chatv2-Verbatim-Repoint + Shell-Hotfix-UserMenu-Avatar.
>
> Day 0-5; mirror 57.29 5-day structure. Format consistency rule per `.claude/rules/sprint-workflow.md` — checklist depth + per-task DoD + Verify command depth match 57.29 checklist.

---

## Day 0 — Plan + Checklist + 三-prong + before-baseline (PRE-WORK)

### 0.1 Plan + Checklist drafted

- [x] **Plan file** `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-30-plan.md` exists with 11 sections (Sprint Goal / Background / User Stories / Technical Specifications / File Change List / Acceptance Criteria / Deliverables / Dependencies & Risks / Workload / Sequencing-Day plan / + MHist footer)
  - DoD: `Glob` returns 1 result for the plan path
  - Verify: read plan §Sprint Goal — Shell hotfix + chat-v2 verbatim re-point per Option B
- [x] **Checklist file** (this file) drafted mirroring Sprint 57.29 checklist format (Day 0-5 + Group A-E + per-task DoD + Verify)
  - DoD: this file exists with Day 0-5 sections
  - Verify: `Glob` returns 1 result for `sprint-57-30-checklist.md`

### 0.2 Day-0 三-prong verify

- [x] **Prong 1 — Path verify** (all §File Change List paths in real repo) — 0 drift; 23 MODIFIED found / 1 NEW absent as expected
- [x] **Prong 2 — Content verify** (grep for plan-time factual assertions in real code) — 6 findings catalogued D1-D6 in progress.md; D2 🔴 (avatarStyle reuse) confirmed; D1+D3+D6 🟢; D4+D5 🟡 deferred
- [x] **Prong 3 — Schema verify** — N/A (frontend-only)
- [x] **Prong 4 — Visual baseline scope** — decision: accept Day 5 regen overhead (same as 57.29 workaround per `AD-CI-7-GHA-PR-Permission`)

### 0.3 Before-baseline screenshot capture

- [x] **22 AppShellV2 route screenshots** — `route-sweep.mjs before` mode (OUT_DIR re-pointed to sprint-57-30-* dir) → all 22 PNG in `before/`; ✅
- [x] **UserMenu states** — `sprint-57-30-day0-extras.mjs` captured `extra-usermenu-closed-overview.png` + `extra-usermenu-open-overview.png` (the latter visually confirms the drift gap user reported)
- [x] **chat-v2 states** — same script captured `extra-chatv2-inspector-default.png` + `extra-chatv2-inspector-toggled.png`
- [ ] **Day 0 commit** — pending (next step)

---

## Day 1 — Group B (Shell hotfix: UserMenu Radix-drop + avatar split + icon audit)

### 1.1 US-B1 — UserMenu Radix-drop verbatim port

- [ ] **Port `useDismiss` hook verbatim** from mockup `topbar-overlays.jsx:9-27`
  - Sub: decide extraction — `frontend/src/hooks/useDismiss.ts` (reusable) OR inline inside `UserMenu.tsx`
  - Sub: copy hook verbatim (TypeScript port: typed `anchorRef: RefObject<HTMLElement>`; handler types: `(e: KeyboardEvent | MouseEvent) => void`)
  - Sub: preserve mockup's ESC close + click-outside close + `data-topbar-overlay` opt-out semantics
  - DoD: hook present + typed correctly + matches mockup line-by-line (modulo TS type annotations)
  - Verify: `grep -n "useDismiss" frontend/src/hooks/useDismiss.ts` (or UserMenu.tsx) shows the hook signature
- [ ] **Drop Radix `<DropdownMenu>` wrapper** in `UserMenu.tsx`
  - Sub: remove `DropdownMenu` / `DropdownMenuTrigger` / `DropdownMenuContent` / `DropdownMenuItem` / `DropdownMenuSeparator` imports
  - Sub: replace with native `<button>` (trigger) + conditional `<div data-topbar-overlay style={panelStyle}>` (panel)
  - Sub: `useState` for `open` + `useRef` for `anchorRef` + call `useDismiss(open, () => setOpen(false), anchorRef)`
  - Sub: each former `<DropdownMenuItem>` becomes a native `<button>` or `<div role="button">` with the same `onClick` / `onSelect` behaviour
  - DoD: 0 Radix `DropdownMenu*` references remain in `UserMenu.tsx`
  - Verify: `grep -n "DropdownMenu" frontend/src/components/UserMenu.tsx` returns 0 results
- [ ] **Verify mockup-canonical positioning works** (manual smoke)
  - Sub: `npm run dev` → open `/overview` → click avatar → confirm dropdown appears flush against topbar bottom edge (no gap)
  - Sub: press ESC → dropdown closes
  - Sub: click outside panel → dropdown closes
  - Sub: click inside panel item → action fires + dropdown closes
  - DoD: all 4 interaction checks pass
  - Verify: Playwright screenshot `after-usermenu-flush.png` shows dropdown top edge = topbar bottom edge + 2px

### 1.2 US-B2 — Avatar trigger 36→26 split

- [ ] **Split `avatarStyle` into trigger + identity** in `UserMenu.tsx`
  - Sub: define `triggerAvatarStyle` (26×26, font-size 10.5) per mockup `.avatar` class — or use the `.avatar` CSS class directly via `<button className="avatar">` (preferred since the class is already in `styles-mockup.css`)
  - Sub: define `identityAvatarStyle` (36×36, font-size 13) per mockup `topbar-overlays.jsx:347-360` — inline-style only because the identity card has no mockup CSS class
  - Sub: use trigger avatar at line ~147 (the button); use identity avatar at line ~161 (inside the dropdown identity card)
  - DoD: 2 distinct style sources for the two avatars
  - Verify: `grep -n "26\|36" frontend/src/components/UserMenu.tsx` shows the two sizes used at different positions
- [ ] **Verify with Playwright screenshot**
  - Sub: `/overview` topbar avatar at 1440×900 → screenshot
  - Sub: compare to before-baseline → trigger avatar visibly smaller (26 vs 36 = 27% smaller)
  - DoD: after-screenshot saved
  - Verify: `claudedocs/4-changes/sprint-57-30-chatv2-shell-repoint/screenshots/after/usermenu-trigger-26px.png` exists

### 1.3 US-B3 — Topbar icon size audit + fix

- [ ] **Audit each topbar icon vs mockup** (per Day 0 Prong 2 findings)
  - Sub: confirm `Icon name="search" size={13}` matches mockup ⌘K icon size (Day 0 catalogued)
  - Sub: confirm `Icon name="globe" size={12}` matches mockup locale icon size
  - Sub: confirm `Icon name={theme} size={14}` matches mockup theme-toggle icon size
  - Sub: confirm `Icon name="bell" size={14}` matches mockup bell icon size
  - DoD: each icon explicitly confirmed match OR fix committed
  - Verify: `progress.md` Day 1 lists audit table per-icon match/fix outcome
- [ ] **Fix any drift discovered** (likely few or zero corrections; mostly verification)
  - Sub: update `Topbar.tsx` Icon `size={...}` literal(s)
  - DoD: corrected sizes match mockup
  - Verify: `grep -n "Icon name" frontend/src/components/layout/Topbar.tsx` shows updated values

### 1.4 US-B4 — Vitest + Topbar / UserMenu spec adaptation

- [ ] **Find Vitest specs that assert UserMenu or Topbar structure**
  - Sub: `grep -rln "UserMenu\|userMenu\|topbar\|DropdownMenu" frontend/tests/`
  - DoD: catalog of spec files in `progress.md` Day 1
  - Verify: list ≥2 spec files (UserMenu + Topbar)
- [ ] **Adapt assertions to verbatim structure**
  - Sub: where spec asserts Radix `role="menu"` / `aria-haspopup="menu"` etc., adapt to native button + `data-topbar-overlay` panel semantics
  - Sub: where spec asserts avatar size implicitly via Radix data attrs, assert the explicit `className="avatar"` or `width: 26` style on trigger
  - DoD: all touched specs pass `npm run test`
  - Verify: `npm run test -- UserMenu Topbar` exits 0
- [ ] Day 1 commit
  - Sub: `git add frontend/src/components/UserMenu.tsx frontend/src/components/layout/Topbar.tsx [frontend/src/hooks/useDismiss.ts if extracted] frontend/tests/...UserMenu*.test.tsx [Topbar*.test.tsx if touched]`
  - Sub: `git commit -m "feat(frontend, sprint-57-30): Day 1 Group B — UserMenu Radix-drop verbatim + avatar trigger 26 split + topbar icon audit\n\nUS-B1: UserMenu Radix-drop → verbatim useDismiss hook (closes AD-UserMenu-Mockup-Structural-Deltas)\nUS-B2: trigger avatar 26×26 separated from identity-card avatar 36×36\nUS-B3: topbar icon size audit (all match mockup)\nUS-B4: Vitest adapted to Radix-free structure\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"`
  - DoD: Day 1 commit landed
  - Verify: `git log --oneline -2` shows Day 0 + Day 1 commits

---

## Day 2 — Group C (chat-v2 shell + composer)

### 2.1 US-C1 — ChatLayout 3-col grid verbatim

- [ ] **Read mockup `page-chat.jsx`** for outer ChatLayout grid (verbatim source)
  - Sub: identify the outer grid template (3 cols: session-rail / 1fr center / inspector-rail)
  - Sub: identify gap + min/max widths
  - DoD: mockup grid spec catalogued in `progress.md` Day 2
- [ ] **Re-point `ChatLayout.tsx`** to verbatim mockup grid
  - Sub: drop translated-Tailwind `grid grid-cols-[...]`
  - Sub: use mockup CSS class (if exists in `styles-mockup.css`) OR inline-style verbatim
  - Sub: preserve component-logic layer (children slots, conditional Inspector rendering, etc.)
  - Sub: add file-level eslint-disable comment with verbatim escape-hatch reason
  - Sub: update file header MHist (1-line)
  - DoD: ChatLayout consumes verbatim grid
  - Verify: `/chat-v2` 3-col layout matches mockup at 1440×900 Playwright screenshot

### 2.2 US-C2 — ChatHeader + SessionList + Composer + InputBar verbatim

- [ ] **ChatHeader** re-point
  - Sub: read mockup `page-chat.jsx` chat-header section
  - Sub: replace shadcn / Tailwind with verbatim mockup classes + inline-style
  - Sub: preserve all logic (back nav, session title, status indicator, etc.)
  - Sub: header MHist update
  - DoD: ChatHeader verbatim
  - Verify: `/chat-v2` header bar matches mockup screenshot
- [ ] **SessionList** re-point
  - Sub: read mockup session-list section
  - Sub: verbatim re-point
  - Sub: preserve session selection + active highlight + scroll behaviour
  - Sub: header MHist update
  - DoD: SessionList verbatim
- [ ] **Composer** re-point
  - Sub: read mockup composer container
  - Sub: verbatim re-point
  - Sub: preserve form submission + keyboard `Enter` / `Shift+Enter` behaviour
  - Sub: header MHist update
  - DoD: Composer verbatim
- [ ] **InputBar** re-point
  - Sub: read mockup input field + send button
  - Sub: verbatim re-point
  - Sub: preserve auto-resize, mention/slash command UI, attach button
  - Sub: header MHist update
  - DoD: InputBar verbatim
- [ ] **Day 2 mini-verify**
  - Sub: `npm run dev` → `/chat-v2` mounts → composer renders → send a message → Vitest `npm run test -- chat-v2` all pass
  - DoD: no regression in chat-v2 send-message flow
- [ ] Day 2 commit
  - Sub: `git commit -m "feat(frontend, sprint-57-30): Day 2 Group C — chat-v2 shell + composer verbatim re-point (US-C1 + US-C2)\n\n..."`

---

## Day 3 — Group D first half (TurnList + 3 turn shapes + 3 blocks)

### 3.1 US-D1 — TurnList + UserTurn + AgentTurn + HITLTurn

- [ ] **TurnList** re-point
  - Sub: verbatim mockup port; preserve scroll behaviour + virtualization (if any)
  - Sub: header MHist
- [ ] **UserTurn** re-point
  - Sub: verbatim mockup user-turn shape
  - Sub: preserve content rendering + timestamp + edit affordance
  - Sub: header MHist
- [ ] **AgentTurn** re-point
  - Sub: verbatim mockup agent-turn shape (includes block routing for ThinkingBlock / ToolBlock / VerificationBlock / SubagentForkBlock)
  - Sub: preserve discriminated-union routing from Sprint 57.21 Turn Block Model
  - Sub: header MHist
- [ ] **HITLTurn** re-point
  - Sub: verbatim mockup HITL turn (the largest turn file — 229 lines today)
  - Sub: preserve approval flow + governance integration
  - Sub: header MHist

### 3.2 US-D2 first half — Block base + ThinkingBlock + ToolBlock

- [ ] **Block** (base wrapper) re-point
  - Sub: verbatim mockup block base style
  - Sub: header MHist
- [ ] **ThinkingBlock** re-point
  - Sub: verbatim mockup thinking-block (collapsed + expanded states)
  - Sub: preserve markdown rendering
  - Sub: header MHist
- [ ] **ToolBlock** re-point
  - Sub: verbatim mockup tool-block (input args + output + status indicator)
  - Sub: preserve JSON syntax highlighting
  - Sub: header MHist
- [ ] **Day 3 mini-verify**
  - Sub: `/chat-v2` turn list renders with new turn frames + 3 block types
  - Sub: Sprint 57.21 Vitest behavioural specs still pass
- [ ] Day 3 commit

---

## Day 4 — Group D second half (VerificationBlock + SubagentForkBlock + Inspector + ApprovalCard)

### 4.1 US-D2 second half — VerificationBlock + SubagentForkBlock

- [ ] **VerificationBlock** re-point
  - Sub: verbatim mockup verification-block (rule list + pass/fail + correction loop UI)
  - Sub: header MHist
- [ ] **SubagentForkBlock** re-point
  - Sub: verbatim mockup subagent-fork (subagent tree + spawn/return events)
  - Sub: header MHist

### 4.2 US-D3 — ChatInspector + InspectorTurn + ComingSoonInspectorTab

- [ ] **ChatInspector** re-point
  - Sub: verbatim mockup 4-tab chrome (Overview / State / Tools / Verification)
  - Sub: preserve tab state + tab-switch behaviour
  - Sub: header MHist
- [ ] **InspectorTurn** re-point
  - Sub: verbatim mockup inspector-turn detail view
  - Sub: preserve turn data binding
  - Sub: header MHist
- [ ] **ComingSoonInspectorTab** re-point
  - Sub: verbatim mockup coming-soon placeholder
  - Sub: header MHist

### 4.3 US-D4 — ApprovalCard

- [ ] **ApprovalCard** re-point
  - Sub: verbatim mockup HITL approval card visual
  - Sub: preserve approve / deny / escalate handlers + governance integration
  - Sub: header MHist

### 4.4 Vitest comprehensive re-run

- [ ] **Run all chat-v2 Vitest** + adapt any new spec drift
  - Sub: `npm run test -- chat-v2`
  - Sub: any failure → adapt to verbatim structure (not to Radix / Tailwind assertions)
  - DoD: 100% pass
- [ ] Day 4 commit
  - Sub: `git commit -m "feat(frontend, sprint-57-30): Day 4 Group D second half — Inspector + ApprovalCard + last 2 blocks verbatim re-point\n\n..."`

---

## Day 5 — Group E (regression sweep + chat-v2 fidelity + closeout)

### 5.1 US-E1 — 22-route regression sweep

- [ ] **Capture after-baseline 22 routes** via `route-sweep.mjs`
  - Sub: `node scripts/visual/route-sweep.mjs --tag=after`
  - Sub: writes to `claudedocs/4-changes/sprint-57-30-chatv2-shell-repoint/screenshots/after/`
  - DoD: 22 PNG in `after/`
- [ ] **Agent triage** before vs after
  - Sub: launch `general-purpose` (or `code-reviewer`) agent with all 22 pairs; classify each as PARITY / 🟡 acceptable-cosmetic / 🔴 catastrophic / 🟠 structural-regression
  - Sub: triage report → REPOINT-REPORT.md
  - DoD: 0 🔴 catastrophic / 0 🟠 structural-regression; any 🟡 cosmetic documented with reason
  - DoD: pre-existing-fail routes (`/subagents` `/memory` `/verification` per Sprint 57.29 carryover `AD-Overview-PreExisting-Route-Crashes`) classified explicitly as **not Sprint 57.30 regressions** (before == after baseline)

### 5.2 US-E2 — chat-v2 fidelity verification (Mockup-Fidelity DoD)

- [ ] **Step 1 — `styles.css` ↔ `styles-mockup.css` diff**
  - Sub: `diff reference/design-mockups/styles.css frontend/src/styles-mockup.css` → empty
  - DoD: diff empty (foundation untouched)
- [ ] **Step 2 — Mockup vs prod Playwright screenshot at 1440×900**
  - Sub: spin up mockup `python -m http.server` from `reference/design-mockups/`
  - Sub: capture mockup `/chat-v2` equivalent page
  - Sub: capture prod `/chat-v2` (Inspector closed + open)
  - DoD: 2-3 screenshot pairs saved
- [ ] **Step 3 — Computed-style measurement**
  - Sub: pick ~10 representative elements (ChatLayout grid, ChatHeader, SessionList row, Composer, AgentTurn frame, ThinkingBlock, ToolBlock, Inspector tab, ApprovalCard)
  - Sub: read `getComputedStyle()` for each on both mockup + prod; diff
  - DoD: drift items each classified as PARITY / cosmetic / structural
- [ ] **Step 4 — Drift classification + parity verdict**
  - Sub: write REPOINT-REPORT.md final verdict section
  - Sub: if PARITY → log as `frontend-verbatim-css-repoint` 2nd-app validated
  - Sub: if non-PARITY → log finding as next sprint carryover AD
  - DoD: verdict in REPOINT-REPORT.md

### 5.3 US-E3 — Full gates

- [ ] **tsc** — `npm run typecheck` → 0 errors
  - Verify: exit code 0
- [ ] **lint** — `npm run lint` → 0 errors
  - Verify: exit code 0
- [ ] **Vitest** — `npm run test` → all pass
  - Sub: log new count vs Sprint 57.29 baseline 457
  - Verify: exit code 0; count delta logged in progress.md
- [ ] **Playwright** — `npm run test:e2e` → all pass
  - Sub: visual-regression baseline regen if Day 4 changes invalidated 57.29 baselines (ff-merge per Sprint 57.29 workaround)
  - Verify: green
- [ ] **Build** — `npm run build` → successful
  - Sub: log bundle size delta vs Sprint 57.29
  - Verify: exit code 0
- [ ] **`check:mockup-fidelity`** — `npm run check:mockup-fidelity`
  - Sub: if new oklch literals added by Day 1-4 work, update `HEX_OKLCH_BASELINE` per US-E1 pre-authorisation (Day 0 catalogue any expected delta)
  - Verify: green
- [ ] **LLM SDK leak check** — `python scripts/lint/check_llm_sdk_leak.py backend/src/agent_harness/` → 0
  - Verify: exit code 0 (sanity check; shouldn't change frontend-only sprint)
- [ ] **Backend pytest** — sanity that no incidental backend change crept in
  - Sub: `cd backend && pytest -x --timeout=60` (if affordable; else skip)
  - DoD: green or skipped with reason in progress.md

### 5.4 US-E4 — Closeout (retro + memory + docs + PR)

- [ ] **`retrospective.md`** Q1-Q7 written
  - Sub: Q1 What went well / Q2 What didn't go well + calibration ratio / Q3 What we learned / Q4 Audit Debt deferred / Q5 Next steps + carryover AD list / Q6 Solo-dev policy validation / Q7 (N/A — feature ship not spike)
  - Sub: Q2 must include `actual / committed` ratio and judge against [0.85, 1.20] band per `sprint-workflow.md §Workload Calibration`
  - DoD: file `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-30/retrospective.md` exists with all 6 sections (Q7 N/A SKIP)
- [ ] **Memory snapshot** `memory/project_phase57_30_chatv2_shell_repoint.md` (NEW)
  - Sub: ~250-300 char per `sprint-workflow.md §Sprint Closeout — MEMORY.md Update Policy` quality pointer rule
  - Sub: subfile detail in `memory/project_phase57_30_*.md`
  - DoD: file exists with frontmatter + sprint summary
- [ ] **MEMORY.md** index entry added
  - Sub: 1 pointer entry per quality pointer principle (topic + keywords + subfile path; ~300 char ceiling)
  - DoD: MEMORY.md has new pointer at top of "Project — Recent Sprints" section
- [ ] **CLAUDE.md** Current Sprint row + footer updated
  - Sub: Current Sprint row → next sprint candidate or "ready for next"
  - Sub: Last Updated footer → `2026-MM-DD (Sprint 57.30 — Chat-v2 + Shell Hotfix Verbatim Re-Point)`
  - DoD: minimal touch per `sprint-workflow.md §Sprint Closeout — CLAUDE.md Update Policy`
- [ ] **`.claude/rules/sprint-workflow.md §Scope-class multiplier matrix`** updated
  - Sub: `frontend-verbatim-css-repoint` row — 2nd data point (Sprint 57.30 ratio)
  - Sub: KEEP 0.60 per `When to adjust` 3-sprint window rule
  - Sub: MHist entry added (1-line per char-budget rule)
  - DoD: matrix row reflects 2 data points
- [ ] **`claudedocs/1-planning/next-phase-candidates.md`** updated
  - Sub: CLOSE `AD-UserMenu-Mockup-Structural-Deltas` (resolved this sprint)
  - Sub: ADD any new carryover ADs from retrospective Q4 + Q5
  - Sub: KEEP `AD-Overview-PreExisting-Route-Crashes` + `AD-CI-7-GHA-PR-Permission` (Sprint 57.31+)
  - DoD: candidates file synced
- [ ] **PR opened**
  - Sub: `gh pr create --title "feat(frontend, sprint-57-30): chat-v2 Phase-2 verbatim CSS re-point + shell hotfix (UserMenu Radix-drop + avatar 36→26 split + topbar icon audit)" --body "..."`
  - Sub: PR body links plan + REPOINT-REPORT.md + retrospective
  - DoD: PR number assigned
- [ ] **CI green → merge**
  - Sub: if visual-regression baseline stale (likely on shell + chat-v2 changes), trigger baseline-regen workflow → ff-merge baseline commit per Sprint 57.29 `AD-CI-7-GHA-PR-Permission` workaround
  - Sub: squash-merge to main when all 5 required CI checks green
  - Sub: delete feature branch + any throwaway baseline-regen branch
  - DoD: PR squash-merged to main; branch cleanup done

### 5.5 Sprint closeout self-check

- [ ] **Sacred Rule check** — no unchecked `[ ]` items in this checklist were deleted
  - Verify: `grep -c "^- \[ \]" sprint-57-30-checklist.md` matches all incomplete-but-deferred items (none expected if all Group A-E delivered)
- [ ] **Acceptance Criteria verified** — all items in plan §Acceptance Criteria pass
- [ ] **Working tree clean post-merge**
  - Verify: `git status` shows clean main + untracked screenshots only
- [ ] **Branch deleted**
  - Verify: `git branch --list feature/sprint-57-30-*` returns empty
