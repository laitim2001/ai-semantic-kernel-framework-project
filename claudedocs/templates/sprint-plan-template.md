# Sprint XX.Y Plan — <short scope phrase, ≤ ~12 words, NO embedded summary>

> **FROZEN canonical sprint-plan template** (REFACTOR-008, 2026-06-17). This file is the
> ABSOLUTE anchor every new sprint plan mirrors — NOT the most-recent sprint's plan.
>
> **Why frozen** (drift audit, REFACTOR-008): the prior rule "mirror the most-recent completed
> sprint's plan" used a RELATIVE / floating anchor — each sprint copied the previous one, so
> small per-sprint drifts compounded monotonically. Audit across 80+ sprints:
> 49.1 (freeform 中文, no §-numbering) → 51.2 / 52.1 (clean §0-9 中文) → 57.107-130
> (英文, ~600-char run-on H1, dense §0 prose). Any adjacent pair looked "consistent"; the
> cumulative drift was large. A frozen template is an absolute anchor that stops the ratchet.
>
> **The 2 readability rules this template enforces** (the defects the 57.x era drifted into):
> 1. **H1 is ONE short line** — a scope phrase, not a paragraph. The full description goes in
>    **Summary** below. (The 57.107-130 H1 was a ~600-char run-on sentence — banned.)
> 2. **§0 Background uses sub-headers + line breaks**, not a wall of prose.
>
> **Mirror this file's STRUCTURE** (§0-9 + the metadata block). Express sprint scope differences
> through **CONTENT** (more stories / files / risks), **never through STRUCTURE** (don't add/rename
> sections, don't change the Day count). Delete this blockquote when you copy the template.

**Summary**: <2-5 sentences. What this sprint delivers · the gap / AD it closes · the key scope decision · whether a drive-through is MANDATORY (any user-facing surface) · whether a design note is required (spike sprint only). This block replaces the giant run-on H1 of the 57.107-130 era.>

**Status**: <Approved-to-execute / Draft> (<who approved + when + the decision trail, e.g. AskUserQuestion pick>)
**Branch**: `feature/sprint-XX-Y-<scope>`
**Base**: `main` HEAD `<sha>` (<what that commit was>)
**Slice**: <which AD this closes / arc position (standalone or arc slice N/M)>
**Scope decisions**: <(a) … (b) … (c) … — the key design choices as a tight lettered list>

---

## 0. Background

### The gap (<the AD / carryover being closed>)

<2-4 sentences or short bullets: what's broken / missing today. Line-broken, not a wall.>

### Why it matters (the missing capability)

<2-4 sentences: the user/operator impact of the gap.>

### Root cause (recon code read, file:line; ALL re-verified §checklist 0.1)

| Layer | Reality (on `main` HEAD `<sha>`) | Anchor |
|-------|----------------------------------|--------|
| <what> | <reality> | `file:line` |

→ <1-2 sentences: what the fix must do, derived from the table.>

### The design (<one-line shape, e.g. "FE-only: 1 type field + 1 store capture + 1 KV row + tests">)

```
# pseudo-code / file-level sketch of the change
```

<Optional: 1 short paragraph on WHY this design over the alternative.>

### Ground truth (recon head-start — code read on `main` HEAD `<sha>`; ALL re-verified §checklist 0.1)

- `file:line` — <fact the plan relies on>

**Baselines (<prior sprint> closeout)**: pytest <N> · wire <N> · Vitest <N> · mockup <N> · mypy <N> · run_all <N>/<N>. Re-verify Day-0.

### STALE / drift findings (Day-0; full detail → progress.md — placeholder, filled in §checklist 0.1)

- **D-<name>** — <what to grep / verify> → <implication / which §Risks row it shifts>

## 1. Sprint Goal

<One paragraph: the measurable goal + how it is PROVEN (gates + the MANDATORY drive-through if user-facing). State the CHANGE-NNN + whether a design note is produced.>

## 2. User Stories

- **US-1** (<theme>): 作為 <role>，我希望 <capability>，以便 <benefit>。
- **US-2** (<theme>): …
- … (typically the last US = drive-through MANDATORY for user-facing; the final US = closeout.)

## 3. Technical Specifications

### 3.0 Architecture (<file-change shape; NO backend/CSS/migration etc. as applicable>)

```
# FILE LIST grouped by EDIT / NEW / REGEN / UNTOUCHED, with one-line purpose each
```

### 3.1 <area> (US-N) — `<file>`

<bullets: the precise change + the anchor it mirrors.>

### 3.x What is explicitly NOT done

<the tempting-but-out-of-scope items, so the reviewer knows they were considered.>

### 3.y Validation (US-1..US-N)

Gates: mypy `src` <N> · run_all <N>/<N> · pytest <N> · Vitest <N> · mockup <N> (`diff` empty) · `npm run lint && npm run build` (NO `--silent`) · black/isort/flake8 clean · LLM-SDK-leak clean. Plus the §3.x drive-through (MANDATORY if user-facing).

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `<path>` | NEW / EDIT / REGEN |
| — | `<path you might expect to change but don't>` | **UNTOUCHED** |

## 5. Acceptance Criteria

1. <measurable, testable criterion>
N. **Drive-through PASS (MANDATORY, real UI + backend + LLM)** — <observable outcome>; screenshot + observed-vs-intended in progress.md. (NOT gate-only.) [omit only for pure-backend/infra with no user-driven surface]
N+1. <AD> CLOSED; CHANGE-NNN; calibration recorded; navigators + next-phase-candidates updated.

## 6. Deliverables

- [ ] US-1 <deliverable>
- [ ] … (one per US)

## 7. Workload Calibration

- Scope class **`<class>` <mult>** (<rationale; cite `.claude/rules/sprint-workflow.md` §Scope-class multiplier matrix; note if NEW class / Nth data point>).
- **Agent-delegated: <yes / no / partial / TBD-Day-1-decision>** (<rationale>). `agent_factor` <value> → <3-segment / 4-segment> form.
- Bottom-up est ~X hr (<per-task breakdown>) → class-calibrated commit ~Y hr (mult Z) [→ agent-adjusted ~Y' hr (agent_factor)]. Day-4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| <risk> | <mitigation; cite §Common Risk Classes A-E if applicable> |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- <out-of-scope item> — <where it goes instead>
