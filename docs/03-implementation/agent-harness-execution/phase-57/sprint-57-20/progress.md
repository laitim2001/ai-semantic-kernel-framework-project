# Sprint 57.20 Progress

**Sprint**: 57.20 — AD-Mockup-Direct-Port Foundation (Shell Rewrite + 2 Anchor Pages; Option W)
**Branch**: `feature/sprint-57-20-mockup-existing-pages-retrofit`
**Plan**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-20-plan.md`
**Checklist**: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-20-checklist.md`
**Aborted Predecessor**: `sprint-57-20-{plan,checklist}.aborted-option-Y-retrofit.md` (Option Y / per-page retrofit — superseded after Day 0 runtime capture revealed shell-level drift)

---

## Day 0 — 2026-05-17 — Setup + 三-prong + Playwright MCP pipeline

### Today's accomplishments

**Pivot decision documented**:
- Original Sprint 57.20 plan (Option Y / Tier 1 page retrofit) aborted after Day 0 runtime Playwright MCP capture revealed 5 shell-level drift dimensions that per-page patching cannot address
- User 2026-05-17 selected Option W (Frontend-Led, Backend-Follows direct-port philosophy)
- New plan + checklist drafted; old archived with `.aborted-option-Y-retrofit.md` suffix for audit trail

**Three-prong scope verify** (per `.claude/rules/sprint-workflow.md` §Step 2.5):

#### Prong 1 — Path verify
| Asset | Expected | Actual | Status |
|-------|----------|--------|--------|
| `frontend/src/components/AppShellV2.tsx` | exists | exists | ✅ |
| `frontend/src/components/Sidebar.tsx` | exists | exists | ✅ |
| `frontend/src/components/UserMenu.tsx` | exists | exists | ✅ |
| `frontend/src/components/layout/` | empty dir ready for NEW Topbar.tsx | empty dir present | ✅ |
| `frontend/src/components/topbar/` | CommandPalette + NotificationsPanel (Sprint 57.19 NEW) | confirmed both present | ✅ |
| `frontend/src/components/ui/` | shadcn primitives (Card / Button / Badge / Dialog / DropdownMenu / EmptyState / ErrorRetry / Skeleton / Tabs) | all 9 + index.ts present | ✅ |
| `frontend/src/pages/overview/index.tsx` | Sprint 57.19 US-C1 ship | exists | ✅ |
| `frontend/src/pages/chat-v2/index.tsx` | Sprint 57.8 ship | exists | ✅ |
| `reference/design-mockups/{shell,page-overview,page-chat,i18n,styles,tweaks-panel,topbar-overlays}.{jsx,css}` | mockup canonical sources | all present | ✅ |
| `frontend/public/fonts/` | font assets for Geist + Noto Sans TC | **MISSING** | ⚠️ D-PRE-5 |

#### Prong 2 — Content verify
| Plan claim | Grep verify | Result |
|-----------|-------------|--------|
| `tailwind.config.ts` declares Geist + Noto Sans TC fontFamily | grep `fontFamily` in config | ✅ confirmed (Sprint 57.18) |
| `index.css` `:root` currently light default | head -50 | ✅ confirmed — `--background: 0 0% 100%` (white); dark only in `.dark` class |
| `index.css` `--primary: 234 89% 60%` indigo from Sprint 57.19 US-A1 | grep `--primary` | ✅ confirmed |
| `features/chat-v2/` (hyphen) for chat module | ls | ❌ **D-PRE-1 (CRITICAL)** — actual is `features/chat_v2/` (underscore); pages dir uses hyphen `pages/chat-v2/` but features module uses underscore |
| `features/loops/types.ts` + `subagents/types.ts` + `state/types.ts` (Sprint 57.19 NEW) | ls | ✅ all 3 present with hooks/services/types.ts structure |
| `features/memory/` exists | ls | ✅ + has components/hooks/services/types.ts + README.md |
| `features/auth/` exists | ls | ✅ present |

#### Prong 3 — Schema verify
**N/A** — pure frontend sprint, 0 DB schema work, 0 backend changes.

### Drift findings catalogued

- **D-PRE-1 (CRITICAL — naming convention)**: `features/chat_v2/` uses underscore (Python module style) but `pages/chat-v2/` uses hyphen (URL route style). Sprint 57.20 plan + checklist mention `features/chat-v2/` (hyphen) in several places — must use `features/chat_v2/` (underscore) in Day 3 actual code. **Scope impact**: 0% shift; documentation correction only.
- **D-PRE-2 (info)**: `frontend/src/components/layout/` already exists as empty dir — NEW Topbar.tsx slot ready (no mkdir needed Day 1).
- **D-PRE-3 (info)**: `features/` has additional modules not mentioned in plan: `guardrails / orchestrator-loop / state-mgmt / subagent` (singular). Some appear to be legacy or pre-Sprint-57.19 names (e.g. `subagent` singular vs `subagents` plural NEW Sprint 57.19). **Scope impact**: 0% — Sprint 57.20 anchor pages use only `loops / memory / subagents / state / chat_v2`; legacy modules untouched.
- **D-PRE-4 (info)**: shadcn `ui/` has `tabs.tsx` (Sprint 57.19 NEW for Orchestrator 6 sub-tabs) + `dropdown-menu.tsx` (cmdk + UserMenu) — both available for Day 1 Topbar.tsx (locale dropdown) and Day 2 /overview (KPI tabs if mockup uses).
- **D-PRE-5 (BLOCKER for fidelity)**: `frontend/public/fonts/` directory does NOT exist. Geist + Noto Sans TC declared in `tailwind.config.ts` but **no font asset files bundled**. Day 1 US-B2 Geist wiring must either (a) add CDN `@import` in `index.css`, (b) install self-hosted font assets and reference via `@font-face`, or (c) accept system fallback for this sprint and open AD-Font-Asset-Bundling carryover. **Scope decision**: Option (a) CDN @import for Sprint 57.20 — faster + zero asset commits; if CDN unreliable in prod → AD upgrade to self-hosted Phase 58+.
- **D-PRE-6 (verified)**: `tailwind.config.ts` fontFamily Geist + Noto Sans TC declared correctly (Sprint 57.18). Day 1 US-B2 only needs `@layer base { body { font-family: theme('fontFamily.sans') } }` + `@import` line — no config change.
- **D-PRE-7 (verified — driver of shell rewrite)**: `index.css` `:root` is light default; dark theme only via `.dark` class on `<html>`. Mockup default = dark + `[data-variant]` mechanism. Day 1 US-B3 rewrite `index.css` for dark default in `:root` + `[data-variant]` + `[data-density]` selectors.
- **D-PRE-8 (verified)**: `index.css` already has Sprint 57.18 semantic tokens (`--success` / `--warning` / `--danger` / `--thinking` / `--tool` / `--memory` / `--info`) + risk tokens (`--risk-low` / `--risk-medium` / `--risk-high` / `--risk-critical`). Day 2 /overview + Day 3 /chat-v2 anchor pages can consume directly.
- **D-PRE-9 (port conflict — resolved as benign)**: Port 3007 LISTENING = PID 50796 (node.exe, started 5/17 01:35 AM). This IS the running Vite dev server. Per CLAUDE rule **do NOT kill node.js processes**. Vite HMR will pick up Sprint 57.20 source changes automatically → no need to spin up second dev server. ✅ Use existing 3007.
- **D-PRE-10 (verified)**: Port 8080 LISTENING = PID 44700 (python.exe, started 5/17 18:29). This is the mockup `python -m http.server 8080` running from `reference/design-mockups/`. Day 0 capture confirmed `GET /shell.jsx` returns 304. ✅
- **D-PRE-11 (verified)**: Port 8000 LISTENING = PID 41528 (python.exe, started 5/16). Likely backend uvicorn — irrelevant to Sprint 57.20 (0 backend changes).
- **D-PRE-12 (BLOCKER for capture)**: Initial Playwright MCP capture attempt with `..` prefix failed — playwright-mcp resolves `..` from `.playwright-mcp/` as project parent dir (not project root parent of `.playwright-mcp`). Resolution: use project-root-relative path `claudedocs/...` (no leading `..`). ✅ Pattern documented for Day 1-4 captures.

### Go/no-go decision

**Scope shift**: 0% (all 12 drift findings are documentation corrections, environment confirmations, or already-anticipated rewrite scope).

**Decision**: ✅ **GO** Day 1 — proceed with shell rewrite as planned. D-PRE-1 naming correction applies to Day 3 chat-v2 work; D-PRE-5 Geist asset gap resolved via CDN `@import` Option (a).

### Playwright MCP reference captures (US-A1 complete)

All 6 baseline captures at 1440×900 viewport saved to `claudedocs/4-changes/sprint-57-20-direct-port-foundation/screenshots/`:

| File | Size | Purpose |
|------|------|---------|
| `shell/mockup-shell-default.png` | 204 KB | Mockup default theme baseline for Day 1 shell rewrite reference |
| `shell/prod-shell-pre.png` | 102 KB | Production pre-Sprint-57.20 shell — Day 4 before/after comparison |
| `overview/mockup-overview.png` | 204 KB | Mockup `page-overview.jsx` rendered — Day 2 anchor page 1 target |
| `overview/prod-overview-pre.png` | 176 KB | Production `/overview` (Sprint 57.19 ship) — Day 4 comparison |
| `chat-v2/mockup-chat-v2.png` | 77 KB | Mockup `page-chat.jsx` rendered — Day 3 anchor page 2 target |
| `chat-v2/prod-chat-v2-pre.png` | 91 KB | Production `/chat-v2` (Sprint 57.8 ship, requires auth) — Day 4 comparison |

**Note on mockup-shell-default.png**: Mockup ships only one theme variant by default at `/` (no auto-switching dark/light toggle visible in console). Day 1 will use this single baseline; if 4 mockup variants (indigo / forest / violet / dawn per `tweaks-panel.jsx`) become Day 1+ work scope, additional baselines can be captured by JS-injecting `document.documentElement.dataset.variant = "forest"` etc. via `browser_evaluate`.

### Remaining for Day 1

- US-B1: AppShellV2 V3 + Topbar.tsx + Sidebar enrichment per mockup `shell.jsx` (~5-6 hr)
- US-B2: Geist + Noto Sans TC font wire via CDN `@import` + `@layer base { body }` (~1 hr)
- US-B3: `[data-variant]` + `[data-density]` mechanism + dark default in `:root` (~1 hr)
- Day 1 EOD: 14 active pages smoke test + Playwright capture POST-Day-1 shell

### Notes

- Anti-stop rule continued validation: 6 Bash + multiple Playwright tool calls executed without frequent stops — `memory/feedback_tool_result_is_not_turn_boundary.md` continues to apply correctly.
- Console errors observed on production overview (~156-162): backend cost endpoints 500 — known carryover, irrelevant to Sprint 57.20 (0 backend changes).
- Plan/checklist correction needed: replace `features/chat-v2` → `features/chat_v2` (underscore) in checklist Day 3 references. Will apply in Day 1 commit batch.
