# Sprint 57.131 Retrospective — chat-v2 Inspector Turn tab `model` row

**Closed**: 2026-06-17 · **Branch**: `feature/sprint-57-131-chatv2-inspector-model-row` (from `main` `eef15c5e`)
**Slice**: closes the `model` row leg of `AD-ChatV2-Inspector-Turn-Metadata-Wire` (57.120 carryover).

## Q1 — What was delivered?

A per-turn `model` KV row in the chat-v2 Inspector "Turn" tab, surfacing the LLM model that ran each turn (alongside `trace_id` / `tokens` / `cost`). Pure-frontend: `AgentTurn += model: string | null`; capture `ev.data.model` onto the active turn in the EXISTING `llm_request` `mergeEvent` case (init `model: null` at `turn_start`); one new `<KV k="model" …/>` row reusing the `KV` helper. NO backend / wire / codegen / migration; NO new CSS / mockup authoring. Drive-through PASS (real Azure → `model = gpt-5.2`, matching the ChatHeader badge). CHANGE-098; no design note (FE surfacing fix). +3 Vitest tests (908→911).

## Q2 — Estimate accuracy / calibration

- Scope class **`chatv2-inspector-existing-field-surface` 0.85** — the **2nd data point** (57.120 was the 1st, re-pointed 0.55→0.85 at ratio ~1.6).
- Bottom-up ~3.3 hr → class-calibrated commit ~2.8 hr (mult 0.85, parent-direct agent_factor 1.0).
- **Feature-only actual** ≈ ~2.3-2.6 hr (Day-0 ~20 min · code 3 src + 4 test edits ~40 min · tests ~30 min · drive-through ~15 min trivial · closeout ~40 min). **Ratio ≈ 0.82-0.93 — IN band.** → **KEEP 0.85** (the 57.120 rule "if a 2nd lands < 0.7, lower toward 0.65" is NOT triggered). The ceremony floor held: ~6-8 lines of real code but the full ceremony (plan/checklist/Day-0/drive-through/CHANGE/retro/navigators) dominated, exactly as the 0.85 anticipates.
- **Calibration note**: the format-drift meta-work (REFACTOR-008) was a SEPARATE concern interleaved on user request, NOT part of the 57.131 bottom-up — excluded from the ratio (it has no calibration class; it was a one-off process refactor).
- 2-data-point trend for the class: 57.120 (the re-point landing) + 57.131 (~0.85 in band) → 0.85 looks well-calibrated; a 3rd data point would validate.

## Q3 — What went well?

- **Day-0 三-prong caught the required-field tsc ripple** (D-agentturn-literal-sites): grep `role: "agent"` enumerated 4 AgentTurn literals upfront, surfacing 2 test factories the plan missed → `model: null` added in the same Day-1 pass; `npm run build` confirmed zero missed literals. No mid-sprint surprise. This is the §8 risk being caught exactly as designed.
- **Trivial drive-through** — unlike 57.130's fatal-terminate hunt, a normal message produces an `llm_request` with a model. `browser_evaluate` read the Inspector KV rows precisely (`model = gpt-5.2`) + confirmed badge-consistency (gpt-5.2 ×3 in body) without a giant snapshot.
- **Clean recipe reuse** — mirroring the 57.120 `active_skill` row meant the design was settled before coding (capture-at-`llm_request`-not-`turn_start` was the only real decision).

## Q4 — What to improve?

- The plan's File Change List under-counted by 2 test factories (caught Day-0, low cost). The frozen template's §4 should keep reminding that a REQUIRED type-field change ripples to every literal — but Day-0 Prong-2 D-agentturn-literal-sites already covers it; no rule change needed.
- The format-drift detour (REFACTOR-008) consumed real wall-clock mid-sprint. It was the right call (the user surfaced a genuine systemic issue), but it's a reminder that a small feature sprint can absorb a large adjacent process fix — kept cleanly separate (own REFACTOR record, own logical commit) per scope discipline.

## Q5 — Anti-pattern self-check (04-anti-patterns)

- AP-2 (side-track): ✅ on the 主流量 (chat-v2 Inspector, reached from `/chat-v2`).
- AP-3 (scattering): ✅ all chat_v2 frontend.
- AP-4 (Potemkin): ✅ REMOVES a missing-metadata gap — the model row is REAL live data (gpt-5.2 from the turn's `llm_request`), drive-through-proven, not a hardcoded label.
- AP-6 (premature abstraction): ✅ reused the `KV` helper; no new abstraction.
- AP-8 (no PromptBuilder): N/A (no LLM call).
- AP-11 (version suffix): ✅ none.
- v2 lints: backend UNCHANGED (zero backend diff) → 10/10 holds; FE lint clean.

## Q6 — Carryover

- **`AD-ChatV2-Inspector-Turn-Metadata-Wire` token-sweep leg** (🟢) — actual `input_tokens` vs the `tokens_in` estimate + `cached_input_tokens` + `cache_hit_rate` per turn. Still open.
- **`AD-ChatV2-Inspector-Cost-InStream`** (cost-in-stream carve-out) — cost stays an honest "—" by design (post-loop). Only carve if a real consumer demands it (YAGNI).
- Other bucket-C carryovers (separate slices): `AD-ChatV2-Resume-Tool-RoundTrips` (57.129), Inspector turn metadata token-sweep, transcript retention. (`AD-ChatV2-HITL-Card-Tool-Name` was confirmed already-closed by 57.108 during this sprint's slice-selection — stale carryover; remove from the pool.)
- Pre-existing: `AD-Billing-Outbox-Drain-Test-Flake` (Risk Class C; did NOT surface — FE-only sprint).

## Q7 — Design note

N/A — FE surfacing fix (surfaces an already-captured field in a new render location), NOT a spike. No design note per the spike-only rule.

---

### Process note (REFACTOR-008, interleaved this sprint)

On user observation that sprint plan/checklist formatting had been drifting (49.1 freeform → 51.2/52.1 §0-9 中文 → 57.107-130 英文 giant-H1 + dense §0), audited the drift, root-caused it to the format 鐵律's RELATIVE anchor ("mirror the most-recent sprint" → monotonic ratchet), and fixed it: froze `claudedocs/templates/sprint-{plan,checklist}-template.md` (absolute anchor, keeping the valuable 57.x sections, fixing the H1 + §0-density defects) + re-anchored the 鐵律 in `.claude/rules/sprint-workflow.md` + `CLAUDE.md`. 57.131 is the first sprint mirroring the frozen template. See REFACTOR-008.
