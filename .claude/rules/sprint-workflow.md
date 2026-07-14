# Sprint Workflow Rules

**Purpose**: Enforce sprint execution discipline; prevent Phase 35-38 shortcut lessons from repeating.

**Category**: Development Process
**Created**: 2026-04-28
**Last Modified**: 2026-07-14
**Status**: Active

> **Modification History**
> - 2026-07-14: REFACTOR-011 — matrix/agent_factor + Step2.5 prongs + Step5.5 gate → on-demand files
> - 2026-07-14: REFACTOR-009 — matrix + agent_factor narration re-extracted → calibration-log §1/§2
> - 2026-07-07: REFACTOR-010 — §Sprint Closeout Self-Check +1 line: full SHIPPED carryover → next-phase-candidates-shipped-archive.md, main file keeps 1-line pointer + open ADs only (stop next-phase re-bloat)
> - 2026-06-17: REFACTOR-008 — Reference Template (Step 1 + Step 2) re-anchored from "most-recent sprint" (relative/floating → monotonic drift) to FROZEN `claudedocs/templates/sprint-{plan,checklist}-template.md` (absolute); enforce short H1 + Summary block + §0 line-breaks (fix the 57.107-130 drift defects)
> - 2026-06-16: chore(rules) — §Sprint Closeout post-merge status-flip rule: flip `PR-pending`→`MERGED` on the 2 current-status surfaces (CLAUDE.md Current Sprint row + next-phase head block) after gh-verified merge + interregnum Current-Sprint-row wording + historical-block sweep only if misleading (one done 2026-06-16 for 57.112-126)
> - 2026-06-03: chore(rules) — Area-A (57.66-73) lessons fold-in: Prong-1 test-infra verify (AD-Day0-Prong1-TestInfra-File-Verify) + Prong-2 +2 drift rows (codegen-shape AD-Day0-Codegen-Existing-Shape-Capture / no-live-producer) + Risk Class E (stale --reload masks wiring; C-11 cost_ledger) + Risk Class C reinforce (AD-Source-DB-Call-Test-Isolation) + Before-Commit item 7 (agent-delegation: all gates + pin language + parent re-verify)
> - 2026-05-31: REFACTOR-005 — extract per-sprint calibration history (matrix per-cell narration + §Scope-class MHist list + agent_factor activation history 57.42→57.62 + top calibration-retro entries) to calibration-log.md; kept active multiplier table + agent_factor Formula/Rollback/Escalation/Tracking rules (always-loaded file ~90k→~25k tok)
> - 2026-05-29: Sprint 57.62 follow-up chore — mark §Common Risk Classes Risk Class A **RETIRED Sprint 55.6** (paths filter removed → docs-only PRs run full CI; stale touch-backend-ci.yml workaround description corrected; residual webhook-miss edge case noted)
> - 2026-05-26: Sprint 57.52 — Drift Class table +2 rows (closes AD-Day0-Prong2-Oklch-Delta-Grep + AD-Stale-Docstring-Karpathy-3)
> - 2026-05-26: Sprint 57.51 — add §Common Risk Classes Risk Class D ORM File Path Reference Style (closes AD-Plan-Risk-ORM-File-Path-Reference-Style #82; Sprint 57.50 D-DAY0-2 lesson)
> - 2026-05-25: Bundle Item #4 — propose Agent Delegation Factor Modifier (matrix proposal, pending 2-3 sprint validation) + §Before Commit lint must be non-silent (closes AD-Sprint-Plan-Agent-Delegation-Factor-Modifier as proposal + AD-Pre-Push-Lint-Silent-Suppression-Anti-Pattern)
> - 2026-05-25: AD-Plan-5 fold-in §Step 2.5 Prong 2.5 Child Component Tree Depth Audit (closes AD-Day0-Prong2-Child-Component-Tree-Depth-Audit; Sprint 57.39 D-DAY1-1 + FIX-015 evidence)
> - 2026-05-18: Sprint 57.22 — add §Sprint Closeout CLAUDE.md+MEMORY.md update policy (closes REFACTOR-001 Step 2)
> - 2026-05-06: Sprint 57.1 — fold-in §Step 2.5 Prong 3 Schema Verify (closes AD-Plan-4 promotion)
> - 2026-05-05: Sprint 55.6 — promote AD-Plan-3 (Prong 2 content verify + ROI + grep patterns)
> - 2026-05-04: Sprint 55.3 — add §Step 2.5 Day-0 plan-vs-repo grep verify (closes AD-Plan-1) + drop per-day "Estimated X hours" headers from checklist template (closes AD-Lint-2)
> - 2026-05-04: Sprint 53.7 — add §Workload Calibration sub-section under Step 1 (closes AD-Sprint-Plan-1) + new §Common Risk Classes top-level section (closes AD-CI-4) + Pre-Push reference `python scripts/lint/run_all.py` wrapper (closes AD-Lint-1 doc portion)
> - 2026-04-28: Initial creation (V2 foundation) — enforce 5-step workflow + change record conventions
>
> Per-sprint calibration-retro entries (Sprint 57.42→57.62, dropped here per REFACTOR-005) → [calibration-log.md §3](../../docs/03-implementation/agent-harness-execution/calibration-log.md).

---

## Overview

This document enforces the **mandatory 5-step sprint execution flow** used in V2 (Phase 49+). Phase 35-38 violated this flow by skipping plan + checklist, leading to scattered implementation and poor traceability.

**Golden Rule**: `Phase README → Sprint Plan → Sprint Checklist → Code → Update Checklist → Progress Doc`

---

## Mandatory 5-Step Workflow

### Step 1: Create Plan File

**Before writing any code**, create sprint plan at `docs/03-implementation/agent-harness-planning/phase-XX-name/sprint-XX-Y-plan.md`.

**Required Sections**:
- **Sprint Goal**: One sentence. What does this sprint deliver?
- **User Stories**: 3-5 stories in "As a / I want / So that" format
- **Technical Specifications**: Design decisions, architecture rationale, technology choices
- **File Change List**: Explicit list of all files to be created/modified (with counts)
- **Acceptance Criteria**: Measurable, testable definition of done
- **Deliverables**: `- [ ]` checkbox list mapping to stories
- **Dependencies & Risks**: What could block? What's the mitigation?

**Reference Template** (FROZEN — REFACTOR-008, 2026-06-17): Mirror the **frozen canonical template** `claudedocs/templates/sprint-plan-template.md` — an ABSOLUTE anchor, **NOT** the most-recent sprint's plan. Mirror its §0-9 section structure + the `**Status/Branch/Base/Slice/Scope decisions**` metadata block + the 2 readability rules it enforces: **(1) the H1 is ONE short scope line** — the full description goes in the `**Summary**` block, never embedded in the H1; **(2) §0 Background uses sub-headers + line breaks**, not a wall of prose. Express sprint scope differences through **content** (more stories / files / risks), **never through structure** (don't add/rename sections, don't change the Day count).

**Why FROZEN** (drift audit, REFACTOR-008): the prior "mirror the most-recent completed sprint" rule used a RELATIVE / floating anchor — each sprint copied the previous, so small per-sprint drifts compounded monotonically. Audit across 80+ sprints: 49.1 (freeform 中文, no §-numbering) → 51.2/52.1 (clean §0-9 中文) → 57.107-130 (英文, ~600-char run-on H1, dense §0). Any adjacent pair looked "consistent"; the cumulative drift was large. The frozen template stops the ratchet. (The 51.2/52.1 §0-9 was the prior closest-to-canonical; the 57.x era added genuinely valuable sections — §6 Deliverables, §7 Workload Calibration, the metadata block, Drive-through — which the frozen template KEEPS while fixing the H1 + §0-density defects.)

**Why**: Prevents vague scope. Forces thinking before coding. Becomes sprint contract. Format consistency lets reviewer / next-session AI navigate any sprint plan with the same mental map.

**Violation Pattern** ❌: "I'll start coding and see what happens" → scattered PRs → unclear scope → Phase 35-38 repeat.

**Violation Pattern** ❌ (Sprint 52.1 v1 — 2026-04-30): Drafted plan with 10 sections + 6 days + custom section names without consulting most recent (51.2) plan format. User had to point out inconsistency; 3 rewrites (v1→v2→v3) before format aligned. **Lesson**: Read prior sprint plan FIRST, then mirror exactly.

#### Workload Calibration (Sprint 53.7+ — closes AD-Sprint-Plan-1)

Plan §Workload (or equivalent header) **must** state estimate in this three-segment form:

> Bottom-up est ~X hr → calibrated commit ~Y hr (multiplier Z)

- **X** = sum of per-task / per-US bottom-up estimates (raw, no calibration applied)
- **Z** = calibration multiplier in [0.4, 1.0]; default **0.5–0.6** (mid-band 0.55) per 53.4 + 53.5 + 53.6 retrospectives Q2 evidence (3 consecutive ~50% over-estimate; ~7-14 hr banked across 3 sprints)
- **Y** = X × Z = number you actually commit to (PR description / sprint goal acceptance / Day 4 retrospective Q2 baseline)

**When to adjust the multiplier**:
- 3+ consecutive sprints with `actual / committed > 1.2` → raise multiplier (e.g. 0.55 → 0.70) — under-estimating
- 3+ consecutive sprints with `actual / committed < 0.7` → lower multiplier (e.g. 0.55 → 0.40) — buffer too generous
- Single-sprint outliers: ignore; 3-sprint moving evidence required

**Day 4 retrospective Q2 must verify the multiplier**:
- Compute `actual_total_hr / committed_total_hr` ratio
- Document delta vs expected `≈ 1.0`
- If `|delta| > 30%`: log `AD-Sprint-Plan-N+1` to revisit multiplier in next plan template iteration

**Why**: Three consecutive ~50% over-estimate sprints (53.4 + 53.5 + 53.6) showed bottom-up estimates consistently double actual; without calibration, sprint commitments were inflated and "banked" hours obscured velocity tracking.

**First plan to apply**: Sprint 53.7 itself (`sprint-53-7-plan.md` §Workload).

#### Four-segment form when `agent_factor` applies (Sprint 57.43+ — ACTIVATED 2026-05-25 per Sprint 57.42 retro)

When the sprint anticipates code-implementer agent-delegation as the primary Day 1 mechanism (≥ 80% of Day 1 work via agent), Plan §Workload **must** use the four-segment form:

> Bottom-up est ~X hr → class-calibrated commit ~Y hr (mult Z) → agent-adjusted commit ~Y' hr (agent_factor 0.55)

where `Y' = Y × 0.55 = X × Z × 0.55`. See `calibration-matrix.md` §Active Agent Delegation Factor Modifier for full formula, evidence, rollback rule, and tracking discipline.

**MANDATORY plan-time `Agent-delegated:` field** (Sprint 57.57+ — codified via `AD-Plan-Workload-AgentDelegation-Explicit-Field-Codification` PROMOTION; 5-data-point evidence Sprint 57.53+57.54+57.55+57.56+57.57 consecutive usage):

Plan §Workload section MUST include an explicit `Agent-delegated:` field at plan-time (NOT just retrospective Q2). Acceptable values:

- **`yes`** — ≥ 80% of Day 1 work via code-implementer agent. Apply 4-segment form with appropriate `agent_factor` sub-class baseline. Required for sprints generating validation data points under the tier-4 agent_factor sub-class table (in `calibration-matrix.md`).
- **`partial`** — 20-79% via agent. Apply `agent_factor = 0.75` linear interpolation per §Active block formula. Sprint plan §Workload still uses 4-segment form.
- **`no`** — < 20% via agent (parent-assistant-direct execution). Apply `agent_factor = 1.0`. Sprint plan §Workload uses 3-segment form (no agent-adjusted commit line; class-calibrated commit IS the final commit).
- **`TBD-Day-1-decision`** — when delegation choice is contingent on Day 0 三-prong findings or Day 1 scope clarification (e.g. Sprint 57.45 Path A vs Path B branch). MUST resolve to `yes`/`no`/`partial` by Day 1 start; recorded as final value in retrospective Q2.

**Rationale** (5-data-point evidence base): plan-time `Agent-delegated:` field surfaced calibration class selection decisions upfront (Sprint 57.53 parent-direct → `agent_factor = 1.0` applied retroactively per Sprint 57.45 Path B precedent; Sprint 57.54-57.57 all delegated-yes pre-declared and consistently honored). Without this field, the `agent_factor` row in §Active block was inconsistently applied — some sprints retroactively classified, some pre-declared. Pre-declaration prevents retro confusion AND surfaces sub-class baseline selection (mechanical-pattern-reuse-heavy 0.30 vs -greenfield-port-style 0.45 vs -design-decisions 0.65) in plan §Workload §Sub-class declaration. Per AD-Plan-2/3/4/5 promotion precedent: 3-data-point evidence sufficient; Sprint 57.57 = 5th consecutive consistent usage.

**Tracking discipline cross-ref**: `calibration-matrix.md` §Active Agent Delegation Factor Modifier §Tracking discipline (MANDATORY from Sprint 57.43+) §3 row reads "**NEW**: explicit `agent-delegated: yes / no / partial` tag" — Sprint 57.57 codification clarifies this is PLAN-TIME tag (was ambiguous between plan-time vs retro-time in original wording).

#### Scope-class multiplier matrix + agent_factor — MOVED to on-demand (REFACTOR-011, 2026-07-14)

> **Read [`calibration-matrix.md`](../../docs/03-implementation/agent-harness-execution/calibration-matrix.md) at the two moments that need it**: (1) **plan drafting** — the 3/4-segment §Workload forms above REQUIRE the scope-class multiplier + agent_factor tier from that table (the section cannot be completed without the lookup); (2) **Day 4 closeout** — append/update your class row THERE (≤ 1 line ~250 chars; full narration → calibration-log §1, per the fill-in skeleton in the frozen checklist template). Hygiene is lint-enforced: `scripts/lint/check_rules_hygiene.py` (12th in run_all) fails any matrix row > 400 chars and any always-loaded rule file over its size budget — the mechanical guard REFACTOR-005/-009 lacked.

### Step 2: Create Checklist File

**Immediately after plan approval**, create sprint checklist at `docs/03-implementation/agent-harness-planning/phase-XX-name/sprint-XX-Y-checklist.md`.

**Required Format**:
```markdown
# Sprint XX.Y — Checklist

[Link to plan]

## Day N — Task Group

### N.M Task Description
- [ ] **Specific deliverable**
  - DoD: Measurable definition of done
  - Command: `git ...` or `pytest ...`
- [ ] **Next deliverable**
  - ...
```

**Key Rules**:
- Use `- [ ]` format
- Each task should be a single logical unit (break down if checklist entry covers >1 commit's worth of work)
- Include DoD (Definition of Done) — how to verify
- Map each task to plan's acceptance criteria
- Assign to days (Day 1-5 for typical sprint)
- **DO NOT include time estimates in checklist** (since Sprint 55.3 / AD-Lint-2):
  - ❌ ~~`## Day N — Task Group (Estimated X hours)`~~ — drop "(Estimated X hours)" header
  - ❌ ~~`### N.M Task Description (Y min)`~~ — drop "(Y min)" suffix
  - ❌ ~~`- Estimated: Y min`~~ sub-bullets — drop entirely
  - ✅ Sprint-aggregate `Bottom-up est ~X hr → calibrated commit ~Y hr` lives in plan §Workload only
  - ✅ Per-day / per-task actuals (with informal estimates if useful) → progress.md Day entries (individual record, non-binding)
  - **Why** (Sprint 53.7 retrospective Q4 evidence): Day-level estimates have higher variance than sprint-level (banking offset Day N over-runs against budget). Per-day calibrated targets create false precision and trigger anxiety mid-sprint when Day N slips. Sprint-aggregate calibration is the only signal that survives 3-sprint moving evidence (per §Workload Calibration above).

**Reference Template** (FROZEN — REFACTOR-008, 2026-06-17): Mirror the **frozen canonical template** `claudedocs/templates/sprint-checklist-template.md` — an ABSOLUTE anchor, **NOT** the most-recent sprint's checklist (same drift rationale as §Step 1). Day 0-4 (5 days); each task = bold deliverable + DoD + Verify command; NO time estimates; header line SHORT (full description lives in the plan's `**Summary**`, not duplicated here).

**Format Consistency Rule**: Same Day count (5 days, Day 0-4), same per-task detail depth, same DoD/Verify command patterns. Scope differences expressed through **content** (more checkboxes inside a Day), **not structure** (don't add Day 5 / Day 6).

**Violation Pattern** ❌ (Phase 42 Sprint 147): Deleting unchecked `[ ]` items when scope shrinks. This hides what was planned vs. what shipped.

**Violation Pattern** ❌ (Sprint 52.1 v1-v2 — 2026-04-30): First draft used 6 days (Day 0-5); second draft was 27% shorter than 51.2 with insufficient per-task detail. Both required rewrites. **Lesson**: Match prior sprint's day count + detail depth before drafting.

✅ **Correct behavior**: Only change `[ ]` → `[x]`. If scope cuts, leave `[ ]` and note reason in progress.md.

---

### Step 2.5: Day-0 Plan-vs-Repo Verify (Sprint 55.3+ — closes AD-Plan-1; AD-Plan-3 promoted Sprint 55.6; AD-Plan-4 Schema-Grep promoted Sprint 57.1)

**Mandatory** between plan/checklist drafting and Day 1 code start. Plans drafted from session memory + retrospective context **drift from real repo** because:

- Class names get renamed between sprints (e.g. `_obs.py` may already exist when plan assumes new file)
- Table names change in Alembic migrations between PR drafts
- Test fixture paths shift when `conftest.py` is restructured
- Service/method signatures evolve in unrelated PRs while plan was being written
- **Wrong-content drift**: file exists but body diverged from plan's claim (e.g. plan asserts `_retry_policy` is dead but path verify alone can't see the body's call sites; or plan asserts ABC `ToolErrorDecision` exists but the ABC was never created)

**Cost when skipped**:
- Sprint 53.7 retrospective Q4 — 5 path-drift findings (D4-D12) cost ~1 hr Day 1+ re-work
- Sprint 55.3 Day 0 — 3 path-drift findings (D1-D3) caught in ~30 min before code starts
- Sprint 55.5 Day 0-2 — **5 wrong-content drifts** (D1+D2+D4+D5+D7) caught via AD-Plan-3 first application; ~55 min cost prevented ~3-4 hr re-work (4-8× ROI)
- Sprint 55.6 Day 0-3 — **11 wrong-content drifts** (D1-D11) caught via AD-Plan-3 second through sixth applications; ~75 min cost prevented ~9-10 hr re-work + 2 production-grade bugs (7-8× quantitative + 2 critical correctness saves)

#### Required actions (Day 0, before Day 1 code) — full procedures MOVED to on-demand (REFACTOR-011, 2026-07-14)

The verify is a **three-prong grep pass** (+ Prong 2.5 sub-prong for frontend page sprints); all prongs are mandatory when applicable. **Read [`docs/rules-on-demand/day0-plan-verify.md`](../../docs/rules-on-demand/day0-plan-verify.md) at every Day 0** for the full prong procedures + drift-class grep tables + ROI evidence + worked examples. Summary:

- **Prong 1 — Path Verify** (AD-Plan-2): every plan-mentioned file path → Glob/ls exists-as-expected (incl. test-infra files — the 57.66 phantom-file lesson).
- **Prong 2 — Content Verify** (AD-Plan-3): every plan factual claim about existing code → Grep the asserted symbol/pattern (drift classes incl. dead-entry-points / missing-imports / renamed-symbols / missing-ABCs / wrong-units / silent-constraint-delta / stale-docstrings / missing-storage-path / missing-canonical-service / nested-shape-mismatch / flat-codegen-shape / no-live-producer).
- **Prong 2.5 — Child Component Tree Depth Audit** (AD-Plan-5; frontend page sprints only): depth-2 grep into imported child components for style/structure drift.
- **Prong 3 — Schema Verify** (AD-Plan-4; DB schema in scope only): column-level grep of tables / FKs / migration-head / RLS vs plan-asserted schema (+ physical-column-vs-ORM-alias).

##### Catalog drift findings

In `progress.md` Day 0 entry under "Drift findings" header:

- Format: `D{N}` ID + Finding + Implication
- Cross-reference to plan §Risks (where finding may shift scope or risk profile)
- **Do NOT silently update plan §Technical Spec** — instead, add finding to plan §Risks. This preserves audit trail of what was originally planned vs. what reality forced. (See `anti-patterns-checklist.md` AP-2 — "no orphan code".)

##### Decide go/no-go for Day 1

- Findings shift scope by ≤ 20% → continue Day 1 with risk noted in §Risks
- Findings shift scope by 20-50% → revise plan §Acceptance Criteria + §Workload, re-confirm with user
- Findings shift scope by > 50% → abort sprint; redraft plan with reality baseline

#### Cross-references

- `anti-patterns-checklist.md` AP-2 (no orphan / phantom code references — drift findings preserve audit trail vs. silent plan rewrite)
- `.claude/rules/file-header-convention.md` §Modification History (drift findings during refactor go in MHist; AD-Lint-MHist-Verbosity char-count budget complements this rule)
- §Common Risk Classes below (recurring drift patterns deserve catalog entries)

✅ **Correct flow**: Plan drafted → Checklist drafted → **Day-0 探勘 grep (Prong 1 path-verify + Prong 2 content-verify + Prong 3 schema-verify when DB schema in scope) + drift findings catalogued in progress.md** → Day 1 code starts.

❌ **Wrong flow** (Sprint 53.7 pre-AD-Plan-1): Plan drafted → Day 1 code → discover plan-vs-repo gaps mid-implementation → re-work checklist + plan + commits.

❌ **Wrong flow** (Sprint 55.5 pre-AD-Plan-3 first application): Path verify only (Prong 1) → Day 1 code → discover content gaps mid-implementation (file exists but body wrong; ABC doesn't exist; field uses wrong units).

❌ **Wrong flow** (Sprint 56.1 pre-AD-Plan-4 first observation): Path + content verify only (Prong 1+2) → Day 1 migration / ORM code → discover column drift at first migration test run (D26+D27 — column type / nullable mismatch).

---

### Step 3: Implement Code

**Only after both plan + checklist exist**.

**Workflow**:
1. Review sprint plan + checklist
2. Create feature branch: `git checkout -b feature/sprint-XX-Y-<scope>` (use scope from git-workflow.md)
3. Code against checklist deliverables (one at a time)
4. Commit frequently (one logical unit per commit)

**Prohibited** ❌:
- Starting code before plan/checklist approved
- Committing without checklist entry
- Scope creep without updating plan + checklist

---

### Step 4: Update Checklist During Implementation

**Daily workflow**:
- Morning: Review today's checklist tasks
- As you complete: `[ ]` → `[x]` (change, never delete)
- If blocked: Add notation `🚧 阻塞：<reason>` below the task, continue working or escalate
- End of day: Commit checklist updates

**Sacred Rule** (Phase 42 Sprint 147 violation):
- ❌ **Never delete** `[ ]` items that weren't done
- ❌ **Never hide** scope cuts by removing lines
- ✅ **Always mark**: `[x]` when done, `[ ]` when not (or abandon formally)

**Why**: Traceability. In retrospective, we see what was planned vs. shipped.

---

### Step 5: Create Progress & Documentation

**Daily (evening)**:
- Update `docs/03-implementation/agent-harness-execution/phase-XX/sprint-XX-Y/progress.md`

#### 🆕 Step 5.5: Spike Sprint Design Note Extract Pattern（2026-05-08+ — closes doc-level rolling discipline）

**When to apply**:
若 sprint 是 **spike sprint**（用於探索新領域 / 新 gap fill — 例：Phase 57.7 IAM Block A spike / 57.8 SOC 2 + SBOM spike / 57.9 Status Page + APAC compliance spike）：**Day 4 closeout 必須額外產出 1 份 design note**（extract from real implementation）。

**When NOT to apply**:
若 sprint 是 **feature continuation sprint**（單純擴充已驗證範疇 — 例：Phase 57.4 admin tenants list 是延伸 57.3 tenant settings pattern reuse）：**不需** design note；只需 progress.md + retrospective.md。

Full **8-Point Quality Gate** (per-point checklist) + the quality-is-verified-ratio table + the Day-4 retrospective self-check record format MOVED to [`docs/rules-on-demand/spike-design-note-gate.md`](../../docs/rules-on-demand/spike-design-note-gate.md) (REFACTOR-011, 2026-07-14) — **read it at every spike sprint's Day 4 closeout**. Template: `claudedocs/templates/spike-design-note-template.md`. The retrospective MUST record the 8-point self-check (format in the on-demand file).

- Format:
  ```markdown
  # Sprint XX.Y Progress — YYYY-MM-DD

  ## Today's Accomplishments
  - Task X.Y completed (approx. Z min under/over estimate)
  - Issue: blockers, discoveries

  ## Remaining for Next Day
  - Task X.Z (pre-work done)

  ## Notes
  - Learning / decision / risk
  ```

**Sprint end**:
- Create `retrospective.md` covering: did well / improve next sprint / action items + estimate accuracy %

**Per-day estimates live here** (Sprint 55.3+ — AD-Lint-2 follow-on):
- Since checklist no longer carries "(Estimated X hours)" / "(Y min)" headers, **progress.md is the single home for per-day / per-task time tracking**.
- Format inside "Today's Accomplishments": `Task X.Y — actual Z min (est ~W min, delta ±N%)`
- Sprint-aggregate ratio computed in retrospective.md Q2 from sum of progress.md actuals vs. plan §Workload committed hours.
- Per-task estimates here are **non-binding individual record** — they help calibrate next sprint's bottom-up estimates but do not gate Day N completion.

**What NOT to do** ❌:
- "We'll update docs after the sprint" → too late, details lost
- Skip retrospective → patterns repeat
- Generic notes ("worked on stuff") → no data for future planning

---

## Sprint Closeout: CLAUDE.md + MEMORY.md Update Policy (Sprint 57.22+ — closes REFACTOR-001 Step 2)

**Trigger**: After Day N retrospective.md written, before opening next sprint plan. The 5-step workflow (§Mandatory 5-Step Workflow above) writes sprint execution artifacts (plan / checklist / progress / retrospective / memory subfile); this policy governs the **navigator files** (CLAUDE.md / MEMORY.md) — keep them lean, never archive sprint records inside them.

### Core Principle

| File | Role | What belongs |
|------|------|-------------|
| **CLAUDE.md** | Navigator / Principle / Rule | Timeless statements (mission / 11+1 範疇 / 5 大約束 / Mockup-Fidelity rule / Sprint Workflow rules / Karpathy / file-header convention); navigators to authoritative sources (V2 規劃文件導航 21 份 / ClaudeDocs structure / V1 reference table); current-phase milestone (1 line, principle-level) |
| **MEMORY.md** | Quality Pointer Index | Per-topic 1 pointer entry: subfile link + 1-sentence topic + keywords for future retrieval |
| **Memory subfile** (`memory/project_phase57_XX_*.md`) | Per-sprint detail | Full retro highlights / calibration / carryover ADs / file change list |
| **Retrospective** (`docs/03-implementation/agent-harness-execution/phase-XX/sprint-XX-Y/retrospective.md`) | Authoritative full Q1-Q7 retro | Sprint-level truth source |
| **Sprint plan §Workload** | Calibration source-of-truth | Multiplier / ratio per scope class |
| **`claudedocs/1-planning/next-phase-candidates.md`** | Open items / pending decisions | Next Phase 候選 / carryover AD list |
| **Git log + PR description** | Commit-level + sprint-level ground truth | Authoritative |

**Single-source rule**: Sprint detail lives in **memory subfile + retrospective.md** only. CLAUDE.md / MEMORY.md are pointers, NOT archive.

### CLAUDE.md Update at Sprint Closeout — Minimal Touch

**Allowed** ✅:
- Update `Current Sprint` row — 1 line. **Two cases**: (i) a next sprint is selected → next sprint id + branch name; (ii) **rolling-discipline interregnum** (sprint merged, next NOT yet selected) → `**No active sprint** (awaiting next-phase selection) — last shipped Sprint XX.YY MERGED (PR #N, main <sha>)`, NOT a stale `PR-pending`
- **Post-merge status flip** (codified 2026-06-16; closes the interregnum-staleness gap): closeout doc edits are written during Day 4 **before** the PR merges → they label the sprint `PR-pending` / `NOT pushed`. After a `gh`-verified merge, flip those labels → `MERGED (PR #N, main <sha>)` on the TWO current-status surfaces only — CLAUDE.md `Current Sprint` row + `next-phase-candidates.md` head carryover block. Older per-sprint carryover blocks are historical snapshots (each PR# is recoverable from its memory subfile + git log) — do a truthful batch `PR-pending → MERGED` sweep only if they accumulate misleadingly (one done 2026-06-16 for Sprint 57.112-126), not every closeout
- Update `Last Updated` footer line — 1 line: `**Last Updated**: YYYY-MM-DD (Sprint XX.YY — short goal); see memory/ for sprint history`
- Update `Phase` / `Roadmap` row IF milestone reached (e.g. V2 22/22 → SaaS Stage 1 1/3, Phase 57+ Frontend N/N+1)
- Update `Tech Stack` / `Architecture` / `Branch Protection` rows IF actually changed (rare; e.g. CI policy change)
- Add new principle / rule sections (e.g. Sprint 57.19's new "Frontend Mockup-Fidelity Hard Constraint" — that's a timeless rule, belongs here)

**Forbidden** ❌:
- Add `Latest Sprint` / `Prev Sprint` / `Prev-Prev Sprint` / `Prev³` / `Prev⁴` rows packed with retro detail
- Pack carryover ADs / calibration ratios / commit SHAs / PR numbers / Vitest counts / bundle KB sizes / file change lists into any table cell
- Add multi-paragraph history blocks to `Last Updated` footer
- Add `[Sprint XX historical row preserved below]` archive blocks at end of CLAUDE.md
- Inline `Next Phase 候選` 20-bullet pending lists into a table cell

**Violation Pattern** ❌ (pre-cleanup state captured by REFACTOR-001 audit 2026-05-18): CLAUDE.md grew from ~30 KB foundation to **77 KB** over 20+ Phase 57+ sprints; ~58 KB was duplicate sprint records (table cells × 6 sprints + footer multi-paragraph history + `[historical row preserved]` blocks + 20-bullet `Next Phase 候選`).

### MEMORY.md Update at Sprint Closeout — Quality Pointer

**Allowed** ✅ — Add 1 entry of this shape (~250-300 char total, 3-4 lines):
```markdown
- [project_phase57_XX_<topic>.md](project_phase57_XX_<topic>.md) — Sprint XX.YY closed YYYY-MM-DD; <1-sentence what>; <1 phrase distinguishing feature or anomaly>.
  Keywords: <feature/AD/class/anomaly names for future retrieval>
```

Example (good pointer):
```markdown
- [project_phase57_21_chatv2_mockup_fidelity_phase_1.md](project_phase57_21_chatv2_mockup_fidelity_phase_1.md) — Sprint 57.21 closed 2026-05-18; Chat-v2 Turn Block Model + 3-col shell + Inspector 4-tab + Composer scaffolding; bimodal calibration pattern emerging.
  Keywords: chatv2, mockup-fidelity Phase-1, Turn Block, Inspector 4-tab, frontend-mockup-direct-port class, bimodal ratio
```

**Forbidden** ❌:
- Dump retro Q1-Q7 content into the entry
- List specific calibration ratio numbers (those live in subfile + `calibration-matrix.md`)
- List commit SHAs / PR numbers / Vitest counts / bundle KB sizes (in subfile + retrospective)
- Make entry >500 char (~300 is comfortable ceiling; quality matters more than rigid limit per user 2026-05-18 — but >500 signals you're packing summary instead of pointing)

**Quality Criteria** — Does the pointer let future AI / dev find this sprint when they search by keyword?

| Quality | Example |
|---------|---------|
| ✅ Good keywords | feature name (`chatv2`, `mockup-fidelity`) / AD ID (`AD-Tailwind-v4`) / class name (`frontend-mockup-direct-port`) / anomaly pattern (`bimodal`, `silent CSS no-op`) |
| ❌ Bad keywords | generic terms ("frontend", "refactor") / date-only / sprint-id-only / numbers without context |

**Header rule statement** (in MEMORY.md opening): the prior「每行 ≤ 200 字符」hard limit is updated to「**quality pointer principle**: topic + keywords + subfile path; detail single-source in subfile; ~300 char comfortable ceiling, but quality matters more than character count」per user clarification 2026-05-18.

### Open Items / Pending Decisions Destination

**Forbidden** ❌:
- `Next Phase 候選` 20-bullet lists in CLAUDE.md table cells (was pre-cleanup case)
- Pending AD candidates / unresolved issues in CLAUDE.md table cells
- Time-bound TODOs / schedule notes in CLAUDE.md

**Allowed** ✅:
- Maintain `claudedocs/1-planning/next-phase-candidates.md` as **single-source** for open / pending items
- Sprint plan §Carryover section (in `docs/03-implementation/agent-harness-planning/phase-XX-*/sprint-XX-Y-plan.md`) lists carryover ADs for next sprint pickup
- Sprint retrospective.md §Carryover section accumulates per-sprint additions to the candidate pool
- [`calibration-matrix.md`](../../docs/03-implementation/agent-harness-execution/calibration-matrix.md) tracks cross-sprint calibration trends (matrix rows lint-capped ≤ 400 chars)

### Self-Check at Sprint Closeout (Pre-Commit)

Before commit closeout MHist, verify:

- [ ] **CLAUDE.md changes**: Only navigator / principle / rule level? (NO sprint-by-sprint history record additions)
- [ ] **MEMORY.md new entry**: ~250-300 char quality pointer (topic + keywords + subfile link)? (NOT a packed retro summary)
- [ ] **Sprint detail preserved**: Memory subfile + retrospective.md updated with full content? (YES — single-source preserved elsewhere)
- [ ] **Carryover / open items**: Documented in next sprint plan §Carryover or `claudedocs/1-planning/next-phase-candidates.md`? (NOT in CLAUDE.md table cell)
- [ ] **next-phase-candidates.md append** (post REFACTOR-010): full SHIPPED carryover narration → `next-phase-candidates-shipped-archive.md` (verbatim, newest-first); into `next-phase-candidates.md` only a **1-line §Shipped Sprints Pointer Index row + the open ADs into §Open Carryover ADs**. NO full SHIPPED block (file:line / drive-through / pytest counts / CHANGE-NNN / design note) in the main file — that is the REFACTOR-001/005/009/010 re-bloat anti-pattern.
- [ ] **Calibration ratio**: Tracked in `calibration-matrix.md` (on-demand)? (NOT in CLAUDE.md / MEMORY.md prose)
- [ ] **Matrix row lean (REFACTOR-009/-011)**: new/updated `calibration-matrix.md` row ≤ 1 line (~250 chars — lint-enforced by check_rules_hygiene)? Full narration → calibration-log §1, NOT the matrix cell.

### Why This Policy Exists (REFACTOR-001 root cause analysis 2026-05-18)

V2 evolved organic CLAUDE.md + MEMORY.md bloat pattern over Phase 57+ ship sprints (20+ sprints accumulated):
- **CLAUDE.md** grew from ~30 KB foundation to **77 KB**; ~58 KB ≈ duplicate sprint records
- **MEMORY.md** exceeded its own ≤24.4 KB system limit (actual 28 KB); 12 entries violated own ≤200 char rule (worst: 57.17 entry at ~3000 char = 15× over)
- ~9-12% session context window consumed by duplicates at session start
- **Triple-source for same sprint detail**: CLAUDE.md table cell + CLAUDE.md footer + MEMORY.md entry + memory subfile + retrospective.md (5 copies of overlapping content)

**Root cause**:
1. AI sprint-closeout pattern dumped full retro Q1-Q7 highlights into "index" entries (forgot single-source principle)
2. Sprint table cells accumulated history without archive cutoff or policy
3. No enforcement (no lint, no review checkpoint)
4. "捨不得刪" mentality: each prev sprint row felt "still useful" → kept indefinitely

**Fix**: This policy (§Sprint Closeout) + REFACTOR-001 Step 3 cleanup execution.

### Cross-References

- `claudedocs/4-changes/refactoring/REFACTOR-001-claude-md-memory-md-bloat-audit.md` — initial trigger audit (Step 1/4)
- `.claude/rules/file-header-convention.md` §Modification History char-budget rules — sibling philosophy (MHist 1-line max, detail in commit body / 4-changes record)
- MEMORY.md header rule statement — quality pointer principle (post-2026-05-18 rewording)
- `claudedocs/1-planning/next-phase-candidates.md` — open items / Next Phase 候選 single-source (created in REFACTOR-001 Step 3)

---

## Common Risk Classes (Sprint 53.7+ — closes AD-CI-4)

When drafting plan §Risks, consider these recurring risk classes (V2 carryover evidence). Each entry: `Symptom → Workaround → Long-term fix`.

### Risk Class A: Paths-filter vs `required_status_checks` (CI infra) — ⚠️ RETIRED Sprint 55.6

**Status**: **NO LONGER APPLIES.** Sprint 55.6 removed the `paths` filter from `.github/workflows/backend-ci.yml` (Option Z, closes AD-CI-5) → **every PR now runs full backend CI + v2-lints**, including docs-only / `.gitignore`-only PRs. There is no paths-filter `BLOCKED` situation and **no touch-`backend-ci.yml` workaround is needed**. The `backend-ci.yml` header is the authoritative source.

**Historical (53.2.5 – 55.6, audit trail)**: docs-only PRs once didn't trigger the path-filtered backend-ci → required contexts never reported → `mergeStateStatus = BLOCKED`. Interim fix was a header-comment touch on `backend-ci.yml` (53.2.5). Retired permanently in 55.6 by dropping the paths filter (trade-off ~+1.5 min CI per docs-only PR; acceptable for solo-dev volume).

**Residual edge case (NOT paths-filter)**: a rare GitHub webhook miss/delay can still leave checks unreported (e.g. PR #203, Sprint 57.53) — a header touch re-triggers, but that is a webhook quirk, not the retired paths-filter issue.

### Risk Class B: Cross-platform `mypy --strict` `unused-ignore` (Python tooling)

**Symptom**: 同一 import / Optional unwrap 在 Linux runner 與 Windows 開發機 mypy 行為不同（缺 stub 包 vs 有 stub 包）。`# type: ignore[X]` 在一邊需要、在另一邊變 `unused-ignore` 報錯（`warn_unused_ignores=true` strict 模式下）。

**Source**: Sprint 52.6 retrospective Q4.

**Workaround**: 雙 ignore code → `# type: ignore[X, unused-ignore]`. 兩邊都不報錯. Documented in `.claude/rules/code-quality.md` §Cross-platform mypy pattern.

**Long-term fix**: Pin Python stub package versions in `pyproject.toml` so both platforms behave identically. Independent.

### Risk Class C: Module-level Singleton Across Test Event Loops (test isolation)

**Symptom**: TestClient-based integration tests 共用 module-level singletons (e.g. `service_factory` cache / `RiskPolicy` DB cache / `MetricsRegistry`) → 第二次 fixture activate 拿到上一個 event loop 的 cached instance → 「event loop closed」cascade fail.

**Source**: Sprint 53.6 Day 4 (US-5 ServiceFactory consolidation introduced; 5 governance / audit tests failed until autouse `reset_service_factory` fixture added).

**Workaround**: Per-suite `conftest.py` autouse fixture calling `reset_*()` for affected singletons. Pattern documented in `.claude/rules/testing.md` §Module-level Singleton Reset Pattern (since 53.7).

**Long-term fix**: Refactor singletons to be DI-injected per-request (no module-level cache); avoids root cause. Per-singleton scope; track as needed.

**Related (Sprint 57.68 reinforcement, `AD-Source-DB-Call-Test-Isolation`)**: Adding a NEW DB call to a previously DB-free endpoint can surface a latent isolation leak — TestClient overrides auth but NOT `get_db_session`, so the endpoint hits a non-test session. Symptom: tests that passed pre-change fail only after the endpoint gains a query. Fix: ensure the suite's `get_db_session` dependency override (or autouse session fixture) covers the newly-DB-touching endpoint.

### Risk Class D: ORM File Path Reference Style (sprint planning)

**Symptom**: Plan §8 Risks row references an ORM model with a speculation-based path like `backend/src/infrastructure/db/models/<table_name>.py` (e.g. `tenant.py`); Day 0.8 Prong 2 then wastes 3-5 min discovering the model lives elsewhere (e.g. `identity.py` per domain cohesion grouping).

**Source**: Sprint 57.50 D-DAY0-2 — plan referenced `Tenant.meta_data` JSONB; AI initially looked at `tenant.py` (did not exist); Prong 2 grep resolved to `identity.py` per `09-db-schema-design.md` Group 1 (Identity & Tenancy domain groups User + Role + OIDCProvider + Tenant in one file). Verified in Sprint 57.51 Day 0.8 D-DAY0-3.

**Workaround**: Cite `09-db-schema-design.md §Group N <Domain Name>` in plan §Risks rows touching ORM models, not the speculation-based `.py` path. Example: "Risk: `Tenant.X` field doesn't exist — mitigation: Day 0.8 Prong 2 read `Tenant` ORM in `09-db-schema-design.md §Group 1 Identity & Tenancy` (note: file is `identity.py`, not `tenant.py`)."

**Long-term fix**: Codify in Plan template stub (when Plan template doc is formalized as part of `.claude/rules/`).

### Risk Class E: Stale long-running `--reload` backend masks a wiring/startup fix (local verification)

**Symptom**: A fix that only takes effect at process startup (lifespan wiring, env load, DI singleton construction) appears NOT to work when verified against an already-running dev backend — because the running process started BEFORE the fix landed (or its `--reload` worker reloaded module code but did NOT re-run lifespan startup). Looks like a code bug; is actually process-state.

**Source**: 2026-06-03 C-11 `cost_ledger Δ=0` (`AD-RealLLM-CostLedger-ProcessState-Verify`). FIX-022 pricing-loader wiring was on disk, but the running backend had `cost_ledger_service=None` from its own stale startup → router gate skipped every cost row. A clean restart → startup log `pricing loader wired` (`main.py:149`) → `cost_ledger Δ=2`. Compounded by 2 stale `--reload` reloaders sharing :8000 via SO_REUSEADDR (Errno 10048 on re-bind).

**Workaround**: When verifying startup/wiring behavior locally, do a CLEAN restart first: kill ALL stale uvicorn reloader+worker processes on the port (not just the listener — a `--reload` worker is a `multiprocessing.spawn` child whose cmdline lacks `uvicorn`), confirm the port is free + your new process is the sole owner (no Errno 10048), then re-verify and capture the startup log line proving the wiring fired.

**Reinforcement (Sprint 57.97, D-DAY3-1 — orphaned spawn-worker)**: The drive-through verifying cheap-tier verification recorded the STRONG model on the first 2 chats despite a `dev.py restart` reporting a fresh PID — and it was NOT a code bug (a reproduce-script proved the builder built the cheap client). The real culprit: an orphaned `multiprocessing.spawn` worker (a child of a long-DEAD reloader from a PRIOR sprint) was STILL ALIVE serving :8000 via SO_REUSEADDR with old code + old `.env`. `dev.py stop` + `netstat` + `taskkill /PID <port-owner>` ALL missed it because the socket was attributed to the dead PARENT and the worker's cmdline is `python -c "from multiprocessing..."` (no "uvicorn"). **A clean restart must verify the LIVE serving process, not the port-owner PID.** The reliable check on Windows: `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` → inspect PID / PPID / StartTime → `Stop-Process -Force` any worker whose parent is dead or whose StartTime predates the current restart. For startup-only/env-loaded behavior (the cheap client is built at startup from `.env`), set the env BEFORE the restart and confirm the fresh PID is the SOLE live worker.

**Long-term fix**: Prefer `python scripts/dev.py restart backend` (kills by port owner) over assuming the running process is current; for one-off wiring checks, a no-`--reload` single process with log redirect gives a deterministic startup log. When SO_REUSEADDR orphans recur, fall back to the `Win32_Process` PID/PPID/StartTime sweep above (port-owner kills are insufficient against spawn-worker orphans).

### How to use this section

When drafting plan §Risks, scan this catalog. If any class applies to your sprint scope, copy the symptom + workaround text into your plan §Risks table. Add new classes here when 2+ sprints hit the same root cause.

---

## Change Record Conventions

When fixing bugs or implementing features, create corresponding document in `claudedocs/4-changes/`:

| Type | Directory | Naming | When |
|------|-----------|--------|------|
| Bug Fix | `4-changes/bug-fixes/` | `FIX-XXX-description.md` | Any bug fix |
| Feature Change | `4-changes/feature-changes/` | `CHANGE-XXX-description.md` | Feature enhancement |
| Refactoring | `4-changes/refactoring/` | `REFACTOR-XXX-description.md` | Code restructure |

**Format** (1 page):
```markdown
# FIX-123: <Description>

**Date**: 2026-05-15
**Sprint**: 50.2
**Scope**: <11+1 category or cross-cutting>

## Problem
2-3 sentences. What was broken?

## Root Cause
Analysis. Why did it happen?

## Solution
What we changed. Code location. PR reference.

## Verification
How we confirmed it's fixed (test name, manual steps).

## Impact
Scope of fix (backend-only? frontend? integration?).
```

**Daily Workflow**:
1. **Morning**: Check `claudedocs/3-progress/daily/` latest log
2. **When fixing bug**: Create `claudedocs/4-changes/bug-fixes/FIX-XXX-<issue>`
3. **When changing feature**: Create `claudedocs/4-changes/feature-changes/CHANGE-XXX-<feature>`
4. **End of day**: Use SITUATION-5 to save progress (which creates daily log entry)

---

## Sprint Naming & Directory Structure

**Standard format** (from 06-phase-roadmap.md):

```
phase-XX-name/
├── sprint-XX-Y-plan.md           ← Must exist before coding
├── sprint-XX-Y-checklist.md      ← Must exist before coding
└── ...

agent-harness-execution/
└── phase-XX/
    └── sprint-XX-Y/
        ├── progress.md           ← Daily entries during sprint
        ├── retrospective.md      ← End of sprint
        └── artifacts/            ← Evidence files
```

**Branch naming** (from git-workflow.md):
```
feature/sprint-XX-Y-<scope>
```

**Commit messages**:
```
feat(<scope>, sprint-XX-Y): <description>

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Common Violation Patterns & Consequences

| Pattern | Evidence | Why Bad | Fix |
|---------|----------|---------|-----|
| **Skip Plan** | Code appears without plan.md | Unknown scope → unclear PR → rework | Always: plan → checklist → code |
| **Skip Checklist** | Implementation doesn't track tasks | Can't measure progress; retro blind | Checklist = truth table; mandatory |
| **Delete `[ ]` items** | Checklist shrinks mid-sprint | Hides scope cuts; retro can't diagnose (Phase 42) | Only mark `[x]` or note `[阻塞]` |
| **Update checklist after sprint** | Checklist retroactively filled in | Data quality → estimates useless | Update daily, during work |
| **Skip progress.md** | "Will write at end" | Details lost; retro weak | Write daily 10-min entry |
| **No Change records** | Bugs fixed in silence | No audit trail; same bug reappears | FIX/CHANGE/REFACTOR every time |
| **Vague DoD** | "Implement X" → what counts as done? | Infinite rework; unclear when to stop | DoD: testable + measurable |
| 🆕 **Format inconsistency** (Sprint 52.1 v1) | New plan has different section count / naming / Day count than prior completed sprint | Hard to navigate; mental overhead; user must matrix-correct | Read prior sprint's plan + checklist BEFORE drafting; mirror structure; scope differences expressed through content, not structure |

---

## Error Flow: Phase 35-38 Shortcut (DO NOT REPEAT)

```
❌ WRONG:
Phase README → Code (skip plan + checklist) → Progress Doc (scatter, incomplete)
            → Pull request with unclear scope
            → Retro says "we don't know what was planned"
```

```
✅ RIGHT:
Phase README → Sprint Plan (user stories + technical spec)
            → Sprint Checklist (task breakdown + DoD)
            → Code (implement against checklist)
            → Update Checklist (daily: [ ] → [x])
            → Progress Doc (daily progress + retrospective)
            → Pull request with full traceability
            → Retro: "estimate accuracy 85%; unblock story X.Y for next sprint"
```

---

## Daily Workflow Example

**Morning (9 AM)**:
1. Review `claudedocs/3-progress/daily/` latest entry
2. Open sprint checklist (e.g., `sprint-49-1-checklist.md`)
3. Today's tasks: **Day 2.1 — 2.4** (estimated 6 hours)
4. Create feature branch if first day

**During work**:
- Per-task estimate vs actual; mark `[x]` immediately upon completion
- If blocked, add `🚧 阻塞 (HH:MM): <reason>` and switch to another task
- Commit per logical unit with sprint scope in message

**End of day (4 PM)**:
1. Update checklist (today's done tasks `[x]`)
2. Commit checklist changes
3. Write `progress.md` entry (estimate vs actual + notes)
4. Create FIX/CHANGE/REFACTOR record if applicable

---

## Before Commit Checklist

Every commit must pass:

1. **Correspond to Sprint Checklist**
   - Commit message matches task ID
   - Checklist `[ ]` → `[x]` done before or immediately after commit

2. **Lint + Format** (from code-quality.md)
   - Backend (per-file format + type chain): `black . && isort . && flake8 . && mypy .`
   - Backend (V2 architecture lints — 6 scripts; closes AD-Lint-1 since Sprint 53.7): `python scripts/lint/run_all.py`
     - One-stop wrapper invokes 6 V2 lints with correct `--root` args (check_ap1: `backend/src` / check_promptbuilder: default `backend/src/agent_harness` / 4 auto-discover)
     - Exit 0 = all 6 green; non-zero = `<failed>/6` with per-script line summary
     - Replaces the prior 6 separate invocations (which silently mis-passed when `--root` arg mismatched script expectation — see Sprint 53.7 Day 0 drift D1)
   - Frontend: `npm run lint && npm run build` — **MUST run WITHOUT `--silent` flag** (Sprint 57.40 closes AD-Pre-Push-Lint-Silent-Suppression-Anti-Pattern). FIX-015 PR #183 CI failed in 30s with 28 ESLint `no-restricted-syntax` errors that local `npm run lint --silent` swallowed; the `--silent` flag suppresses lint error output along with package-manager noise. **Never** use `--silent` for the pre-push lint check; if you want clean output, redirect with `2>&1 | tail -20` instead (preserves errors while trimming noise).

3. **Tests Passing**
   - Backend: `pytest` (>= 80% coverage for new code)
   - Frontend: `npm run test` (>= 80% coverage)

4. **Sprint Workflow Compliance** (anti-patterns-checklist.md 11 points)

5. **No Prohibited Imports**
   - Backend agent_harness: no direct `import openai` / `import anthropic`

6. **File Headers Updated** (file-header-convention.md)

7. **Agent-delegated work — run ALL gates yourself; don't trust the agent's report** (Sprint 57.69 + 57.73)
   - Delegated FE work MUST run the FULL gate set incl. `npm run check:mockup-fidelity` (not just lint/build/test). Sprint 57.69: a delegated agent ran lint/build/test but skipped `check:mockup-fidelity`; 2 `oklch(...)` tints would have silently failed `HEX_OKLCH_BASELINE` at PR — parent re-verify caught it pre-PR.
   - Pin language / convention in the agent prompt: user-facing copy follows the codebase convention (English state strings, not 繁中). Sprint 57.73: a delegated agent wrote 繁中 state copy the parent had to rewrite.
   - Parent independent re-verify: re-run every gate yourself; treat the agent's "all green" as unverified until reproduced (57.66 stringified-float / 57.67 flat-vs-nested / 57.68 wrong isolation culprit were all caught this way).
   - Tooling: if Bash `grep` output looks corrupted (e.g. token substitution), re-read via a dedicated reader (Read/Grep tool) before acting on it (Sprint 57.70).

8. **Drive-Through Acceptance — user-facing features must be DRIVEN, not just gated** (2026-06-06; closes AD-Drive-Through-Acceptance; full rationale CLAUDE.md §Drive-Through Acceptance Hard Constraint + `memory/feedback_drive_through_over_paper_metrics.md`)
   - Any feature a human reaches through the UI MUST be verified by actually driving the real UI (dev server) + real backend + real LLM (NOT echo/mock) through its primary path BEFORE it can be marked done. Gate-pass + curl prove the parts work / the API responds; NEITHER proves the car drives.
   - Walk every control on the path: clickable? has an effect? label real (not hardcoded / fixture)? does the result actually render? (chat-v2 escape 2026-06-06: dead "New session" button + fixture session list + hardcoded `claude-haiku-4-5` badge + agent answer never rendered — all AP-4 Potemkin sitting on the 主流量, all green on every gate. PR #253 also wrote "~80-85% working" off curl-only verification with "UI 驅動未做" self-noted — exactly the trap.)
   - Do NOT write "verified" / "~X% working" for anything whose drive-through layer wasn't actually run — write "未驗證 (gate-only)" instead. Backend-not-ready widgets: render per mockup with fixture data BUT label DEMO (or leave blank) — never let fixture masquerade as real.
   - Evidence: screenshot + "observed vs intended flow" diff into progress.md / CHANGE record.
   - Scope: applies to any task touching a user-facing surface (frontend page / SSE-driven flow / API a human drives via UI). Pure-backend / pure-infra tasks that no human drives through a UI are exempt — but their reports MUST say "gate-only verified", not imply usability.

---

## Prohibited Actions

- ❌ Force push to main
- ❌ Commit without corresponding checklist entry
- ❌ Delete unchecked `[ ]` items from checklist
- ❌ Skip progress.md updates (update daily)
- ❌ Skip FIX/CHANGE/REFACTOR records for bug/feature changes
- ❌ Code before plan + checklist exist
- ❌ Commit secrets, large binaries, generated files
- ❌ Scope creep without updating plan
- ❌ Mark a user-facing feature done — or report it "verified / ~X% working" — without an actual drive-through (real UI + real backend + real LLM); gate-pass / curl is NOT drive-through (AD-Drive-Through-Acceptance; see Before Commit item 8)

---

## References

| Document | Purpose |
|----------|---------|
| CLAUDE.md §Sprint Execution Workflow | High-level discipline |
| CLAUDE.md §ClaudeDocs — Change Records | FIX/CHANGE/REFACTOR conventions |
| 06-phase-roadmap.md | 22 sprint overview + naming |
| sprint-49-1-plan.md | Plan template |
| sprint-49-1-checklist.md | Checklist template |
| git-workflow.md | Commit message format + scope |
| anti-patterns-checklist.md | 11-point code review checklist |
| category-boundaries.md | 11+1 scope isolation rules |
| file-header-convention.md | Header + Modification History format |

---

**Applies To**: V2 Phase 49+ (all 22 sprints)
