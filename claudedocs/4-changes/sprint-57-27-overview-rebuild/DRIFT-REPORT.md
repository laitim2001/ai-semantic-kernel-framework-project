# Sprint 57.27 — `/overview` Mockup-Fidelity DRIFT-REPORT

**Sprint**: 57.27 — AD-Mockup-Fidelity-Rebuild-Overview
**Mockup ref**: `reference/design-mockups/page-overview.jsx:74-379` + `styles.css` (`.card` / `.stat` / `.badge` / `.page-head`)
**Production ref**: `frontend/src/pages/overview/OverviewPage.tsx` (728-line all-in-one close port — Sprint 57.19 commit `f8949504` + 57.20 `d6cc70bd`)
**Status**: 🟡 Day 0 skeleton — per-widget verdict + final verdict filled Day 1-3
**Viewport**: 1440×900 (mockup `:8080` vs production `:3007`)

---

## §1 — 16-Drift list (Day 0 agent exploration)

| ID | Drift | Class | Closed by | Day 0 note |
|----|-------|-------|-----------|------------|
| D1 | In-page page-head title — mockup `:76` `.page-title` present; prod delegates to AppShellV2 topbar | structural | US-B1 | D-PRE-8: AUDIT-REPORT Unit 7 wrongly said mockup has no title; mockup DOES (`:76`). Render in-page. |
| D2 | Mono `tenant · role · clock` meta line missing (mockup `:80`) | cosmetic | US-B1 | Rendered inside PageHead `subtitle` ReactNode (D-PRE-4) |
| D3 | KPI sparklines — mockup Cost MTD (`:93`) + SLA p95 (`:94`) pass `spark`; prod inline Stat has no spark | functional/cosmetic | US-B1 | StatCard `spark` prop confirmed present (D-PRE-5) |
| D4 | Active Loops row content — mockup agent+session+tenant+model; prod session-id only | structural | US-B2 | D-PRE-6: backend `Loop` type has no `agent_name`/`model` → layout closed, agent/model placeholder |
| D5 | `stat-spark` styling absent | cosmetic | US-B1 | Via shared StatCard |
| D6 | Card radius literal `rounded-[12px]` vs `--radius-lg` token | cosmetic | US-D2 | CardShell already `rounded-[12px]` = 12px (visually OK; token-purity only) |
| D7 | Card-head padding `px-4 py-3` vs mockup `11px 14px` | cosmetic | US-D2 | In shared CardShell (D-PRE-5) |
| D8 | Card-title `text-sm` 14px vs mockup `.card-title` 12.5px | cosmetic | US-D2 / R9 | **In shared CardShell** — R9 Day 1 decision (change shared vs carryover) |
| D9 | Stat padding | cosmetic | US-D2 | StatCard `px-4 py-3.5` = 16/14px ≈ mockup `.stat` `14px 16px` — OK (D-PRE-5) |
| D10 | Stat delta glyph `▲/▼` → SVG icon | cosmetic | US-B1 | Shared StatCard already uses `<ArrowUp/Down>` SVG — auto-closed |
| D11 | Badge pill → mockup `.badge` 4px radius | cosmetic | US-C2 | — |
| D12 | RiskBadge tone map — prod `medium→info`; mockup `risk-medium→--warning` | cosmetic | US-C2 | — |
| D13 | HITL critical bg tint approximation | cosmetic | US-B2 | — |
| D14 | Page-wrapper `gap` vs mockup per-row `marginBottom` | cosmetic | US-D2 | — |
| D15 | Active Loops `maxTurns` hardcoded 50 | functional | carryover | Backend gap — AD-Loop-Session-Enrich-Phase58 |
| D16 | CostBurnChart + ErrorTrendChart drop x-axis labels + budget-line label | structural | US-C1 | — |

## §2 — 9-Widget mockup-vs-production matrix (filled Day 1-3)

| # | Widget | Mockup ref | Day | Verdict | Note |
|---|--------|-----------|-----|---------|------|
| A | page-head | `:74-87` | 1 | ⬜ pending | — |
| B | KPI row 4-stat | `:90-95` | 1 | ⬜ pending | — |
| C | Active Loops card | `:99-141` | 1 | ⬜ pending | — |
| D | HITL Queue card | `:143-167` | 1 | ⬜ pending | — |
| E | Cost Burn chart | `:172-178, 273-329` | 2 | ⬜ pending | — |
| F | Providers card | `:180-199` | 2 | ⬜ pending | — |
| G | Recent Incidents card | `:204-225` | 2 | ⬜ pending | — |
| H | Error Trend chart | `:227-233, 331-379` | 2 | ⬜ pending | — |
| I | Quick Actions strip | `:236-266` | 2 | ⬜ pending | — |

## §3 — Final verdict (Day 3)

⬜ Pending — filled Day 3 closeout. Target: PARITY (D1-D14 + D16 closed; D15 carryover).

## §4 — Carryover

- **D15** — `maxTurns` hardcoded; backend gap → existing `AD-Loop-Session-Enrich-Phase58`
- **AD-Overview-Backend-Extensions-Phase58** (NEW; Day 3 → next-phase-candidates.md) — HITL Queue / Providers / Incidents / Error Trend / Cost Burn fixture-backed widgets need backend aggregation endpoints
- **R9 outcome** — if Day 1 chooses to defer the shared `CardShell` card-title fix → shared-primitive token-audit carryover
