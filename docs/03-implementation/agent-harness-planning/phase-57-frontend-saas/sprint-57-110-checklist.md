# Sprint 57.110 — Checklist (B4: subagent child governance — tenant-resolved Cat 9 engine into BOTH child loops + `GuardrailTriggered` relay visibility + spawn failure policies FAIL_FAST/SOFT/PARTIAL per-tenant — child verifier deferred)

[Plan](./sprint-57-110-plan.md)

---

## Day 0 — Plan-vs-Repo Verify + Branch

### 0.1 Three-prong Day-0 verify (against `main` HEAD `220ed587`) — DONE, catalogued in progress.md D1-D13
- [x] **Prong 1 — path verify**: EDIT files Glob-1 (`handler.py` / `_contracts/subagent.py` / `subagent/modes/fork.py` / `subagent/modes/teammate.py` / `subagent/tools.py` / `subagent/dispatcher.py` / `platform_layer/governance/harness_policy.py` / FE `chatStore.ts` + `InspectorTree.tsx` exact paths / `17-cross-category-interfaces.md` / design note `20-subagent-child-loop-design.md`); test suites pinned (8 subagent files + harness_policy tests + InspectorTree Vitest); **test-file basename pre-check** (Glob every NEW test basename across the whole test tree — 57.109 D-DAY1-2 collision lesson); NO new src files expected EXCEPT possibly the `SubagentFailureEscalation` error type location
- [x] **Prong 2 — content verify** (D1 engine composition HITL-conditional / D4 output-ESCALATE child no-op / D5 hardcoded budget + no LLM budget args / D6 FATAL mirror / D7 `_register_all.py` threading / D8 partial-salvage feasible + `empty_response` honest-label fix / D9 teammate mirror / D11 FE pins zero-codegen / D12 threading order / D13 PUT seam) (the plan §0 STALE anchors, ALL of): exact engine COMPOSITION lines in handler.py after `:528` (C3 keyword guardrails + RiskyActionDetector additions — the child must capture the COMPOSED instance) · engine chain statelessness · OUTPUT-gate ESCALATE fallback when hitl absent (:1511 region) · child `is_final_answer` output-gate firing semantics · GUARDRAIL_BLOCKED child run → which `SubagentResult.error` string · default `SubagentBudget` construction site for chat (tools.py vs dispatcher — the failure-policy threading point) · `task_spawn` ToolSpec budget args (LLM-controllable `max_duration_s`?) · `TeammateExecutor` catch sites shape · Cat 8 FATAL classification path for tool-handler raises (`RateLimitExceededError` precedent — pin the mirror for `SubagentFailureEscalation`; MUST NOT retry) · `_drive` partial-content retention (FAIL_PARTIAL salvage feasibility) · sse serializer generic over inner LoopEvent (GuardrailTriggered rides the wrapper?) · `chatStore` inner routing + `childTurnLabel` switch location (57.103 message_injected mirror) · harness_policy PUT-side field validation shape (422 seam) · HANDOFF child = full session boot (out-of-scope confirm) · 17.md current HarnessPolicy/SubagentBudget rows · baselines re-verify (pytest 2485 / wire 24 / Vitest 836 / mockup-fidelity 51)
- [x] **Prong 3 — schema verify**: N/A (no DB / no migration — harness_policy is meta_data JSONB, 57.106 infrastructure) — recorded explicitly
- [x] **Catalog drift** findings in progress.md Day 0 (D1-D13 + implications; plan §8 cross-ref)
- [x] **Go/no-go**: GO — D5/D7 file-list adjustment <10%; D4 narrows output semantics (test-pinned, dt unaffected); D8 adds in-scope honest-label fix

### 0.2 Branch
- [x] `git checkout -b feature/sprint-57-110-subagent-child-governance` (from `main` `220ed587`)

---

## Day 1 — Backend: child engine injection (US-1) ✅

### 1.1 Engine injection (US-1)
- [x] **`handler.py`**: `_make_child_loop` + `_make_teammate_child_loop` pass `guardrail_engine=<composed engine>` (late-bound closure capture; factory aliases unchanged); MHist 1-line (+ explicit `DefaultSubagentDispatcher | None` annotation — the closure capture defers mypy re-analysis, D-DAY1-1)
- [x] **Injection identity tests ×2**: capture-and-delegate on `make_chat_subagent_dispatcher` → FORK + TEAMMATE child engines ARE the parent's composed instance (1 test, both modes)
- [x] **Fail-closed pins**: child input-block → `success=False` + truthful `error="child_guardrail_blocked"` (fork+teammate `_drive` stop_reason capture — D8 honest-label fix) · tool-gate ESCALATE → soft-blocked + child continues to final answer · ESCALATE-in-child → NO ApprovalRequested + `GuardrailTriggered(action="escalate")` event keeps the truth while the RUN blocks (D-DAY1-2 pin) · engine-threading identity on the helper factory
  - DoD: subagent + handler suites **93 passed (+5 new, 0 del)** ✓; `loop.py` diff EMPTY ✓; mypy strict 0/359 ✓; flake8 0 ✓

---

## Day 2 — Backend: relay visibility + failure policies (US-2 + US-3) ✅

### 2.1 GuardrailTriggered relay + FE label (US-2)
- [x] **`fork.py`**: `_TAO_CHILD_EVENT_TYPES` += `GuardrailTriggered` (additive; subset otherwise locked); MHist 1-line
- [x] **FE**: `chatStore` projection (+`inner.reason`→text + `action` field; the reducer was already generic per D11) + `InspectorTree.childTurnLabel` `guardrail_triggered` case + `ChildTurnEvent.action?` (types.ts); Vitest +1 (store projection — mergeEvent suite 55 passed)
  - DoD: relay unit test extends (`test_forwards_child_guardrail_triggered` — tagged + forwarded) ✓; wire count 24 unchanged + no codegen diff (run_all 10/10) ✓; Vitest green ✓; FE lint + build ✓

### 2.2 Failure policies (US-3)
- [x] **`_contracts/subagent.py`**: `SubagentFailurePolicy` Literal + `SUBAGENT_FAILURE_POLICIES` frozenset + `SubagentBudget.failure_policy: SubagentFailurePolicy = "fail_soft"` (frozen, defaulted); exports; MHist 1-line
- [x] **`fork.py` / `teammate.py`**: timeout/exception catch sites honor `fail_partial` (`_salvaged_summary()` — the nonlocal survives wait_for cancellation; `metadata["failure_policy"]`); `fail_soft` byte-identical
- [x] **`tools.py`**: task_spawn handler — `fail_fast` + `success=False` → raise `SubagentFailureEscalation` (`_contracts/errors.py` NEW type; `DefaultErrorPolicy._register_defaults` FATAL — the RateLimitExceededError mirror; NO retry / NO re-spawn)
- [x] **`harness_policy.py`**: `subagent_failure_policy` joins `_STR_FIELDS` (from_dict/to_dict/is_empty ride free) + `tenants.py` PUT/GET field + `_FAILURE_POLICIES` literal 422 + persisted dict; threading: `handler.py` cast→`make_default_executor(subagent_failure_policy=)`→`make_task_spawn_tool(failure_policy=)`→`SubagentBudget` (D7 `_register_all.py` site)
- [x] **Tests ADD ×13 (backend)**: budget field ×1 · fail_fast raise + soft default + fast-success ×3 · fail_partial salvage + soft-empty ×2 (slow-tool timeout lever) · FATAL classification ×1 · harness_policy round-trip + tri-state ×2 · admin PUT 422 + persists ×2 · relay forward ×1 · (the spawn→child-block→soft chain is covered at the Cat 11 seam — fork input-block + tools fail_soft tests; chat-path covered live by the dt)
  - DoD: subagent 90 + harness_policy + admin 23 + handler suites green (0 del); run_all 10/10; mypy 0/359; 17.md SubagentBudget row updated + SubagentFailurePolicy NEW row ✓
- 🚧 **AS_TOOL fail_fast** deferred → `AD-Subagent-AsTool-FailFast` (D-DAY2-1: `as_tool_factory` is a `SubagentDispatcher` ABC method — a signature change is NOT surgical; salvage already inherits via ForkExecutor; AS_TOOL failures stay soft-returned to the LLM)

---

## Day 3 — Full gates + drive-through (US-4) + CHANGE-077 ✅

### 3.1 Full gate sweep
- [x] mypy strict 0/359 · black/isort/flake8 0 (all four) · run_all 10/10 from repo root (count 24; no codegen diff) · full pytest **2502+4skip (+17, 0 del)** vs 2485 baseline (+2 more Day-3: loop-level fail_fast pin + popen regression → final +19) · Vitest **837** (+1) · mockup-fidelity **51** holds · `loop.py` diff EMPTY (`git diff main...HEAD` = 0 lines) · wire schema diff empty

### 3.2 Drive-through (US-4 — real UI :3007 + fresh no-reload backend + real Azure gpt-5.2; zero dev-login founder@dt57105.test; Risk Class E clean restart, sole-owner verified, stale 57.109-knob backend killed) ✅ ALL LEGS PASS
- [x] **Leg A (soft default + visibility — risky-action lever, stronger than the planned phrase lever)**: spawn child task = sandbox `os.system('whoami')` → child rewrote to `subprocess` → **inherited C3 RiskyActionDetector ESCALATE → fail-closed tool BLOCK in the child** → `subagent_child guardrail_triggered (tool/escalate)` relay frame + Inspector Tree child row **"guardrail escalate · risky_action: sandbox code matched '\bsubproces…'"** → parent continued honestly. 🔴 **D-DAY3-1**: the child then REWROTE to `os.popen` — NOT in the C3 deny-list → whoami actually ran → fix-forward +`os.popen`/`os.spawn*`/`os.exec*` patterns (+regression tests) → **Leg A-bis re-drive: popen now blocked; the child honestly gave up ("I can't run os.popen… in the sandbox"); whoami did NOT run**
- [x] **Leg B (fail_fast)**: admin PUT `subagent_failure_policy="fail_fast"` + sentinel phrase (200; invalid literal **422 live**) → split-word prompt → parent wrote task `"zzqx sentinel"` → child INPUT gate ESCALATE (relay frame: `input/escalate/"input matched escalation phrase: 'zzqx sentinel'"`) → child failed (done · **0 tok**) → task_spawn handler RAISED (tool result never materialized) → **run terminated** (no answer turn; no conversation_completed audit). D-DAY3-2: the graceful terminal is `LoopTerminated` — a server-side-only event (NOT on the wire; pre-existing 57.58 shape) → unit pin `test_fail_fast_child_failure_terminates_parent_run` (LoopTerminated + exactly ONE spawn + no turn 2; requires production Cat 8 wiring error_terminator+tenant_id)
- [x] **Non-regression probe**: Leg A IS a normal spawn completing (fork done 5,745 tok + 57.102-shape Tree + verification 0.98) — covered
- [x] Screenshots ×2 (`dt57110-legA-tree-guardrail-row.png` / `dt57110-legAbis-popen-blocked.png`) in `artifacts/` (never-commit) + observed-vs-intended table in progress.md
  - DoD: ALL legs PASS ✓; policy flipped back (PUT {} → 200; GET all-None verified) ✓

### 3.3 CHANGE-077
- [x] `claudedocs/4-changes/feature-changes/CHANGE-077-subagent-child-governance-failure-policies.md` (1-page; spike design note NOT required — design note 20 continuation, §5.5 NOT-apply; note 20 §5 deferred pair → RESOLVED edit instead)

---

## Day 4 — Closeout

### 4.1 Closeout
- [ ] retrospective.md Q1-Q7 + calibration (NEW `subagent-child-governance` 0.55 1st data point; agent-delegated: no) + progress.md final
- [ ] Design note 20 §5 edit: `AD-Subagent-Child-Governance` + failure-policies rows → RESOLVED (depth>1 + child verifier stay open); MHist 1-line
- [ ] Navigators: CLAUDE.md Current-Sprint row + Last-Updated; MEMORY.md quality pointer + memory subfile; next-phase-candidates (closes proposal §2.5 B4; B-family 4/4 done; remaining slice = optional A3); sprint-workflow matrix NEW row
- [ ] PR (push + open on user authorization)
