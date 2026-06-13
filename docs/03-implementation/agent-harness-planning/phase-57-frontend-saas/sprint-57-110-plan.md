# Sprint 57.110 Plan — B4: subagent child governance (the tenant-resolved Cat 9 engine into BOTH child loops — "child 不能成為 guardrail 旁路" 鐵律) + child guardrail visibility (`GuardrailTriggered` joins the relay subset) + spawn failure policies (FAIL_FAST / FAIL_SOFT / FAIL_PARTIAL, per-tenant governable) — child verifier deferred by design

**Status**: Draft (pending user approval)
**Branch**: `feature/sprint-57-110-subagent-child-governance`
**Base**: `main` HEAD `220ed587` (post-#284 merge)
**Slice**: B4 per the interleave decision (RBAC → C3 → B3 → UX → C2 ✅ → **B4**) — the LAST B-family slice before optional A3; closes harness-deepening proposal §2.5 B4 (design note 20 §5 deferred pair: `AD-Subagent-Child-Governance` + failure policies). Recursion depth>1 stays deferred per the proposal (YAGNI).
**Scope decisions**: (a) child Cat 9 = inherit the parent's tenant-policy-resolved engine INSTANCE (C3 per-tenant governance — escalate phrases / risky-action detector switches — flows into the child for FREE; no second policy surface). (b) ESCALATE-in-child downgrades to BLOCK automatically — the fail-closed invariant is ALREADY in loop.py (:673-680 input / :1310-1311 between-turns / :412 ctor docstring) → **`loop.py` UNTOUCHED**; a child cannot pause (no HITL wiring, parent blocks in `wait_for`), and escalate-propagation-to-parent-pause is its own future slice. (c) the proposal's "可選 verifier" (Cat 10 in the child) is DEFERRED → `AD-Subagent-Child-Verification` — it doubles judge cost per child with no demand; the 鐵律 is about Cat 9 bypass, which this slice closes. (d) failure policies ride `SubagentBudget.failure_policy` (defaulted `"fail_soft"` = today's behavior byte-identical) + a per-tenant `subagent_failure_policy` tri-state on `HarnessPolicy` (C3 pattern); FAIL_FAST escalates a child failure to a run-level FATAL tool error (no retry — a retry would re-spawn the child), FAIL_PARTIAL salvages the child's partial output into the result.

---

## 0. Background

Proposal §2.5 B4: "Child 必須受 Cat 9 治理（企業鐵律：child 不能成為 guardrail 旁路）：`ChildLoopFactory` 閉包注入 guardrail_engine（可選 verifier）——目前 lean child 是已知 deferred（design note 20）" + "Failure policies：FAIL_FAST / SOFT / PARTIAL（多 spawn 場景的失敗語義）" + "Recursion depth > 1 ... 等真實需求出現再做（YAGNI）". Design note 20 §5 records both as deferred (`AD-Subagent-Child-Governance` — "lean child this slice (no guardrail/verifier)"; failure policies — "`SubagentBudget` has no `failure_policy`"). The 57.96/57.103 relay deliberately excluded `GuardrailTriggered` from the child TAO subset — once the child CAN trigger guardrails, that exclusion becomes a transparency hole (Agent Team principle #6), so visibility ships in the same slice.

### Design decision (pure ctor injection — loop.py / wire / codegen / DB ALL untouched; thin FE label addition)

- **US-1 is two closure params**: the FORK factory (`handler.py:355-366`) and TEAMMATE factory (`:387-401`) construct the child `AgentLoopImpl` WITHOUT `guardrail_engine` — every `_run_turns` gate (input / between-turns / tool / output) hangs off ctor-injected components, so passing the parent's composed engine activates ALL gates in the child for free (AS_TOOL inherits FORK's path). The child gets NO `hitl_manager` / `hitl_deferred` / `checkpointer` → every ESCALATE falls through loop.py's existing fail-closed branch to BLOCK / GUARDRAIL_BLOCKED. This is the DESIRED child semantic, already implemented and documented in loop.py — zero loop change.
- **Inherit the COMPOSED engine, not a bare default**: the parent engine at `handler.py:528` is `build_default_guardrail_engine()` + the C3 policy-derived additions (keyword escalate guardrails from `harness_policy` phrases + the 57.106 `RiskyActionDetector`) — Day-0 pins the exact composition lines so the child factory closure captures the SAME instance (engines are stateless chains; parent awaits the child in `wait_for`, so checks are sequential — no concurrency concern until §2.5 detached teammate).
- **Intentional behavior change (record, 57.107 precedent)**: with the engine inherited, children of ALL tenants (policy or not) are now subject to the DEFAULT guardrails (Toxicity p10 / SensitiveInfo p20 / risky-action per its default) — that is the POINT of closing the bypass; documented + test-pinned, not silent.
- **US-3 failure policy shape**: `SubagentFailurePolicy` Literal (`"fail_fast" | "fail_soft" | "fail_partial"`) in `_contracts/subagent.py` + `SubagentBudget.failure_policy: str = "fail_soft"` (frozen dataclass, defaulted — budget already carries spawn-policy fields `max_concurrent` / `max_subagent_depth` and travels spawn→executor). Semantics at the consumption sites: **FAIL_SOFT** (default) = today byte-identical — `SubagentResult(success=False, error=...)` folded into the tool result, parent LLM continues; **FAIL_FAST** = the `task_spawn` handler raises a FATAL-classified error on a failed child (Cat 8 must NOT retry — a retry re-spawns the child; mirror the `RateLimitExceededError` FATAL precedent, Day-0 pins the classification path); **FAIL_PARTIAL** = the executor catch sites salvage the child's best-effort partial output (last assistant text seen by `_drive`) into `summary` + keep `error` — a timed-out child's work is not discarded. Per-tenant: `HarnessPolicy.subagent_failure_policy: str | None = None` (tri-state, None → default) resolved in `handler.py` and threaded into the default budget.
- **US-2 visibility**: `GuardrailTriggered` joins `_TAO_CHILD_EVENT_TYPES` (fork.py:77-92 — additive; rides the existing `subagent_child` wrapper, NO new wire type, count 24 unchanged, no codegen) + the FE child-row label case (`chatStore` inner routing + `InspectorTree.childTurnLabel`, mirror the 57.103 `message_injected` case).
- **Rejected**: a per-tenant child-governance kill switch (the 鐵律 says child governance is NOT a tenant choice — deliberately no `child_governance_enabled` field); building a second engine from the same policy (shared instance is simpler and Day-0 verifies statelessness); threading the verifier into the child (deferred, see Scope decision c); a spawn-time LLM-chosen failure policy arg (governance belongs to the tenant, not the model — the budget default is tenant-resolved); new wire fields on `SubagentCompleted` (failure policy is visible via the existing `error`/summary surfaces).

### Ground truth (Day-0 head-start — 1 Explore recon agent + direct greps, file:line anchors on `main` HEAD `220ed587`)

- **Child factories (lean child)**: FORK `handler.py:355-366` / TEAMMATE `:387-401` — ctor gets `chat_client/output_parser/tool_executor/tool_registry/system_prompt/tenant_id/tracer/max_turns/token_budget` (+`message_inbox` TEAMMATE); LACKS `guardrail_engine/verifier_registry/error_*/compactor/checkpointer/prompt_builder/hitl_*`. Type aliases `_contracts/subagent.py:106` (`ChildLoopFactory`) / `:114` (`TeammateChildLoopFactory`) — signatures UNCHANGED this sprint (closure captures the engine).
- **Parent engine**: `guardrail_engine = build_default_guardrail_engine()` (`handler.py:528`) → parent ctor `:656`; verifier `make_chat_verifier_registry(profile.cheap, judge_template)` `:606-607` (NOT given to the child this sprint). HarnessPolicy consumption `:427` + per-field fallbacks `:507-526`.
- **Fail-closed ESCALATE invariant (the US-1 enabler)**: loop.py `:673-680` (input — "ESCALATE WITHOUT the HITL wiring fall through to the soft block — fail closed"), `:1310-1311` (between-turns — "fails closed to GUARDRAIL_BLOCKED"), `:412` (ctor docstring — "When None, ESCALATE remains a soft-block (53.3 baseline)"), tool branch `:886` (`ESCALATE and self._hitl_manager is not None` — None falls to the block path), `_emit_deferred_pause` `:1151` + defensive None-checks `:760/:983/:1384`.
- **Failure semantics today**: `ForkExecutor.execute` catch sites fork.py:114-200 — `child_loop_factory_unavailable` (:134) / `timeout: {N}s` (:170, `asyncio.wait_for(budget.max_duration_s)`) / `child_loop_error: {type}: {msg}` (:179) / `empty_response` (:190) — ALL return `SubagentResult(success=False, error=...)`; grep `FAIL_FAST|FAIL_SOFT|PARTIAL` in backend/src = ZERO hits. `SubagentResult` fields `_contracts/subagent.py:71-82` (has `error: str | None` + `metadata: dict`); `SubagentBudget` `:61-68` (max_tokens 10_000 / max_duration_s 300 / max_concurrent 5 / max_subagent_depth 3 — NO failure_policy).
- **HarnessPolicy (C3)**: `platform_layer/governance/harness_policy.py:110-126` — 11 tri-state fields (escalate phrases ×3 / escalate_tools / verification ×3 / risky ×2 / handoff ×2); NO child/failure fields; resolver `resolve_tenant_harness_policy` `:200-232` (TTL-cached, fail-open).
- **Relay subset**: `_TAO_CHILD_EVENT_TYPES` fork.py:77-92 = TurnStarted / LLMResponded / ToolCallRequested / ToolCallExecuted / ToolCallFailed / MessageInjected — `GuardrailTriggered` deliberately EXCLUDED → child guardrail fires invisible in the Inspector Tree today.
- **Design note 20 §5** (lines 51-63): the deferred pair this sprint closes ("lean child this slice (no guardrail/verifier)"; "`SubagentBudget` has no `failure_policy`").
- **Dispatcher**: ONE child per `spawn()` call; `wait_for(subagent_id, timeout_s)`; multi-spawn = multiple tool calls (max_concurrent budget-checked). dispatcher.py:173-316.
- **Baselines (57.109 closeout)**: full pytest **2485** (2477+4skip non-e2e + 8 e2e) · wire count **24** · FE Vitest **836** / mockup-fidelity **51** (the recon's calibration-log "2283" is a stale anchor — re-verify at Day-0). 8 existing subagent test files (unit/agent_harness/subagent ×5 + integration ×2 + unit/api/v1/chat relay ×1).

### STALE / drift anchors to re-confirm in the formal Day-0 三-prong (§ checklist 0.1)

Exact engine COMPOSITION lines in handler.py (where C3 keyword guardrails + RiskyActionDetector are added after `:528` — the child must capture the COMPOSED instance, not a bare default) · engine statelessness (no per-run mutable state on the chain) · the OUTPUT gate's ESCALATE fallback when hitl absent (:1511 region — confirm BLOCK like input/between-turns) · child final-answer output-gate firing (`is_final_answer` semantics inside a child run) · what `SubagentResult` a GUARDRAIL_BLOCKED child run produces (which error string; does `_drive` see empty content → `empty_response`?) · where the default `SubagentBudget` is constructed for chat (tools.py `make_task_spawn_tool` arg schema vs dispatcher default — the threading point for the tenant-resolved failure policy) · whether `task_spawn`'s ToolSpec exposes budget args (LLM-controllable `max_duration_s` = the dt failure lever) · `TeammateExecutor` failure catch sites (mirror fork's?) · Cat 8 classification path for an error raised from a tool handler (how `RateLimitExceededError` reaches FATAL — mirror for `SubagentFailureEscalation`; MUST NOT retry) · `_drive` partial-content capture (does fork retain the last assistant text → FAIL_PARTIAL salvage feasibility) · inner-event serialization for `GuardrailTriggered` through the wrapper (sse serializer generic over LoopEvent? FE `inner` typing additive?) · `chatStore` childEvents routing + `InspectorTree.childTurnLabel` switch location (mirror 57.103 message_injected) · harness_policy PUT-side field validation shape (where to 422 an invalid `subagent_failure_policy` literal) · HANDOFF child = full session boot via HandoffService (full-grade governance already; confirm out-of-scope) · `make_chat_subagent_dispatcher` / `_category_factories` signatures (threading surface) · 17.md current `HarnessPolicy`/`SubagentBudget` contract rows · baselines (pytest 2485 / wire 24 / Vitest 836 / mockup 51).

## 1. Sprint Goal

The child agent loops (FORK + TEAMMATE; AS_TOOL inherits) run under the SAME tenant-resolved Cat 9 guardrail engine as the parent — closing the "child is a guardrail bypass" hole with zero loop.py change (ESCALATE-in-child fail-closes to BLOCK by the existing invariant); child guardrail fires become visible in the Inspector Tree (`GuardrailTriggered` joins the relay subset — no new wire type); spawn failure semantics become explicit and per-tenant governable (`fail_soft` default byte-identical / `fail_fast` run-fatal without child re-spawn / `fail_partial` salvages partial output) — proven by a real-UI drive-through (a tenant escalate phrase blocks a child input + the fire renders in the Tree + the parent continues honestly under soft, and fail_fast flips the same failure to run-fatal). Closes proposal §2.5 B4; design note 20 §5 deferred pair → RESOLVED (depth>1 + child verifier stay open).

## 2. User Stories

- **US-1**: 作為 platform，我希望 FORK + TEAMMATE child loop factories 注入 parent 的 tenant-policy-resolved guardrail engine（同一 COMPOSED instance——C3 escalate phrases / risky-action detector 自動治理 child），以便 child 的 input / between-turns / tool / output 四個 gate 全部激活；child 無 HITL 佈線 → 任何 ESCALATE 依 loop.py 既有 fail-closed 不變量降級 BLOCK（test-pinned），`loop.py` 零修改。
- **US-2**: 作為 reviewer，我希望 `GuardrailTriggered` 加入 child relay TAO subset（騎 `subagent_child` wrapper，無新 wire type）+ chat-v2 Inspector Tree child row 顯示 guardrail 觸發 label，以便 child 治理事件可審計可見（透明原則），wire count 24 不變、無 codegen diff。
- **US-3**: 作為 tenant admin，我希望 spawn 失敗語義成為顯式政策：`SubagentBudget.failure_policy`（default `"fail_soft"` = 今日行為 byte-identical）+ `HarnessPolicy.subagent_failure_policy` tri-state per-tenant override（C3 pattern；invalid 值 PUT 422）——`fail_fast` 把 child 失敗升級為 run-level FATAL tool error（Cat 8 不 retry、不重 spawn），`fail_partial` 把 child 的部分產出（最後 assistant 文本）搶救進 `summary` 並保留 `error`。
- **US-4**: 作為 reviewer，我希望 drive-through 證明：(A) tenant escalate phrase → task_spawn child 的 input gate BLOCK → Inspector Tree child row 顯示 guardrail_triggered → parent 在 default soft 下誠實繼續（summary 反映 child 失敗）；(B) 同一失敗在 tenant `subagent_failure_policy="fail_fast"` 下變 run-fatal（loop error 終止，無 child 重 spawn）——全程真 UI + 真後端 + 真 Azure + 零 dev-login。

## 3. Technical Specifications

### 3.0 Architecture (backend + thin FE label; wire count 24 UNCHANGED; no codegen / no DB / no migration / **loop.py UNTOUCHED**)

```
handler.py:            <composed engine already built for the parent (Day-0 pins lines)>
                       _make_child_loop / _make_teammate_child_loop: AgentLoopImpl(..., guardrail_engine=<composed engine>)
                       failure_policy = policy.subagent_failure_policy or "fail_soft" → threaded to the spawn budget default
_contracts/subagent.py: SubagentFailurePolicy Literal + SubagentBudget += failure_policy: str = "fail_soft"
fork.py:               _TAO_CHILD_EVENT_TYPES += GuardrailTriggered; execute() catch sites honor fail_partial (salvage last assistant text)
teammate.py:           mirror the failure-policy semantics at its catch sites (Day-0 pins shape)
tools.py:              task_spawn handler — fail_fast + success=False → raise SubagentFailureEscalation (FATAL-classified, no retry)
harness_policy.py:     HarnessPolicy += subagent_failure_policy: str | None (tri-state) + parse + PUT-side literal validation (422)
frontend:              chatStore inner routing case + InspectorTree.childTurnLabel "guardrail_triggered" (mirror 57.103 message_injected)
loop.py / wire schema / codegen / DB / verification / compaction: UNTOUCHED
```

### 3.1 Child Cat 9 governance injection (US-1)

Both factories pass `guardrail_engine=<the parent's composed engine instance>` (closure capture; factory type aliases unchanged). The child has NO `hitl_manager`/`hitl_deferred`/`checkpointer` → input ESCALATE falls to soft-block (:673-680), between-turns to GUARDRAIL_BLOCKED (:1310-1311), tool ESCALATE to the block path (:886 None-check), output per Day-0-confirmed fallback — all existing code. Tests: child-loop unit tests with a deny/escalate keyword guardrail prove (a) input-block before any child LLM call → `SubagentResult success=False`, (b) tool-gate block → LLM sees error ToolResult + child continues, (c) ESCALATE-in-child produces NO pause checkpoint + NO pending_approval (the fail-closed pin), (d) default-engine inheritance (Toxicity/SensitiveInfo active in child) — the intentional behavior change test. TEAMMATE: same injection alongside `message_inbox` (one test).

### 3.2 Child guardrail visibility (US-2)

`GuardrailTriggered` joins `_TAO_CHILD_EVENT_TYPES` (additive — high-signal governance event; the subset stays locked otherwise). FE: `chatStore` handles inner `guardrail_triggered` on the `subagent_child` route (childEvents append — likely generic already; Day-0 pins) + `InspectorTree.childTurnLabel` adds the case (label shape mirrors the parent's guardrail row vocabulary). Vitest: childTurnLabel case + store routing. NO wire/codegen change (inner rides the wrapper, serializer is generic over LoopEvent — Day-0 confirms).

### 3.3 Failure policies (US-3)

`SubagentFailurePolicy = Literal["fail_fast", "fail_soft", "fail_partial"]` + `SubagentBudget.failure_policy: str = "fail_soft"` (defaulted; frozen — all existing constructors stay valid). Consumption: (a) **fork/teammate executor catch sites** — `fail_partial` populates `summary` with the salvaged last-assistant-text (Day-0 confirms `_drive` retains it; if not, capture it — a fork.py-local change) + keeps `error` + `metadata["failure_policy"]`; `fail_soft`/`fail_fast` keep today's result shape; (b) **task_spawn handler (tools.py)** — when the result has `success=False` AND the budget's policy is `fail_fast` → raise `SubagentFailureEscalation` (new error type classified FATAL in the Cat 8 path — mirror `RateLimitExceededError`; the run terminates via the existing error machinery, NO retry/re-spawn — test-pinned). Tenant resolution: `HarnessPolicy.subagent_failure_policy` tri-state (None → `"fail_soft"`), parsed by the existing harness_policy reader, validated at the admin PUT (invalid literal → 422, mirror the C3 field-validation shape), threaded in handler.py to wherever the default budget is constructed (Day-0 pins the site). The LLM does NOT choose the policy (governance is the tenant's).

### 3.4 What is explicitly NOT done

Child verifier / Cat 10 in the child (→ `AD-Subagent-Child-Verification`); recursion depth>1 (proposal YAGNI); child escalate-PROPAGATION to a parent pause (child pauses → human decides → child resumes — own future slice, needs detached-child machinery §2.5); a per-tenant child-governance kill switch (鐵律 — deliberately not switchable); full-fidelity child event relay (locked TAO subset + this one addition); HANDOFF child sessions (full-grade loops via session boot — already governed); multi-child GATHER aggregation semantics (no gather API exists; FAIL_PARTIAL is per-child salvage, not cross-child aggregation); new wire fields or FE failure-policy UI surfaces beyond the Tree label.

### 3.5 Validation (US-1..US-4)

Unit (backend): child factory injects the engine (identity pin ×2 modes) · child input-block / tool-block / no-pause-no-checkpoint pins · default-guardrails-active-in-child pin · relay subset includes GuardrailTriggered (existing relay test extends) · budget field default + Literal · fail_partial salvage · fail_fast raise + FATAL classification (no retry) · harness_policy parse + tri-state + PUT 422. Integration: existing subagent suites green UNCHANGED (0 del); a chat-path integration test driving spawn→child-block→soft continuation. FE: Vitest childTurnLabel + store routing. Gates: mypy strict 0 · run_all 10/10 (count 24; no codegen diff) · full pytest 0 del · Vitest +N · mockup-fidelity 51 holds · `loop.py` diff EMPTY.

## 4. File Change List

| # | File | Action |
|---|------|--------|
| 1 | `backend/src/api/v1/chat/handler.py` | EDIT — both child factories +`guardrail_engine`; thread tenant failure policy to the budget default |
| 2 | `backend/src/agent_harness/_contracts/subagent.py` | EDIT — `SubagentFailurePolicy` Literal + `SubagentBudget.failure_policy` defaulted field |
| 3 | `backend/src/agent_harness/subagent/modes/fork.py` | EDIT — relay subset +GuardrailTriggered; fail_partial salvage at catch sites |
| 4 | `backend/src/agent_harness/subagent/modes/teammate.py` | EDIT — mirror failure-policy semantics (shape per Day-0) |
| 5 | `backend/src/agent_harness/subagent/tools.py` | EDIT — task_spawn fail_fast raise (`SubagentFailureEscalation` FATAL) |
| 6 | `backend/src/platform_layer/governance/harness_policy.py` | EDIT — +`subagent_failure_policy` tri-state + parse + PUT validation seam |
| 7 | `backend/src/agent_harness/subagent/dispatcher.py` / `_category_factories.py` | EDIT (if the budget-default / threading site lands there per Day-0) |
| 8 | `frontend/src/...chatStore.ts` + `InspectorTree.tsx` | EDIT — inner `guardrail_triggered` routing + childTurnLabel case |
| 9 | `docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md` | EDIT — HarnessPolicy + SubagentBudget contract rows |
| 10 | backend tests (subagent suites CONVERT/ADD + harness_policy + chat integration) + FE Vitest | CONVERT/ADD (0 deletions) |
| — | `loop.py` / wire schema / codegen artifacts / DB / migrations / verification / compaction | **UNTOUCHED** |

## 5. Acceptance Criteria

1. Both child factories inject the parent's composed tenant-resolved engine (identity test-pinned); child gates fire (input/tool/output covered); ESCALATE-in-child → BLOCK with NO pause artifact (pinned); default-engine guardrails active in children = recorded intentional behavior change; `loop.py` diff EMPTY.
2. A child `GuardrailTriggered` reaches the SSE stream inside `subagent_child` and renders as a labeled child row in the Inspector Tree; wire count 24 unchanged; no codegen diff.
3. `failure_policy` default `"fail_soft"` is byte-identical (all existing subagent tests green, 0 del); `fail_fast` terminates the run via a FATAL-classified error with NO child re-spawn (test-pinned); `fail_partial` salvages partial child output into `summary` while keeping `error`; tenant tri-state resolves via `harness_policy` (None → soft) and an invalid literal 422s at the admin PUT.
4. Gates: mypy strict 0 · run_all 10/10 · full pytest +N (0 del) vs 2485 baseline · Vitest +N vs 836 · mockup-fidelity 51 holds.
5. Real-LLM drive-through PASS (zero dev-login): leg A escalate-phrase → child input-block → Tree shows the child guardrail row → parent continues honestly (soft); leg B same failure under tenant `fail_fast` → run-fatal, no re-spawn. Closes proposal §2.5 B4; design note 20 §5 pair → RESOLVED.

## 6. Deliverables

- [ ] US-1 child engine injection (FORK + TEAMMATE) + fail-closed pins + intentional-change record
- [ ] US-2 GuardrailTriggered relay + FE Tree label + Vitest
- [ ] US-3 failure policies (contract field + executor/tool semantics + tenant tri-state + 422) + tests
- [ ] US-4 drive-through PASS (screenshots + observed-vs-intended + both legs)
- [ ] CHANGE-077 + closeout (retro Q1-Q7 + calibration + navigators + design note 20 §5 edit + 17.md + next-phase-candidates)

## 7. Workload Calibration

- Scope class **NEW `subagent-child-governance` 0.55** (1st data point) — Cat 11 composition over the proven 57.94/57.102 child-loop machinery (factories exist; injection is closure params) + a policy-field mirror (C3 shape) + a thin FE label; sibling of `subagent-teammate-multiturn-spike` 0.55 (57.102 — same reuse-heavy composition shape), lighter than `subagent-child-loop-spike` 0.60 (57.94 built the machinery; this slice rides it), heavier than pure-backend (failure semantics span 3 modules + cross-stack label + 2-leg dt).
- **Agent-delegated: no** — parent-direct (guardrail/error-path correctness-sensitive; total diff small); `agent_factor = 1.0`, 3-segment form.
- Bottom-up est ~10 hr (US-1 ~2 + US-2 ~1.5 + US-3 ~3 + dt ~1.5 + docs/closeout ~2) → class-calibrated commit ~5.5 hr (mult 0.55). Day 4 retro Q2 verifies.

## 8. Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| Child captures a BARE default engine instead of the C3-composed one (policy bypass persists) | Day-0 Prong-2 pins the exact composition lines after handler.py:528; the injection test asserts IDENTITY with the parent's engine |
| Engine carries per-run mutable state → shared instance leaks parent↔child | Day-0 reads the chain classes for state; if stateful, build a second engine from the same policy inputs (small fallback) |
| OUTPUT-gate ESCALATE fallback when hitl absent differs from input/between-turns (:1511 region unverified) | Day-0 traces it; if it can pause-attempt or bypass, scope US-1 tests to pin the actual fallback and (only if a bypass exists) add the downgrade at the GATE call site — still not a loop rewrite |
| `fail_fast` raise gets RETRIED by Cat 8 → child re-spawn (expensive + wrong) | mirror the `RateLimitExceededError` FATAL classification path exactly (Day-0 pins it); test asserts exactly ONE spawn |
| `_drive` does not retain partial assistant text → FAIL_PARTIAL has nothing to salvage | Day-0 reads `_drive`; if absent, capture last LLMResponded content in the existing event-forwarding loop (fork.py-local) |
| `GuardrailTriggered` inner breaks FE inner typing / store routing | additive case; rawEvents fallback already renders unknown inners; Day-0 pins the store's inner switch |
| Child output gate never fires (child's `is_final_answer` semantics) | acceptable — input + tool gates carry the dt; output covered by unit tests at whatever semantics Day-0 finds |
| dt leg B lever: forcing a child failure deterministically | the SAME escalate-phrase input-block from leg A IS a child failure (success=False) → flips to run-fatal under fail_fast; no separate lever needed |
| GUARDRAIL_BLOCKED child run's result shape unknown (`empty_response` vs error) | Day-0 pins; the soft-leg dt asserts the honest summary whatever the string is |
| Risk Class C — `resolve_tenant_harness_policy` TTL cache across test loops | existing 57.106 reset fixture covers; reuse |
| Risk Class E — stale backend masks the injection at dt | clean no-reload restart + `Win32_Process` orphan sweep + startup probe (57.97/57.109 routine) |
| Teammate failure-path shape differs from fork | Day-0 reads TeammateExecutor catch sites; mirror minimally (Karpathy §3 — no opportunistic refactor) |

## 9. Out of Scope (this sprint; → separate slices / ADs)

- Child verifier / Cat 10 in the child (`AD-Subagent-Child-Verification` — judge cost per child; benchmark/demand-gated).
- Child escalate-propagation to a parent HITL pause (child pauses → human → child resumes; needs detached-child machinery — pairs with proposal §2.5).
- Recursion depth>1 / child-of-child routing (proposal YAGNI).
- Multi-child gather/aggregation semantics (no gather API; per-child salvage only).
- Full-fidelity child event relay (locked subset + GuardrailTriggered only).
- HANDOFF child sessions (full-grade loops already; governance covered by their own handler build).
- A3 trace-aware critique (the only remaining optional slice per interleave).
