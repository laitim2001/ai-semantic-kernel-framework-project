# Sprint 55.3 — Retrospective

**Sprint**: 55.3 — Audit Cycle Mini-Sprint #1 (Groups A + G)
**Phase**: 55 (Production / V2 Closure Audit Cycles)
**Branch**: `feature/sprint-55-3-audit-cycle-A-G`
**Plan**: [`sprint-55-3-plan.md`](../../../agent-harness-planning/phase-55-production/sprint-55-3-plan.md)
**Checklist**: [`sprint-55-3-checklist.md`](../../../agent-harness-planning/phase-55-production/sprint-55-3-checklist.md)
**Date**: 2026-05-04
**Outcome**: ✅ **6/6 ADs closed** (4 doc/process + 2 backend production)

---

## Sprint Stats

| Metric | Value |
|--------|-------|
| **ADs closed** | **6/6 (100%)** |
| **Tests added** | **+18** (1416 → 1434;target ≥+12;50% over) |
| **Commits** | 6 (Day 0 setup + 4 AD commits + Day 3 commit + Day 4 closeout pending) |
| **V2 lints** | **7/7 green** (added 7th: `check_sole_mutator`) |
| **mypy --strict** | 0 errors |
| **flake8 / black / isort** | green |
| **LLM SDK leak** | 0 |
| **Alembic 0013** | upgrade + downgrade roundtrip clean |
| **Drift findings** | **8** (D1-D8 catalogued via AD-Plan-1 first self-application) |
| **V2 main progress** | 22/22 unchanged (audit cycle, not main) |

---

## Q1 — What went well ✅

1. **AD-Plan-1 first self-application** caught **3 drift findings (D1-D3) before Day 1 code starts**, saving estimated ~30 min of re-work. Validated rule's ROI immediately;the rule paid for itself in its own sprint.

2. **Bonus parametric test coverage**:
   - AD-Cat7-1 added 3 parametric tests covering remaining 3 forbidden patterns(scratchpad / tool_calls / user_input)inside same time budget — original plan asked for 3, delivered 6.
   - AD-Hitl-7 delivered 9 tests vs plan target 5-7 → 30% over coverage.
   - Total +18 tests vs plan ≥+12 → 50% over.

3. **Option A (thin wrapper delegation) for AD-Cat12-Helpers-1** preserved 7 callers' API signatures unchanged → zero downstream code churn. Option B (delete `_obs.py` + direct call) would have refactored 7 files;Option A refactored only 2.

4. **Clean delegation pattern in AD-Hitl-7**:`get_policy()` 3-tier fallback chain(DB → default_policy → hardcoded LOW/MEDIUM)preserves backward compat — existing tests (45) all green without changes;new functionality is opt-in via constructor arg.

5. **Path corrections (D4 / D7 / D8) caught during探勘 / 實作 — not after merge**. AD-Plan-1 + 認真 探勘 in each Day prevented orphan code or wrong-location commits.

6. **Rolling planning discipline maintained**:no preemptive Sprint 55.4 plan written;Day 4 retrospective Q5 below lists candidate scope only.

7. **Drift findings audit-trail rule (AD-Plan-1 §Decision matrix)** preserved — plan §Risks accumulates D1-D8 findings;plan §Spec / §File Change List **NOT** silently rewritten. This makes the diff between "what was planned" vs "what was built" visible to future auditors.

8. **Dogfooding caught AD-Lint-3 ironic self-violation**(helpers.py first MHist line was 104 chars vs new ≤100 char rule). Caught immediately at flake8;fixed before commit.

---

## Q2 — What didn't go well ⚠️

### Q2.1 Calibration ratio severely above band

```
Bottom-up est:    ~10-12.5 hr (midpoint 11.25)
Committed (0.40): ~4 hr
Actual Day 0+1+2+3+4: ~11-11.5 hr
Ratio: 11.25 / 4 = ~2.81 ⚠️
```

Ratio 2.81 is **2.4× the [0.85, 1.20] band upper bound**. Two-direction problem with calibration:
- 53.7 = 1.01 ✅ (in band)
- 54.1 = 0.69 / 54.2 = 0.65 / 55.1 = 0.68 (3 consecutive sprints below)
- 55.2 = 1.10 ✅ (first 0.40 application in band)
- **55.3 = 2.81 ⚠️ way over**

### Q2.2 Multiplier 0.40 too aggressive for medium-scope sprint

The 0.40 multiplier was set after 4 consecutive ~50% over-estimate sprints (53.4-55.1). It worked for 55.2 (close-out + tools.py mode swap = small scope). For 55.3 (6 ADs including 2 medium-backend ADs with new DB table + ABC + 9 tests), 0.40 compressed estimates too aggressively.

**Hypothesis**: multiplier should be **scope-dependent**:
- Audit-cycle / closure / template sprints → 0.40 (works for 55.2)
- Medium-backend production sprints (new tables / ABCs / 5+ wiring points) → 0.55-0.65 (matches 53.7 evidence)
- Large multi-domain sprints → 0.50-0.55 (matches 55.1 evidence)

### Q2.3 Plan §File Change List had 3 wrong paths

D4 (V2 lint scripts at project root) + D7 (Alembic versions) + D8 (test paths under platform_layer/) — all could have been caught if Day 0 探勘 had grep'd each plan §File Change List path against `find` / `Glob` output. AD-Plan-1 spec didn't explicitly enumerate "grep file paths" as required action;Sprint 55.4 plan §File Change List should be 100% Day-0 verified.

### Q2.4 Manager.py edit mid-stream lint break

Adding new MHist entry to manager.py inflated header to 100+ chars on one line → discovered only at lint chain pre-commit. AD-Lint-3 should have caught this if I had run `flake8 manager.py` immediately after edit. Lesson: **run flake8 per-file edit**, not batched at end.

---

## Q3 — What we learned (generalizable) 📚

### L1 — AD-Plan-1 ROI is real and immediate

3 drift findings caught Day 0 (D1-D3) + 5 more in Day 1-3 = 8 total. Average ~30 min saved per finding from avoided re-work / wrong-location code → ~4 hr saved over the sprint. This **exceeds the AD-Plan-1 implementation cost** (~30 min). Rule pays for itself in its own sprint.

### L2 — Calibration multiplier is scope-class dependent, not time-trend dependent

Treating the multiplier as a single global value (adjusted by 3-sprint moving evidence) misses scope variance. Future approach:

```
Calibration matrix (proposed for Phase 56+ AD-Sprint-Plan-4):

| Scope class                     | Multiplier | Evidence              |
|---------------------------------|------------|-----------------------|
| Audit cycle / template / docs   | 0.40       | 55.2 ratio 1.10       |
| Mixed (process + 1-2 backend)   | 0.55-0.65  | 53.7 ratio 1.01       |
| Medium-backend production       | 0.65-0.75  | 55.3 ratio 2.81 → est should have been ~7-8 hr commit |
| Large multi-domain              | 0.50-0.55  | 55.1 ratio 0.68       |
```

55.4 (Group B+C: Cat 8 + Cat 9 backend) = **medium-backend production** → recommend multiplier **0.65** for first application;re-evaluate after 1 sprint.

### L3 — Plan §File Change List is high-leakage; must Day-0 verify each path

Plan §Tech Spec assertions are usually class-level / behavior-level — those rarely drift between plans. **File paths drift more often** because directory conventions evolve (53.6 ServiceFactory consolidation moved governance test paths;55.1 added platform_layer/ structure;etc). AD-Plan-1 should explicitly require:

> Before Day 1 code starts, every path in plan §File Change List + §Spec must be `Glob`-verified to exist (for edits) or `Glob`-verified to NOT exist (for creates).

This is a `~5 min Day 0 task` that prevents the D4 / D7 / D8 class of drift.

### L4 — Per-file lint chain prevents mid-sprint surprise

Running `flake8 <file>` immediately after editing each file (not batched at sprint end) catches AD-Lint-3 violations + E501 in the file under edit. Cost: ~5 sec per file. Savings: avoid mid-sprint scramble + commit-message shame.

### L5 — Option A (thin wrapper delegation) > Option B (delete + refactor) when callers are many

For AD-Cat12-Helpers-1, 7 caller sites favored A (preserve API);Option B would have been viable only if ≤2 callers. Decision rule for future helper extracts:

> If callers ≥ 3, default to Option A (thin wrapper delegating to extracted primitive). Reserve Option B for ≤2 callers OR when wrapper API itself is being deprecated.

---

## Q4 — Audit Debt deferred 📋

### Q4.1 New AD logged

| ID | Description | Target |
|----|-------------|--------|
| **AD-Sprint-Plan-4** (NEW) | Multiplier matrix proposal: scope-class dependent (0.40 / 0.55-0.65 / 0.65-0.75 / 0.50-0.55) — supersedes single global multiplier strategy from AD-Sprint-Plan-3 | Phase 56+ first sprint plan |
| **AD-Plan-2** (NEW) | Extend `sprint-workflow.md` §Step 2.5 to require explicit Day-0 path verification for every plan §File Change List entry (Glob-check exists/not-exist) | Sprint 55.4+ plan template |

### Q4.2 Carryover unchanged from Sprint 55.2 retrospective Q6

| ID | Status |
|----|--------|
| AD-Cat8-1 / AD-Cat8-2 / AD-Cat8-3 | ⏳ Sprint 55.4 (Group B) |
| AD-Cat9-5 / AD-Cat9-6 / AD-Cat9-1-WireDetectors | ⏳ Sprint 55.4 (Group C) — except WireDetectors (operator-driven) |
| AD-Cat10-Wire-1 / AD-Cat10-VisualVerifier / AD-Cat10-Frontend-Panel / AD-Cat10-Obs-Cat9Wrappers | ⏳ Sprint 55.5 / 55.6 (Group D / F) |
| AD-Cat11-Multiturn / AD-Cat11-SSEEvents / AD-Cat11-ParentCtx | ⏳ Sprint 55.5 (Group E) |
| AD-Phase56-Calibration | **superseded by AD-Sprint-Plan-4** (this retro) |
| AD-Cat12-BusinessObs / AD-Lint-3 (no, closed by 55.3) / AD-Cat12-Helpers-1 (closed by 55.3) | various |
| #31 V2 Dockerfile / AD-CI-5 / AD-CI-6 | ⏳ infra track (no sprint binding) |

---

## Q5 — Next steps (rolling planning)

> Per `.claude/rules/sprint-workflow.md` rolling planning rule: candidate scope only;NO preemptive Sprint 55.4 plan written.

### Sprint 55.4 candidate scope — Groups B + C (Cat 8 + Cat 9 backend)

```
AD-Cat8-1   RedisBudgetStore + fakeredis integration test
AD-Cat8-2   RetryPolicyMatrix wire 進 AgentLoop end-to-end
AD-Cat8-3   Soft-failure 路徑保留 original Exception type
AD-Cat9-5   ToolGuardrail max-calls-per-session counter
AD-Cat9-6   WORMAuditLog real-DB integration tests
```

Estimated bottom-up: ~7-9 hr → **multiplier 0.65** (medium-backend production class per L2) → committed ~5-6 hr。

User approval of scope required before Sprint 55.4 plan/checklist drafting begins。

### Sprint 55.5 candidate scope — Groups D + E (Cat 10/11 backend)
### Sprint 55.6 candidate scope — Group F (Cat 10 frontend)

(Per rolling planning, NOT detailed here — drafted only when 55.4 closes.)

---

## Q6 — Multiplier 0.40 1st-of-2 application validation + Phase 56+ implications

### Calibration history

| Sprint | Multiplier | Bottom-up | Committed | Actual | Ratio | Band? |
|--------|------------|-----------|-----------|--------|-------|-------|
| 53.7 | 0.55 | 13.5 hr | 7.4 hr | 7.5 hr | **1.01** | ✅ |
| 54.1 | 0.55 | 18.5 hr | 10.2 hr | 7 hr | **0.69** | below |
| 54.2 | 0.55 | 22.5 hr | 12.4 hr | 8 hr | **0.65** | below |
| 55.1 | 0.50 | 22 hr | 11 hr | 7.5 hr | **0.68** | below |
| 55.2 | 0.40 | 17.5 hr | 7 hr | 7.7 hr | **1.10** | ✅ |
| **55.3** | **0.40** | **11.25 hr** | **4 hr** | **~11.5 hr** | **~2.81** | **⚠️ over** |

### 6-sprint moving stats

- **Mean**: (1.01 + 0.69 + 0.65 + 0.68 + 1.10 + 2.81) / 6 = **1.16** (just inside band upper)
- **Variance**: very high (range 0.65 - 2.81 = 2.16);std dev ≈ 0.85
- **In-band count**: 2/6 (33%) — 53.7 + 55.2 only

### Diagnostic

Single global multiplier oscillates between **under-estimate** (0.55 sprints below) and **over-estimate** (0.40 medium-scope sprint above) without finding equilibrium. Root cause:**scope class differs**.

### Recommendation for Phase 56+

**Adopt scope-class multiplier matrix** (per AD-Sprint-Plan-4):

```
Sprint scope class detector:
  - "Audit cycle / docs / template" if 70%+ of ADs are non-code → 0.40
  - "Medium-backend" if has 1-2 ADs with new DB table OR new ABC OR 5+ wirings → 0.65
  - "Large multi-domain" if affects 3+ business domains OR 10+ files → 0.55
  - "Mixed" if balanced process + 1-2 backend → 0.55
```

For each new sprint, plan §Workload header should state:
```
Scope class: <class>
Multiplier: <multiplier per class>
Bottom-up est: ~X hr → calibrated commit ~Y hr
```

After 3-4 sprints under matrix, re-evaluate;if any class persistently outside [0.85, 1.20] band, adjust that class's multiplier.

### Sprint 56.1 first application

- Scope: Phase 56 SaaS Stage 1 (multi-tenant infrastructure + billing) → **Large multi-domain class**
- Recommended multiplier: **0.55**
- Sprint 56.1 retro Q2 must verify ratio in band;if outside → AD-SaaS-Plan-1 re-baseline that class

---

## Sprint 55.3 closeout

- **Branch**: `feature/sprint-55-3-audit-cycle-A-G`
- **Commits (5+1)**:
  - `ab42b076` Day 0 plan + checklist + progress
  - `bc468477` AD-Plan-1 + AD-Lint-2
  - `144c4595` AD-Lint-3
  - `52d802a9` AD-Cat12-Helpers-1
  - `cd86a814` AD-Cat7-1
  - `c09d3cc5` AD-Hitl-7
  - Day 4 closeout: pending
- **Tests**: 1416 → **1434** (+18, 50% over plan ≥+12)
- **V2 lints**: 6 → **7** (added `check_sole_mutator`)
- **V2 main progress**: 22/22 unchanged (audit cycle, not main)
- **Next sprint**: Sprint 55.4 candidate scope = Groups B + C (Cat 8 + Cat 9 backend) — user approval pending

---

**Status**: ✅ Sprint 55.3 main work complete. Day 4 closeout commit (this retrospective + SITUATION sync + memory update) → push → PR → CI → merge.
