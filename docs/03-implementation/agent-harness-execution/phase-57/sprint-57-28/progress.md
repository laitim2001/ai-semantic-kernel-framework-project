# Sprint 57.28 Progress — AD-Mockup-Fidelity-Foundation-Switch

**Class**: `frontend-verbatim-css-foundation` 0.55 (NEW; 1st application)
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-28-plan.md`
**Checklist**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-28-checklist.md`

---

## Day 0 — 2026-05-22 — Plan + Checklist + guidance-PR merge + 三-prong + before-baseline

### Today's Accomplishments

- **Plan + checklist drafted** (mirror Sprint 57.26 structure; 11 sections / Day 0-4) — user-approved 2026-05-22 incl. Option B scope decision (foundation-only; per-page re-point = Phase 2).
- **guidance PR #161 merged** — `chore/frontend-mockup-fidelity-guidance` (`19f31443`) → opened PR #161 → behind origin/main (PR #160 Sprint 57.27 merged in the interim) → merged `origin/main` into the branch (clean, 0 conflict — disjoint file sets) → all 8 CI checks green → squash-merged to main `d4461141`, remote branch deleted.
- **Feature branch cut** — `feature/sprint-57-28-mockup-fidelity-foundation` from updated main `d4461141`.
- **Day 0 三-prong** complete (Prong 1 path + Prong 2 content/collision-enumeration + Prong 4 test-selector) — see Drift findings below; 0 path drift, 6 D-PRE findings catalogued.
- **`route-sweep.mjs` re-pointed** — OUT_DIR `sprint-57-26-foundation-fidelity` → `sprint-57-28-mockup-fidelity-foundation` + header MHist (reused harness, minor tweak per plan).
- **Before-baseline sweep** — 22 routes captured 1440×900 → `claudedocs/4-changes/sprint-57-28-mockup-fidelity-foundation/screenshots/before/` (22 PNGs; all ✓).
- **FOUNDATION-SWITCH-REPORT skeleton** written — 4-layer summary + token-collision table (filled) + 22-route matrix skeleton + D-PRE catalogue.

### Drift findings (Day 0 三-prong — per sprint-workflow §Step 2.5)

| ID | Sev | Finding | Implication / cross-ref |
|----|-----|---------|-------------------------|
| D-PRE-1 | 🟠 | Mockup `styles.css` HAS a full light theme (`[data-theme="light"]` ×4 variants, L114-164). Plan US-C2 premise "mockup has no light design → dark-only" is WRONG (reports 02/03 imprecise). | Plan §Risks R3 updated. Revised US-C2: keep light; `ThemeProvider` toggles mockup `[data-theme]`. **Surfaced to user — confirm before Day 2.** Scope shift <20% (same US, corrected approach) → continue per Step 2.5. |
| D-PRE-2 | 🟠 | Mockup bg/fg/border/shadow/radius tokens are `[data-theme][data-variant]`-scoped, NOT `:root`. | Production `<html>` MUST carry `data-theme="dark" data-variant="linear"` for verbatim CSS to resolve. Day 1 sets static attrs on `index.html`; Day 2 wires toggle. |
| D-PRE-3 | 🟢 | Mockup `styles.css` uses 0 `rem` — fully px. | `html{font-size:13px}` hack KEPT through Phase 1 (plan R2 default confirmed). |
| D-PRE-4 | 🟢 | Token-collision set enumerated — ~28 collisions: 2 tricky (`--primary`/`--border` de-collide) + ~26 shared-intent/identical. | Day 2 Layer 4 resolution table ready — see FOUNDATION-SWITCH-REPORT §2. |
| D-PRE-5 | 🟢 | `--radius`/`--row-h`/`--pad`/`--gap` mockup values == production. | Retiring production's = 0 value change (safe). |
| D-PRE-6 | 🟢 | 4 Vitest files reference theme/token literals (`AuthShell`/`AppShellV2`/`UserMenu`/`adminTenantsRoleGate`). | Day 4 US-E1 adapt as needed (NOT delete). |

**Prong 1**: 0 path drift. `index.css`/`main.tsx`/`tailwind.config.ts`/`ThemeProvider.tsx` exist (edits); `styles-mockup.css` absent (create); `route-sweep.mjs` present (reuse); frontend CI = `.github/workflows/frontend-ci.yml`.
**PoC reference**: `investigation/mockup-fidelity-poc` confirmed — `main.tsx` imports `./styles-mockup.css` after `./index.css`.

### Decisions taken

- `html{font-size:13px}` → **KEEP** through Phase 1 (D-PRE-3 — mockup px-only; transition-safe for the 13 not-re-pointed pages).
- Theme → **revised** from "dark-only" to "keep light + `ThemeProvider` toggles `[data-theme]`" (D-PRE-1). Pending user confirmation before Day 2.

### Remaining for next day (Day 1 — Group B Layer 2 + Layer 3)

- US-B1 Layer 2: `cp styles.css → styles-mockup.css`; `main.tsx` import; `diff` byte-identical; add `data-theme="dark" data-variant="linear"` to `index.html` (D-PRE-2 prerequisite for spot-check).
- US-B2 Layer 3: `index.css` retire mockup-system HSL approximations; keep `html{font-size:13px}`; body block.

### Notes

- Workload Day 0 est ~0.6 hr (calibrated) — actual ~ on track (guidance PR merge + 三-prong + sweep).
- Day 0 commit: `<hash>` (recorded post-commit).
