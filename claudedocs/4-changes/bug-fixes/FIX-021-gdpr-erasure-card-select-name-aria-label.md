# FIX-021: GdprErasureCard `<select>` aria-label (Sprint 57.42 PR #191 a11y CI fail)

**Date**: 2026-05-25
**Sprint**: 57.42 (post-PR-CI fix)
**Scope**: Frontend / memory / GdprErasureCard component
**PR**: #191

## Problem

Sprint 57.42 PR #191 Frontend E2E (chromium headless) failed on `a11y-scan.spec.ts:123` — `Sprint 57.13 US-B6 — accessibility scan: gated pages have 0 critical/serious a11y violations`. Specifically `/memory` page reported **1 critical violation** with rule `select-name`:

```
/memory: critical/serious violations: [
  {"id": "select-name", "nodes": [...]}
]
```

Sub-checks all failed: `implicit-label` / `explicit-label` / `aria-label` / `aria-labelledby` / `non-empty-title` / `presentational-role`.

## Root Cause

`GdprErasureCard.tsx:51` `<select className="select" defaultValue="gdpr">` rendered the GDPR Reason dropdown but had **no accessible name**. The wrapping `<Field label="Reason (audited)">` provides a visual label `<div>` but NOT a `<label htmlFor="">` element with proper `for`/`id` association — axe couldn't detect implicit label.

Same potential issue on `<input className="input mono">` (L48) for Subject id, though axe only flagged the select. Pre-emptively fixed both for defense.

## Solution

Added `aria-label` to both form controls in `frontend/src/features/memory/components/GdprErasureCard.tsx:48,51`:

```tsx
<input className="input mono" placeholder="u_…" aria-label="Subject id" />
<select className="select" defaultValue="gdpr" aria-label="Reason (audited)">
```

Single-file 2-line change. Mirrors Sprint 57.41 Vitest accessibility convention (text/role/aria queries) + Sprint 57.40 form-field a11y pattern.

## Verification

- `npx tsc --noEmit` → 0 errors (TSC_EXIT=0)
- `npm test -- --reporter=dot` → 486/486 passing (unchanged from pre-fix; aria-label is additive)
- Expected on next CI run: `select-name` violation count 1 → 0 on `/memory`; entire `gated pages` a11y test passes

## Impact

Frontend-only. No backend / no schema change. Test suite unchanged. Improves a11y baseline of `/memory` from 1 critical violation to 0; aligns with Sprint 57.13 US-B6 accessibility scan gate.

## Cross-references

- `frontend/tests/e2e/a11y/a11y-scan.spec.ts:123` — gated pages a11y scan that detected this
- Sprint 57.42 plan §3 + retrospective.md Q4 — was NOT logged as Day 0 Prong 2.5 finding (a11y scan only runs in CI, not Day 0 local checks); candidate for Phase 58+ AD-Day0-Prong-A11y-Local-Smoke
