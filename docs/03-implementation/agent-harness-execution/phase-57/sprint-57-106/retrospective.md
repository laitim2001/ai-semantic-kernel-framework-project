# Sprint 57.106 Retrospective — C3 per-tenant harness policy + risky-action detector

**Date**: 2026-06-12
**Branch**: `feature/sprint-57-106-harness-policy` (base `main` `7e358a6a`)
**Commits**: `b8d169ca` (Day 0) + `2f880870` (Day 1 backend core) + `b7a91dc6` (Day 2 wiring+admin) + `1c5dcd8a` (Day 3.1 FE) + `a76c189d` (Day 3 drive-through+docs) + closeout

## Q1 — What shipped?

The chat handler's hardcoded Cat 9/10 governance knobs (escalate phrases ×3 chains, escalate-tool
list, verification mode/template/escalate-on-max) became tenant-governable via
`tenant.meta_data["harness_policy"]` (sparse JSONB + TTL resolver, C1 mirror) + a pricing-style
admin PUT/GET + a "Harness Policy" tab. A new Cat 9 `RiskyActionDetector` (9-pattern sandbox
deny-list + tenant extra patterns) ESCALATEs risky `python_sandbox` code into the existing HITL
flow, per-tenant switchable. Drive-through PASS with zero dev-login. Closes harness-deepening
proposal §3.4 C3. CHANGE-073 + design note 28.

## Q2 — Estimate accuracy (calibration)

- Plan §7: bottom-up ~18 hr → class-calibrated commit ~10.8 hr (`config-tiering-model-policy-spike`
  0.60, **2nd validation data point**); Agent-delegated: **partial** (backend parent-direct, FE
  tab agent-delegated-then-parent-re-verified → blended full-stack, no single `agent_factor`).
- Actual ≈ 11 hr (Day 0 ~1 / Day 1 backend ~3 / Day 2 wiring+admin ~3 / Day 3 FE-delegated+re-verify
  ~1.5 / drive-through ~1.5 / docs ~1) → **ratio ≈ 1.02 IN band** (0.7-1.2).
- 3-sprint window: C1 (57.104) ≈0.9-0.95 + C3 (57.106) ≈1.02 → 2 consecutive IN band → **KEEP 0.60**.
- The mirror-heavy backend (C1 byte-pattern) + agent-delegated FE both ran on-estimate; the
  detector (a genuinely new component) was the only non-mirror piece and stayed bounded by the
  conservative 9-pattern scope.

## Q3 — What went well?

- **C1 mirror paid off twice**: `model_policy.py` → `harness_policy.py` byte-pattern + the
  model-policy admin block → harness-policy block + ModelPolicyTab → HarnessPolicyTab. Most of the
  surface was a known-good shape; only the detector + the 9-field richer policy were net-new.
- **Day-0 three-prong**: D4 (read the flat `ToolCall` dataclass body) told the detector exactly how
  to access `content.name`/`content.arguments`; D10 (frozensets referenced in 2 unrelated comments)
  steered the surgical no-rename decision before code.
- **Drive-through controlled experiment**: the temporal A/B (same tenant, before/after policy)
  isolated the policy as the sole variable — a cleaner proof than two distinct tenants, and the
  risky-detector on/off contrast did the same for US-3. The PUT-invalidated cache made each toggle
  observable on the very next chat.
- **ESCALATE-not-BLOCK** held up: the risky detector routed into the EXISTING HITL pause with zero
  new event type (`check_event_schema_sync` count unchanged).

## Q4 — What to improve / lessons?

- **Purpose-line char budget**: 3 new files tripped E501 on the docstring `Purpose:` line (the MHist
  char-budget lesson applies to Purpose lines too) — trim on first draft next time.
- **Agent-delegated FE re-verify is mandatory and cheap**: the agent reported green; re-running all
  4 gates myself (lint/build/Vitest/mockup-fidelity) + grepping shadcn-residue/Chinese-copy took
  ~3 min and confirmed it — exactly the Before-Commit item 7 discipline. No surprises this time, but
  the habit is what catches the 57.69/57.73-class misses.
- **chat-v2 HITL card `tool: —`**: the drive-through surfaced that the card doesn't render the
  tool name for an `approval_requested` event — pre-existing FE wiring gap, logged as
  `AD-ChatV2-HITL-Card-Tool-Name`, not chased.

## Q5 — Carryover / next

- `AD-HITL-Policy-ReadSide-Potemkin-Phase58` (NEW) — `DBHITLPolicyStore.get_policy()` write-side
  works but is never consumed at tool execution (ToolGuardrail Stage 3 hardcodes
  `requires_approval`); risk-threshold redesign = own slice.
- `AD-ChatV2-HITL-Card-Tool-Name` (NEW) — chat-v2 card renders `tool: —`.
- `tenant_policies` dedicated table — evaluated, deferred (note 28 §5).
- **Next slice per interleave decision: B3** (HANDOFF finish — platform layer already done 57.68-70
  per the proposal; shrinks to finish + governance).

## Q6 — Discipline self-check

1. Server-Side First ✅ · 2. LLM Neutrality ✅ (detector imports no SDK; `check_llm_sdk_leak` green)
· 3. CC 不照搬 ✅ (bashSecurity → server-side ESCALATE equivalent, not ported) · 4. 17.md
single-source ✅ (N/A by precedent for the value object; detector rides existing ABC — note 28 §4)
· 5. 範疇歸屬 ✅ (platform_layer/governance + Cat 9 × api) · 6. anti-patterns ✅ (no Potemkin —
detector drive-through-proven both poles; ESCALATE-not-BLOCK; `check_cross_category_import` green)
· 7. workflow ✅ (plan → checklist → Day 0 → code → drive-through → closeout) · 8. file header ✅
(MHist 1-line) · 9. multi-tenant ✅ (tenant-scoped resolve + cross-tenant isolation test). Rolling:
no future plans pre-written ✅; no unchecked items deleted ✅.

## Q7 — Design Note Extract (spike sprint — required per §Step 5.5)

**File**: `docs/03-implementation/agent-harness-planning/28-per-tenant-harness-policy-design.md`
**Verified ratio (estimated)**: ≥ 95% (every claim has file:line or a drive-through screenshot /
pytest command; the only speculative content is the §5 deferred-table graduation trigger).
**8-Point Quality Gate**: all 8 ✅ (self-review in note 28 §8 — section header / file:line /
decision matrix D1-D7 / verification commands / test fixtures / open-invariant separation /
rollback path / 17.md cross-ref).
**Reviewer pass**: self-review (solo-dev).
