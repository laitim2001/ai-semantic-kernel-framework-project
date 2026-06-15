# CHANGE-088: Skills slash-menu mockup + production re-point

**Date**: 2026-06-15
**Sprint**: 57.121
**Scope**: Frontend / chat_v2 (the `/`-slash skill picker) + `reference/design-mockups/` — pure FE, no backend
**Slice**: `AD-Skills-SlashMenu-Mockup` — the LAST Skills-epic item (the epic completes with this)

## Problem

Sprint 57.115 shipped the chat-v2 `/skill-name` slash picker (`SkillSlashMenu.tsx`) as a GREENFIELD component with inline token-styles + a header comment "No mockup reference exists for this element" + a file-level `eslint-disable no-restricted-syntax`. It was the ONE chat-v2 element with no entry in `reference/design-mockups/` (the canonical visual source of truth), violating the Mockup-Fidelity Hard Constraint (every FE page/element must follow `reference/design-mockups/`, `styles.css` copied byte-identical into `frontend/src/styles-mockup.css`).

## Solution

Two parts: author the mockup, then re-point production to it.

**1. Author the mockup** (`reference/design-mockups/`, user-approved via AskUserQuestion — CommandPalette-consistent):
- `styles.css`: `.skill-menu` (`position:absolute; bottom:100%`, `var(--bg-1)`/`--border-strong`/`--radius-lg`/`var(--shadow)`) + `-list` / `-group` / `-item` / `-item.active` (`var(--bg-hover)`) / `-name` / `-desc` / `-empty` / `-foot`; `.composer-inner` += `position: relative`. Token-only — NO hex/oklch literal. No emoji (the mockup 鐵律).
- `page-chat.jsx`: `SKILLS` (5 illustrative) + a `SkillMenu` component (`role=listbox`, group header + items + kbd footer) + an interactive `Composer` (controlled `text`, slash parse, ↑↓/↵/ESC) so the prototype demonstrates it.
- Verified live (`python -m http.server`): the menu opens on `/`, lists the skills + a kbd footer (↑↓ navigate / ↵ select / ESC close / N skills), filters on type (count updates singular/plural). CommandPalette-consistent (a subtle `var(--bg-hover)` active row, NOT the 57.115 bold `var(--primary)`).

**2. Re-point production**:
- `frontend/src/styles-mockup.css`: the IDENTICAL `.composer-inner { position: relative }` + `.skill-menu*` block copied (byte-identical → `diff` empty; `HEX_OKLCH_BASELINE` 51 unchanged, no literal).
- `SkillSlashMenu.tsx`: swapped the inline `menuStyle`/`rowStyle` for the mockup `className`s; ADDED the `Skills` group header + the `.skill-menu-foot` kbd footer; DROPPED the `eslint-disable no-restricted-syntax` + the `CSSProperties` import (no inline styles remain); KEPT the 57.115 `data-testid`s / `role`s / `aria-selected` + the `onMouseDown` select. The InputBar (filter / activeIndex / keyboard / force-load) is untouched.

The mockup's interactive Composer is prototype-only — production already owns the filter/keyboard (InputBar, 57.115).

## Files

| File | Change |
|------|--------|
| `reference/design-mockups/styles.css` | `.skill-menu*` + `.composer-inner{position:relative}` (token-only) |
| `reference/design-mockups/page-chat.jsx` | `SKILLS` + `SkillMenu` + interactive Composer (prototype) |
| `frontend/src/styles-mockup.css` | byte-identical copy of the above |
| `frontend/src/features/chat_v2/components/SkillSlashMenu.tsx` | inline-styles → mockup classes + group header + kbd footer + drop `eslint-disable` |
| `frontend/tests/unit/chat_v2/SkillSlashMenu.test.tsx` | +4 (group header / footer / empty-no-footer / active class) |

## Verification

- **Gates**: `diff reference/design-mockups/styles.css frontend/src/styles-mockup.css` empty (byte-identical) · `check:mockup-fidelity` 51 byte-identical · `npm run lint` clean (no unused-directive from the dropped disable; no residual inline style) · `npm run build` ✅ · Vitest **888 (142 files)** (+4) · backend `run_all` **10/10** (count 24). git diff: 0 `.py` → mypy `src` 0/371, pytest 2648+5skip, wire 24 UNCHANGED; `InputBar.tsx`/`loop.py`/`events.py`/`sse.py`/`event_wire_schema`/codegen/migration UNTOUCHED.
- **Drive-through** (real chat-v2 + real backend, acme-prod, PASS): type `/` → the menu renders with the new mockup styling (panel + `Skills` group header + the REAL bundled skills from `useChatSkills` — `/code-review` active / `/digest` / `/summarize` — + a subtle `var(--bg-hover)` active row + a `.kbd` footer ↑↓/↵/ESC/3 skills); `/dig` filters to only `/digest` (footer "1 skill"); click `/digest` (via the preserved `skill-slash-item-digest` testid) → `/digest ` filled + menu closed (force-load). Each control live (real skills, real render via the mockup classes). AP-4 clear. Screenshots: `docs/.../sprint-57-121/artifacts/` (1 production + 2 mockup-prototype).

## Impact

Frontend-only (chat-v2 slash menu + the mockup). The last chat-v2 mockup-fidelity gap is closed; the slash menu now has a `reference/design-mockups/` source + production consumes its classes (the inline-style escape-hatch is gone). Closes `AD-Skills-SlashMenu-Mockup` — **the Skills epic is COMPLETE** (57.113 lazy-load → 114 per-tenant overlay → 115 slash-command → 116 chip → 117 quota → 118 bundled scripts → 119 system visibility → 120 Inspector active_skill → 121 slash-menu mockup). No backend / DB / wire / API change.
