# REFACTOR-008: Freeze the sprint plan/checklist template + re-anchor the format 鐵律 (stop monotonic format drift)

**Date**: 2026-06-17
**Sprint**: surfaced during 57.131 (chat-v2 Inspector model row); a process/rules refactor, not a feature.
**Scope**: Development process / `.claude/rules/sprint-workflow.md` + `CLAUDE.md` §Sprint Execution Workflow + new `claudedocs/templates/sprint-{plan,checklist}-template.md`.

## Problem

The user observed that sprint plan/checklist formatting "一直在隨著新的 sprint 慢慢改變" (keeps slowly changing sprint by sprint). An audit confirmed real, monotonic format drift across the V2 sprint series (80+ sprints), even though any two ADJACENT sprints looked "consistent".

## Root Cause

The format 鐵律 (`.claude/rules/sprint-workflow.md` §Step 1/§Step 2 + `CLAUDE.md`) said: **"mirror the most-recent completed sprint's plan/checklist."** That is a **RELATIVE / floating anchor** — each sprint copies the previous one. Small per-sprint drifts therefore compound monotonically (a ratchet with no absolute reference). The 鐵律 enforced *adjacent-pair* consistency but permitted unbounded *cumulative* drift.

### Drift evidence (audited 2026-06-17)

| Dimension | **49.1** (Phase 49 freeform) | **51.2 / 52.1** (Phase 51-52 §0-9) | **57.107-130** (Phase 57 current) |
|-----------|------------------------------|-------------------------------------|-----------------------------------|
| H1 title | short (`V1 封存 + V2 目錄骨架 + CI`, ~25 chars) | short (`Plan：範疇 3 Memory 層…`) | **~600-char run-on** sentence embedded in the H1 |
| Language | 中文 section names | 中文 section names | **全英文** |
| §-numbering | ❌ none, freeform ~11 H2 | ✅ §0-9 | ✅ §0-9 |
| §0 meaning | `Sprint Goal` | `0. Sprint 目標（一句話）` | **`0. Background`** (dense prose; Goal moved to §1) |
| Metadata block | none | none | **`Status/Branch/Base/Slice/Scope decisions`** (new) |
| §5/§6/§7/§9 | — | CARRY / Day估時 / 結構決策 / 啟動條件 | **Acceptance / Deliverables / Workload Calibration / Out of Scope** |
| §0 density | moderate | low (one-liner) | **high (wall of prose)** |

The drift was NOT all regression — the 57.x era added genuinely valuable sections from real retrospective lessons (§6 Deliverables, §7 Workload Calibration since 53.7, the Status/Branch/Base metadata block, the Drive-through MANDATORY requirement since 2026-06-06). The actual *defects* were narrow: **(1)** the giant run-on H1 title, **(2)** §0 Background prose density.

## Solution

Re-anchor the 鐵律 from a relative anchor to an **absolute frozen template**, keeping the valuable 57.x sections and fixing only the 2 defects.

1. **New frozen templates** (the absolute anchor):
   - `claudedocs/templates/sprint-plan-template.md` — §0-9 structure + the metadata block, KEEPING §6 Deliverables / §7 Workload Calibration / Drive-through, but enforcing: **H1 = one short scope line** (full description → a new `**Summary**:` block), **§0 uses sub-headers + line breaks** (not a wall).
   - `claudedocs/templates/sprint-checklist-template.md` — Day 0-4, bold task + DoD + Verify, no time estimates, short header line.
2. **Rule re-anchor** (`.claude/rules/sprint-workflow.md` §Step 1 + §Step 2 "Reference Template"): "mirror the most-recent completed sprint" → "mirror the FROZEN `claudedocs/templates/sprint-{plan,checklist}-template.md`". + MHist + Last Modified.
3. **CLAUDE.md** §Sprint Execution Workflow Step 1/Step 2 「🔴 格式一致性鐵律」 blocks: same re-anchor + the short-H1 / Summary / §0-line-break rules.
4. **Normalized Sprint 57.131** plan + checklist to the new template (the first sprint mirroring the frozen template) — short H1 + `**Summary**` block.

## Verification

- `claudedocs/templates/sprint-plan-template.md` + `sprint-checklist-template.md` exist, with the drift-rationale blockquote + the 2 readability rules.
- `.claude/rules/sprint-workflow.md` §Step 1/§Step 2 reference the frozen template; MHist entry added; Last Modified 2026-06-17.
- `CLAUDE.md` both 鐵律 blocks reference the frozen template.
- `sprint-57-131-plan.md` H1 is one short line + a `**Summary**` block; `sprint-57-131-checklist.md` header is one short line.

## Impact

- Process/docs only — **zero code change**, zero gate impact.
- Future sprints mirror the frozen template (absolute) → the format-drift ratchet is stopped. Adjacent-pair AND cumulative consistency now both hold.
- Does NOT retroactively reformat 49.x-57.130 plans/checklists (historical record preserved; not misleading — they were correct under the then-current relative rule). Only the template + rule + the in-flight 57.131 were touched.
- If a future genuinely-better structure emerges, the correct move is to **edit the frozen template once** (a deliberate, audited change) — not to let it drift sprint-by-sprint.
