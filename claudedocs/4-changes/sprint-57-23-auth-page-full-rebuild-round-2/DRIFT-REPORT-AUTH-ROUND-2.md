# DRIFT-REPORT — Sprint 57.23 Auth Page Full Rebuild Round 2

**Sprint**: 57.23
**AD**: AD-Auth-Page-Full-Rebuild-Round-2
**Status**: Day 0 — pending Day 1+ DRIFT entries per page

---

## Methodology

Per CLAUDE.md §Frontend Mockup-Fidelity Hard Constraint §Mockup-Fidelity DoD:

1. Playwright MCP screenshot mockup target (from `reference/design-mockups/` via `python -m http.server 8080`) at 1440×900 viewport
2. Playwright MCP screenshot production at same viewport
3. Side-by-side compare; drift severity = **PARITY** / **COSMETIC** / **STRUCTURAL** / **FUNCTIONAL**
4. Cosmetic → same commit iterate Tailwind classes to parity; Structural / Functional → fix in this sprint (cannot defer per hard constraint)
5. Parity verdict recorded below per page

---

## Page-by-Page Drift Verdicts

| Unit | Page | Mockup source | Day 0 pre-rebuild | Day 1-3 post-rebuild | Verdict |
|------|------|---------------|--------------------|----------------------|---------|
| 1 | `/auth/login` | `page-extras.jsx:27-57` | ⏭ Day 1 capture | ⏭ Day 1 capture | TBD |
| 2 | `/auth/callback` | `page-extras.jsx:59-107` | ⏭ Day 1 capture | ⏭ Day 2 capture | TBD |
| 3 | `/auth/register` (step 0) | `page-auth-extras.jsx:31-188` step 0 | ⏭ Day 1 capture (expect 404) | ⏭ Day 2 capture | TBD |
| 3 | `/auth/register` (step 1) | `page-auth-extras.jsx:89-117` | n/a | ⏭ Day 2 capture | TBD |
| 3 | `/auth/register` (step 2) | `page-auth-extras.jsx:119-145` | n/a | ⏭ Day 2 capture | TBD |
| 3 | `/auth/register` (step 3) | `page-auth-extras.jsx:147-172` | n/a | ⏭ Day 2 capture | TBD |
| 4 | `/auth/invite/:token` | `page-auth-extras.jsx:191-246` | ⏭ Day 1 capture (expect 404) | ⏭ Day 3 capture | TBD |
| 5 | `/auth/mfa` (TOTP) | `page-auth-extras.jsx:306-336` | ⏭ Day 1 capture (expect 404) | ⏭ Day 3 capture | TBD |
| 5 | `/auth/mfa` (WebAuthn) | `page-auth-extras.jsx:339-360` | n/a | ⏭ Day 3 capture | TBD |
| 6 | `/auth/expired` | `page-auth-extras.jsx:374-416` | ⏭ Day 1 capture (expect 404) | ⏭ Day 3 capture | TBD |
| +supp | `/auth/dev` | `page-extras.jsx:109-185` | ⏭ Day 1 capture (expect 404) | ⏭ Day 1 capture | TBD |
| +shell | AuthShell wrap | `page-extras.jsx:5-25` | ⏭ Day 1 capture (within login/callback) | ⏭ Day 1 capture | TBD |

---

## Severity Definitions (per Mockup-Fidelity Hard Constraint)

- **PARITY (≥95% match)**: visual baseline matches mockup at 1440×900; only ~5% pixel-level noise (font hinting / sub-pixel rendering). No further action.
- **COSMETIC**: Tailwind class drift (padding / radius / shadow / color shade) — same-commit iterate to parity.
- **STRUCTURAL**: layout / DOM tree / component shape mismatch — fix in this sprint same Day (cannot defer per hard constraint; e.g. flex vs grid / wrong column count / missing widget).
- **FUNCTIONAL**: behavioral / interaction model mismatch (wrong button count / different flow / missing tab) — fix in this sprint same Day.

---

## Acceptance Verdict for Sprint Closure

Sprint 57.23 = CLOSED only when **all 12 page-state DRIFT verdicts == PARITY or documented COSMETIC with future Sprint AD reference**. Any STRUCTURAL / FUNCTIONAL drift blocks closure.

---

## Day-by-Day Updates (filled as work progresses)

### Day 0 — 2026-05-18

- Methodology documented; verdicts TBD pending Day 1+ Playwright MCP captures.

### Day 1 — TBD

### Day 2 — TBD

### Day 3 — TBD

### Day 4 — TBD (final closure verdicts + DRIFT-REPORT signed off)

---
