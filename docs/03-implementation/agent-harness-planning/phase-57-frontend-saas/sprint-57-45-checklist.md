# Sprint 57.45 — Checklist

> Plan: [`sprint-57-45-plan.md`](./sprint-57-45-plan.md)
> Scope: `/chat-v2` Inspector tab vocabulary rename (NEAR-PARITY quick win) — closes Phase-2 epic + NEAR-PARITY DUAL CLEAN milestone
> Critical: **1st validation data point under newly tightened `agent_factor = 0.45`** per `.claude/rules/sprint-workflow.md §Active Agent Delegation Factor Modifier` (was 0.55; tightened 2026-05-26 per Sprint 57.44 retro Q4 rollback rule)

---

## Day 0 — Three-Prong Verify + Path A/B Decision + Baselines

### 0.1 Plan + checklist draft commit
- [ ] **Commit draft plan + checklist to feature branch**
  - DoD: `git log --oneline -1` shows commit subject `feat(frontend, sprint-57-45): Day 0 — plan + checklist draft`
  - Verify: 2 files committed on `feature/sprint-57-45-chatv2-inspector-tab-rename`

### 0.2 Prong 1 — Path verify
- [ ] **Glob existing Inspector files**
  - DoD: `frontend/src/features/chat_v2/components/inspector/*.tsx` returns 3 files (ChatInspector + ComingSoonInspectorTab + InspectorTurn)
- [ ] **Glob existing Inspector Vitest specs**
  - DoD: `frontend/tests/unit/chat_v2/inspector/*.test.tsx` — list found specs (estimated 0-2 files)
- [ ] **Glob existing chat-v2 e2e tests**
  - DoD: `frontend/{tests/e2e,e2e}/**/*chat*` — list found specs (per Sprint 57.43 hotfix #1 broader glob)
- [ ] **Verify route-sweep.mjs current OUT_DIR slug**
  - DoD: OUT_DIR currently `sprint-57-44-tenant-settings-rebuild` per Sprint 57.44 closeout; will re-point in Day 0.7

### 0.3 Prong 2 — Content verify (audit-vs-mockup-file divergence resolution)
- [ ] **Re-read mockup `reference/design-mockups/page-chat.jsx:370-395`**
  - DoD: Confirm L378-381 tab labels (`Turn / Trace / Memory / Tree` per current mockup file)
- [ ] **Grep repo-wide for audit's claimed mockup labels**
  - DoD: `grep -r "Run.*Tools.*Memory.*Verify"` + reverse `grep -r "Verify.*Memory.*Tools.*Run"` — identify if any other mockup file / archive / docs reference contains this vocab (the audit's source)
- [ ] **Grep production Inspector for current labels**
  - DoD: `frontend/src/features/chat_v2/components/inspector/ChatInspector.tsx:60-65` confirms `Turn / Trace / Memory / Tree`
- [ ] **Decide Path A or Path B**
  - Path A criteria: audit's "Run / Tools / Memory / Verify" found in canonical source (e.g. older mockup snapshot, UX spec doc, or other authoritative location)
  - Path B criteria: mockup file is the only source of truth; audit's claim is obsolete/erroneous; production already matches mockup file
  - DoD: Decision documented in progress.md with rationale
  - If unresolvable from grep evidence → pause Day 0 and ask user

### 0.4 Prong 2.5 — Child component tree depth audit (if Path A selected)
- [ ] **Grep for tab id usages across chat_v2** (Path A only)
  - DoD: `grep -rn "\"turn\"\|\"trace\"\|\"memory\"\|\"tree\"" frontend/src/features/chat_v2/` identifies all callsites that would need rename
  - Verify: scope confirmed ≤ 1-2 files (per plan §3.2 estimate)

### 0.5 Prong 3 — Schema verify (N/A this sprint)
- [ ] **N/A — no DB schema / migration / ORM model touched**
  - DoD: Skip; document N/A in progress.md

### 0.6 Mockup excerpt Read for Day 1 components
- [ ] **Already done in §0.3 — Path A reference is audit-report L37+L93; Path B reference is mockup file L378-381**

### 0.7 Before-sweep + baselines
- [ ] **Re-point route-sweep.mjs OUT_DIR**
  - DoD: Edit `frontend/scripts/route-sweep.mjs` OUT_DIR slug `sprint-57-44-tenant-settings-rebuild` → `sprint-57-45-chatv2-inspector-tab-rename`
- [ ] **Capture 24-route BEFORE screenshots**
  - DoD: `cd frontend && node scripts/route-sweep.mjs before` exit 0; 24 PNGs in `screenshots/before/`
- [ ] **Record HEX_OKLCH_BASELINE pre-sprint** baseline (47 from Sprint 57.44 closeout)
  - DoD: `node frontend/scripts/check-mockup-fidelity.mjs` reports baseline 47
- [ ] **Record Vitest baseline** (561 from Sprint 57.44 closeout per memory record; main unchanged since merge)

### 0.8 Drift findings catalog + go/no-go
- [ ] **Catalog all D-DAY0-N findings in progress.md**
  - DoD: D-DAY0-1 audit-vs-mockup-file divergence + Path A/B decision; other findings as discovered
- [ ] **Go/no-go decision**
  - DoD: Path A → continue Day 1 with rename + spec update; Path B → continue Day 1 with audit-report.md update only
  - If audit-vs-mockup-file divergence unresolvable from grep → pause and ask user

---

## Day 1 — Implementation (Path A rename OR Path B audit overrule)

### Path A (Rename production tabs to match audit)

#### 1.A.1 Edit `ChatInspector.tsx`
- [ ] **Rename type + TAB_ITEMS + dispatch + ComingSoonInspectorTab props**
  - DoD: L53 type `"turn" | "trace" | "memory" | "tree"` → `"run" | "tools" | "memory" | "verify"`
  - DoD: L60-65 TAB_ITEMS labels + ids updated to "Run / Tools / Memory / Verify"
  - DoD: L93-117 dispatch + ComingSoonInspectorTab `name="..."` props updated
  - Verify: TypeScript strict 0 errors; lint clean

#### 1.A.2 Update Vitest specs
- [ ] **Update spec selectors per Day 0.4 grep finding**
  - DoD: All `getByText("Turn"|"Trace"|"Tree")` selectors updated to `getByText("Run"|"Tools"|"Verify")`
  - Verify: `(cd frontend && npx vitest run --reporter=dot tests/unit/chat_v2/)` all GREEN

#### 1.A.3 Day 1 Path A closeout commit
- [ ] **Commit Day 1 Path A**
  - DoD: `git log --oneline -1` shows `feat(frontend, sprint-57-45): Day 1 — rename Inspector tabs Turn/Trace/Tree → Run/Tools/Verify (Path A per Day 0.3 decision)`
  - Verify: Build green; lint 0 errors; LLM SDK leak 0

### Path B (Audit overrule — no code change)

#### 1.B.1 Document Path B rationale in progress.md
- [ ] **Write Path B rationale paragraph in progress.md Day 0/1 entry**
  - DoD: Documents (a) `frontend-mockup-fidelity.md` rule mockup-file-canonical; (b) production already matches mockup file; (c) audit row 9 overruled
  - Verify: progress.md Day 1 entry contains "Path B selected" + rationale

#### 1.B.2 Day 1 Path B closeout commit
- [ ] **Commit Day 1 Path B (no code change; just progress.md update)**
  - DoD: `git log --oneline -1` shows `docs(frontend, sprint-57-45): Day 1 — Path B audit row 9 overruled (mockup file canonical per frontend-mockup-fidelity.md rule; production already PARITY)`
  - Verify: 1 file modified (progress.md)

---

## Day 2 — (Skipped this sprint — no Vitest batch needed)

Day 2 task group skipped for this small-scope sprint. Day 1 spec updates (Path A) or zero spec updates (Path B) handled in Day 1.

---

## Day 2.5 — After Sweep + 3-Way Evidence Pair

### 2.5.1 After-sweep run
- [ ] **Capture 24-route AFTER screenshots**
  - DoD: `cd frontend && node scripts/route-sweep.mjs after` exit 0; 24 PNGs in `screenshots/after/`

### 2.5.2 sha256 diff vs before
- [ ] **Compute sha256 diff per-route**
  - Path A expected: 23 IDENTICAL + 1 INTENDED `/chat-v2` (small byte delta from tab label text) + ≤ 3 sub-300-byte noise + 0 unintended
  - Path B expected: 24 IDENTICAL OR ≤ 3 sub-300-byte noise + 0 unintended (no code change)

### 2.5.3 3-way evidence pair staging
- [ ] **Stage BEFORE + AFTER `/chat-v2` PNGs**
  - DoD: Path A — `01-BEFORE-chat-v2.png` + `02-AFTER-chat-v2.png` in `before-after/`; Path B — skip (no diff to compare)
- [ ] **MOCKUP capture decision** — defer Option C byte-proxy per Sprint 57.43/44 precedent (NEW carryover `AD-MockupCapture-05-MOCKUP-chat-v2`)

### 2.5.4 Day 2.5 closeout commit
- [ ] **Commit Day 2.5 (sweep PNGs + 3-way evidence + progress.md update)**
  - DoD: `git log --oneline -1` shows `chore(frontend, sprint-57-45): Day 2.5 — 24-route after sweep + 3-way evidence pair`

---

## Day 3 — Retro Q1-Q7 + Matrix MHist + Memory + Closeout

### 3.1 Retrospective Q1-Q7 per 6-question format
- [ ] **Write `docs/03-implementation/agent-harness-execution/phase-57/sprint-57-45/retrospective.md`**
  - DoD: Q1 What went well / Q2 What didn't / Q3 What we learned / Q4 Audit Debt deferred + agent_factor 1st post-tightening validation / Q5 Next steps (rolling candidates) / Q6 Solo-dev policy / Q7 N/A SKIP (non-spike feature-fix sprint per Sprint 57.40-44 cohort precedent)
  - Verify: ~100-150 lines (much shorter than 57.44 ~270 due to smaller scope)

### 3.2 Matrix MHist entry + `agent_factor` 1st post-tightening validation note
- [ ] **Update `.claude/rules/sprint-workflow.md §Scope-class multiplier matrix` for `frontend-refactor-mechanical` 3rd data point**
  - DoD: Add 57.45 ratio to row; verify against 0.80 lift baseline (per AD-Sprint-Plan-13)
- [ ] **Update `§Active Agent Delegation Factor Modifier` Activation history with 1st post-tightening validation Sprint 57.45 entry**
  - DoD: Sprint 57.45 entry records ratio + decision (KEEP 0.45 if in range; tighten 0.45 → 0.35 if < 0.7 again; roll back 0.45 → 0.55 if > 1.20)
  - Single-data-point caution applies; 2nd validation Sprint 57.46

### 3.3 Memory subfile + MEMORY.md update
- [ ] **Create `memory/project_phase57_45_chatv2_inspector_tab_rename.md`**
  - DoD: Per-sprint subfile per `.claude/rules/sprint-workflow.md §Sprint Closeout` quality pointer principle
- [ ] **Add `memory/MEMORY.md` pointer entry**
  - DoD: ~300 char quality pointer with keywords for retrieval

### 3.4 CLAUDE.md sync (Phase-2 epic + NEAR-PARITY DUAL CLEAN milestone)
- [ ] **Update CLAUDE.md `Current Sprint` row + `Last Updated` footer**
  - DoD: Minimal touch per `.claude/rules/sprint-workflow.md §Sprint Closeout` policy; 22/22 PARITY + 0 NEAR-PARITY milestone marker

### 3.5 Day 3 closeout commit + push + PR
- [ ] **Commit Day 3 (retro + matrix MHist + memory + CLAUDE.md)**
  - DoD: `git log --oneline -1` shows `docs(frontend, sprint-57-45): Day 3 — retro + matrix MHist + agent_factor 0.45 1st validation + memory + CLAUDE.md sync`
- [ ] **Push branch + open PR**
  - DoD: `git push -u origin feature/sprint-57-45-chatv2-inspector-tab-rename` + `gh pr create`
- [ ] **Monitor CI → merge when all green**
  - DoD: 5 active required CI checks pass; squash merge

---

## Pre-Commit Self-Check

- [ ] Commit message follows Conventional Commits + co-author
- [ ] `cd frontend && npm run lint` exit 0 (NO `--silent`)
- [ ] `cd frontend && npm run build` exit 0
- [ ] `cd frontend && npm test -- --run` all GREEN
- [ ] `node frontend/scripts/check-mockup-fidelity.mjs` exit 0

---

## Acceptance criteria verification (Day 3 closeout)

- [ ] **AC1**: Day 0 Prong 2 audit-vs-mockup-file resolution documented; Path A/B decision rationale clear
- [ ] **AC2**: `/chat-v2` verdict 🟡 NEAR-PARITY → ✅ PARITY; summary 21→22 PARITY / 1→0 NEAR-PARITY / 0 CATASTROPHIC; 🎉 Phase-2 epic + NEAR-PARITY clean DUAL milestone
- [ ] **AC3**: Path A — Vitest delta minimal (specs updated); all GREEN. Path B — Vitest 561 unchanged.
- [ ] **AC4**: 24-route sweep — Path A: 23 IDENTICAL + 1 INTENDED + ≤ 3 noise + 0 unintended. Path B: 24 IDENTICAL OR ≤ 3 noise + 0 unintended.
- [ ] **AC5**: HEX_OKLCH_BASELINE 47 unchanged (no new oklch literals)
- [ ] **AC6**: `agent_factor = 0.45` 1st validation data point recorded in §Active block; single-data-point caution applies; flag Sprint 57.46 for 2nd validation
