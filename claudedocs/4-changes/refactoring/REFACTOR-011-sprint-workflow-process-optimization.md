# REFACTOR-011: sprint-workflow.md write-flow optimization (lint enforcement + on-demand split)

**Date**: 2026-07-14
**Sprint**: cross-sprint chore (no sprint number — rules maintenance; follows REFACTOR-009 execution same day)
**Scope**: Development Process / always-loaded rule hygiene + workflow optimization
**Status**: **DONE 2026-07-14** (user approved Layers 1+2+3)

> **Modification History**
> - 2026-07-14: Initial creation + execution — 3-layer process fix so the REFACTOR-005/-009 re-bloat cycle cannot recur

---

## Problem

REFACTOR-005 (2026-05-31) extracted the sprint-workflow.md matrix narration once; by 2026-07-14 it had re-bloated (36 → 56 rows > 400 chars) and REFACTOR-009 extracted it again. Root cause of the RECURRENCE (not just the bloat): the only guard was **advisory prose** — each sprint closeout copied the previous sprint's bloated matrix cell as its template (relative-anchor drift, same mechanism REFACTOR-008 fixed for sprint plans), and **nothing failed** when a cell bloated. A third recurrence was guaranteed without a mechanical guard.

Secondary problem: even a lean sprint-workflow.md (~103 KB post-REFACTOR-009) carried large phase-specific bodies (matrix table / Day-0 prong procedures / spike gate) that are used at ONE moment per sprint but loaded into EVERY session (~45k tokens).

## Solution (3 layers, user-approved 2026-07-14)

### Layer 1 — Mechanical enforcement (the piece -005/-009 lacked)

- **NEW `scripts/lint/check_rules_hygiene.py`** (12th lint in `run_all.py`; also CI `lint.yml` Lint 8):
  - Check A: every table row in `calibration-matrix.md` (lines starting `| \``) ≤ **400 chars**
  - Check B: byte budgets on always-loaded files (size @ 2026-07-14 + ~25-40% headroom):
    CLAUDE.md 45k · sprint-workflow.md 60k · file-header-convention 24k · multi-tenant-data 18k · anti-patterns-checklist 14k · rules/README 14k · calibration-matrix 60k
  - Missing budgeted file = violation (conscious SIZE_BUDGETS update required on rename/move)
- `Violation` is a `NamedTuple` (NOT `@dataclass` + future-annotations — Sprint 57.165 importlib lesson)
- Tests: `backend/tests/unit/scripts/lint/test_rules_hygiene.py` (5 cases incl. `test_real_repo_is_currently_clean` — the live repo must pass its own lint)

### Layer 2 — Write-flow inversion (closeout writes LESS, not more)

- Full narration is written ONCE (memory subfile + retrospective.md — already mandatory); the matrix gets ONLY a fill-in skeleton line (absolute anchor, not "copy the previous row"):
  `| \`<class>\` | <mult> | <mean> | KEEP/re-point (<sprint> ratio ~<Y> IN/OVER band; <one clause>; if 2nd >1.20 → <Z>; → calibration-log §1) |`
- Skeleton codified in the FROZEN `claudedocs/templates/sprint-checklist-template.md` §4.2 Closeout (+ navigator line re-pointed to calibration-matrix.md); `sprint-plan-template.md` §7 now cites calibration-matrix.md as the lookup source.
- Net effect: each closeout writes ~2,000 fewer chars while capturing identical information.

### Layer 3 — On-demand split (phase-specific bodies out of every session)

| Moved content | New location | Used only at |
|---------------|--------------|--------------|
| Scope-class multiplier matrix (86 rows) + Active Agent Delegation Factor Modifier | `docs/03-implementation/agent-harness-execution/calibration-matrix.md` (28.5 KB) | Step 1 plan §Workload + Day 4 closeout |
| Step 2.5 prong procedures (Prong 1/2/2.5/3 + drift-class grep tables) + ROI evidence + Examples | `docs/rules-on-demand/day0-plan-verify.md` (21.9 KB) | Day 0 |
| Step 5.5 8-Point Quality Gate + quality table + retro record format | `docs/rules-on-demand/spike-design-note-gate.md` (4.5 KB) | spike Day 4 closeout |

Each moved block replaced by a short trigger + Read-pointer stub in sprint-workflow.md. Kept always-loaded: the 5-step discipline, §Workload Calibration forms + adjustment rule, the 3-prong summary + drift-catalog/go-no-go DoD, Step 5.5 when-to-apply, Sprint Closeout policy, Risk Classes, Before-Commit checklist. Move is verbatim (headings promoted #### → ##; relative links fixed); zero content change.

Navigators updated: `.claude/rules/README.md` (on-demand 11 → 13 + calibration-matrix 查表指標 + 情境快查) + root `CLAUDE.md` §Code Standards (13 條 + matrix pointer).

## Result

| File | Before (2026-07-14 morning) | After REFACTOR-009 | After REFACTOR-011 |
|------|------------------------------|--------------------|--------------------|
| `.claude/rules/sprint-workflow.md` | 179,443 bytes (~79.6k tok) | 102,690 | **53,684 bytes (−70% total; ~24k tok)** |

Estimated per-session startup context saving vs. morning baseline: **~55k tokens**; memory-files share drops from 15.4% → ~10% of the 1M window. Cost: 1-3 on-demand Reads per SPRINT (not per session) at the exact phase that needs them — the §Workload form cannot be completed without the matrix lookup, so the Read cannot be silently skipped.

## Verification

- `python scripts/lint/check_rules_hygiene.py` → `rules-hygiene: OK (7 budgeted files + matrix rows <= 400 chars)`
- `pytest backend/tests/unit/scripts/lint/test_rules_hygiene.py` → 5/5 pass
- `python scripts/lint/run_all.py` → 12/12 green (see commit)
- Code-fence balance verified on all 4 touched/created md files; matrix 86 rows verbatim in calibration-matrix.md; 0 table rows left in sprint-workflow.md

## Impact / Reversibility

- Docs / rules / lint tooling only — no backend/frontend/runtime change. CI gains one <1s step.
- Zero information loss (verbatim moves; narration triple-preserved per REFACTOR-009).
- Fully reversible via `git revert`.

## References

- [REFACTOR-009](./REFACTOR-009-sprint-workflow-matrix-rebloat-extraction.md) — the same-day extraction this layer-set prevents from recurring
- [REFACTOR-005](./REFACTOR-005-sprint-workflow-calibration-extraction.md) — first extraction (advisory-only, regrew)
- [REFACTOR-008](./REFACTOR-008-sprint-plan-checklist-template-freeze.md) — frozen-template absolute-anchor precedent (Layer 2 applies it to matrix rows)
- `.claude/rules/README.md` §載入策略 — the Hybrid always/on-demand mechanism Layer 3 extends to sprint-workflow.md
