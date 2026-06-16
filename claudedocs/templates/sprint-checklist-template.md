# Sprint XX.Y — Checklist (<short scope phrase — one line, NOT a paragraph>)

> **FROZEN canonical sprint-checklist template** (REFACTOR-008, 2026-06-17). The ABSOLUTE anchor
> every new sprint checklist mirrors — NOT the most-recent sprint's checklist. See
> `claudedocs/templates/sprint-plan-template.md` for the drift-audit rationale.
>
> **Rules**: (1) header line is SHORT — the full description lives in the plan's **Summary**, never
> duplicated here. (2) Day 0-4 structure (5 days). (3) Each task: bold deliverable + DoD + Verify
> command. (4) NO time estimates (`(Estimated X hr)` / `(Y min)` banned since Sprint 55.3 — per-day
> actuals go in progress.md; sprint-aggregate calibration in plan §7). (5) Only `[ ]`→`[x]`; NEVER
> delete an unchecked item (mark `🚧 阻塞: <reason>` instead). Scope differences via CONTENT (more
> checkboxes inside a Day), never STRUCTURE (don't add Day 5). Delete this blockquote when copying.

[Plan](./sprint-XX-Y-plan.md)

---

## Day 0 — Plan-vs-Repo Verify (三-prong) + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `<sha>`)
- [ ] **Prong 1 — path verify**: all edit targets exist (NEW files free; EDIT files present); `CHANGE-NNN` free
- [ ] **Prong 2 — content verify** (drift → progress.md):
  - [ ] **D-<name>** — <grep / read to verify a plan claim against real code>
- [ ] **Prong 3 — schema verify**: <grep new DB tables / migrations / ORM columns — or N/A if no DB>
- [ ] **D-baselines** — pytest <N> · wire <N> · Vitest <N> · mockup <N> · mypy <N> · run_all <N>/<N>
- [ ] **Catalog drift** — progress.md Day-0 table
- [ ] **Go/no-go** — <scope-shift % → proceed / revise / abort>

### 0.2 Branch
- [ ] `git checkout -b feature/sprint-XX-Y-<scope>` (from `main` `<sha>`)

---

## Day 1 — <theme> (US-…)

### 1.1 <task>
- [ ] **<deliverable>**
  - DoD: <measurable definition of done>
  - Verify: `<command>`

### 1.x <partial gate>
- [ ] <lint / build / mypy as relevant to today's work>

---

## Day 2 — <theme> (US-…)

### 2.1 <task>
- [ ] **<deliverable>**
  - DoD / Verify

### 2.x Full gate
- [ ] mypy `src` <N> · run_all <N>/<N> · backend pytest <N> · Vitest <N> + new · `npm run lint && npm run build` clean · mockup <N> (`diff` empty) · black/isort/flake8 clean · LLM-SDK-leak clean

---

## Day 3 — Drive-through (US-…) — real UI + real backend + real LLM
_(MANDATORY for any user-facing surface; for pure-backend/infra sprints replace with the relevant integration verification + state "gate-only verified" explicitly — never imply usability.)_

### 3.1 Clean restart (Risk Class E)
- [ ] <kill stale --reload / orphan spawn-workers; confirm fresh sole port owner + startup log; OR FE-only → rebuild Vite, backend untouched>

### 3.2 Drive-through (MANDATORY — NOT gate-only)
- [ ] <trigger the feature's primary path with real LLM>
- [ ] **THE fix (real UI)**: <per-control AP-4 walk — clickable / has effect / label real / result renders>
- [ ] Screenshot + observed-vs-intended → progress.md Day 3

---

## Day 4 — CHANGE-NNN + closeout

### 4.1 CHANGE-NNN
- [ ] **`CHANGE-NNN-<slug>.md`** (gap + fix + drive-through PASS + AD closed) [+ design note if spike — 8-point gate]

### 4.2 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (`<class>` <mult>, <Nth data point>; flag if ratio out of band → re-point)
- [ ] Final gate sweep: mypy · run_all · pytest · Vitest · mockup · build · lint · LLM-SDK-leak
- [ ] Navigators: CLAUDE.md Current-Sprint + Last-Updated · MEMORY.md pointer + subfile · next-phase-candidates (CLOSE the AD) · sprint-workflow matrix (`<class>` row / data point)
- [ ] Anti-pattern self-check (retro Q5): AP-2/3/4/6/8/11 → violations; v2 lints <N>/<N>
- [ ] **Commit** → ⏳ PR push + open → CI → merge: PENDING USER CONFIRMATION (push is outward-facing per Developer Preferences) → post-merge status flip after gh-verified MERGED
