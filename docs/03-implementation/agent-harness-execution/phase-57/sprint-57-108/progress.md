# Sprint 57.108 Progress — UX slice: chat-v2 HITL card real tool/reason + Inspector turn metadata wire

[Plan](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-108-plan.md) · [Checklist](../../../agent-harness-planning/phase-57-frontend-saas/sprint-57-108-checklist.md)

---

## Day 0 — 2026-06-12 — Plan-vs-Repo verify + branch

Branch `feature/sprint-57-108-chatv2-hitl-inspector-wire` created from `main` `a42ed717`.

### Drift findings (three-prong; plan §8 cross-ref)

| ID | Finding | Implication |
|----|---------|-------------|
| D1 | `tokensIn` is ALREADY wired — `llm_request` handler (chatStore.ts:421-431) overwrites `tokensIn` from `ev.data.tokens_in` each call; `turn_start` creates a NEW AgentTurn per TAO turn → one LLM call per turn | Only `tokensOut` is actually missing. FE token capture uses **overwrite** (mirror the llm_request idiom), NOT the plan §3.3 "accumulate" assumption; llm_response additive pair still shipped (input actuals overwrite the pre-call estimate + output fills the gap) |
| D2 | Span linkage is EXPLICIT — spans carry `span_type: "TURN"` (`span_name="agent_loop.turn"`, loop.py:2173-2179; wire fields span_name/span_id/parent_span_id/span_type @ event_wire_schema.py:197-202) | `span_started` handler matches `span_type === "TURN"` → set active AgentTurn.spanId; no first-span-of-turn heuristic needed |
| D3 | NO `turn_end` event exists (wire has loop_start/turn_start/loop_end only); `AgentTurn.durationMs` is initialized null and NEVER set | Fold-in per plan §3.3 "wire if trivially broken": TURN `span_ended.duration_ms` → `durationMs` (same handler as the spanId linkage) |
| D4 | `stopReason` per turn is set only at `loop_end` for the LAST agent turn (chatStore.ts:519-530) | Semantically correct (intermediate TAO turns have no stop reason); no action |
| D5 | `HITLTurn.tsx` needs ZERO edits — renders `turn.tool` (:197-199), `rationale` gated `!== "—"` (:206-211), `payload` gated (:212); fully store-driven. `ApprovalCard.tsx` (legacy) renders risk-only header — never rendered tool | FE fix collapses to chatStore.ts ONLY; plan §4 file #8 becomes no-op; `approvals` dict extension dropped (nothing renders tool from it — YAGNI), so `types.ts` ApprovalEntry unchanged too |
| D6 | Verification escalate site reason IS in scope (`reason` local @ loop.py:1787, yield @ :1833) | All 5 sites pass a real `reason`; no `""` fallback needed |
| D7 | `ApprovalRequested(` constructors: ONLY the 5 loop yield sites + 3 test sites (test_sse.py:164/:176, test_event_wire_schema_parity.py:82), all keyword-style | Defaulted new fields are constructor-safe; no resume-replay / observer re-construction exists |
| D8 | Subagent relay does NOT carry ApprovalRequested (grep 0 in `agent_harness/subagent/`) | No relay change; child approvals out of scope by existing design |

### Prong results

- **Prong 1 (paths)**: all EDIT targets Glob-1 (`HITLTurn.tsx` actual path = `components/turns/HITLTurn.tsx`, not `components/` — minor path drift vs recon, catalogued); NO new files. ✅
- **Prong 2 (content)**: anchors verified per D1-D8; serializer insertion points confirmed (`sse.py` llm_response :158-176 after `cached_input_tokens` :174; approval :241-251). ✅
- **Prong 2.5 (FE tree)**: HITLTurn / InspectorTurn structurally untouched this sprint (store-driven); HITLTurn header documents styles-mockup.css classes — no shadcn residue introduced. Clean. ✅
- **Prong 3 (schema)**: N/A — no DB / no migration. ✅

### Go/no-go

**GO** — drift findings SHRINK scope (HITLTurn no-edit; tokens.in already wired; explicit TURN span match; durationMs bonus fold-in). Shift ≪20%.
