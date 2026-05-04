# Sprint 54.1 — Cat 10 Verification Loops — Checklist

**Plan**: [sprint-54-1-plan.md](sprint-54-1-plan.md)
**Branch**: `feature/sprint-54-1-cat10-verification`
**Day count**: 5 (Day 0-4) | **Bottom-up est**: ~18-19 hr | **Calibrated commit**: ~10-11 hr (multiplier 0.55 per AD-Sprint-Plan-1; 2nd application after 53.7 ratio 1.01 validation)

> **格式遵守**：每 Day 同 53.7 結構（progress.md update + sanity + commit + verify CI）。每 task 3-6 sub-bullets（case / DoD / Verify command）。Per AD-Lint-2 (53.7) — 不寫 per-day calibrated hour targets；只寫 sprint-aggregate calibration verify in retro。

---

## Day 0 — Setup + Day-0 探勘 + Pre-flight Verify

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean**
  - DoD: `git status --short` empty (untracked plan dir is the new sprint files only)
  - Verify: `git branch --show-current` → main
- [ ] **Create branch + push plan/checklist**
  - Branch: `feature/sprint-54-1-cat10-verification` (tracks origin)
  - 2 files (plan + checklist) committed in single Day 0.1 commit

### 0.2 Day-0 探勘 — Per AD-Plan-1 (53.7 lesson)：grep §Technical Spec assertions against repo state
- [ ] **Verify 49.1 stubs exist + signatures match plan §Background § 既有結構**
  - `Read backend/src/agent_harness/verification/_abc.py` → confirms Verifier ABC `verify(*, output, state, trace_context)` async
  - `Read backend/src/agent_harness/_contracts/verification.py` → confirms VerificationResult 7 fields (passed / verifier_name / verifier_type Literal / score / reason / suggested_correction / metadata)
  - `Read backend/src/agent_harness/_contracts/events.py` → grep `VerificationPassed` + `VerificationFailed` confirm event classes exist
  - DoD: 3 stubs identified; field signatures match plan US-1/US-3 expectations
- [ ] **Grep AgentLoop integration point + SSE serializer scope (per `feedback_sse_serializer_scope_check.md`)**
  - `Grep VerificationPassed|VerificationFailed backend/src/agent_harness/orchestrator_loop/sse.py` → expect 0 matches (US-3 will add 2 isinstance branches)
  - `Grep "yield LoopCompleted" backend/src/agent_harness/orchestrator_loop/loop.py` → identify line for verification hook insertion
  - DoD: insertion points identified;預期 SSE serializer 0 matches now，Day 3 完成後 ≥ 2 matches
- [ ] **Grep Cat 9 SANITIZE / REROLL existing tests for AD-Cat9-2/3 closure assertion upgrade (US-4)**
  - `Grep "GuardrailAction.SANITIZE" backend/tests/` 列出所有 occurrence
  - `Grep "GuardrailAction.REROLL" backend/tests/` 列出所有 occurrence
  - Identify 1-2 specific tests to upgrade in US-4
  - DoD: 具體 test file path + line 已列；若 0 occurrence 則 US-4 closure 純新建測試
- [ ] **Verify ChatClient ABC stable for LLMJudgeVerifier (US-2)**
  - `Read backend/src/adapters/_base/chat_client.py` → confirm `chat()` method async signature accepts messages + tools
  - `Read backend/src/adapters/_testing/mock_clients.py` (if exists) → confirm test fixture pattern
  - DoD: LLMJudgeVerifier 可透過 mock ChatClient 測試
- [ ] **Verify `VerifierRegistry` 命名與既有 Cat 9 `GuardrailEngine` 模式對齐 (避免命名衝突 / 概念混淆)**
  - `Read backend/src/agent_harness/guardrails/_abc.py + engine.py` (snippets) 確認 GuardrailEngine pattern (register / evaluate)
  - DoD: VerifierRegistry pattern 命名與 GuardrailEngine 對齐；無命名衝突
- [ ] **Grep `safety_review` / `pii_leak_check` template names 已存在嗎**
  - `Grep -r "safety_review.txt\|pii_leak_check.txt" backend/` → expect 0 matches (US-2 全新建)
  - DoD: 不重複 既有 file;US-2 新建路徑乾淨

### 0.3 Calibration multiplier pre-read（meta；本 sprint 是第二次應用 0.55）
- [ ] **Read 53.7 retrospective Q2** — 確認 53.7 ratio 1.01 證據
  - DoD: 53.7 retro Q2 confirms multiplier 0.55 mid-band; 本 sprint 是第二次驗證；若 54.1 ratio 也在 [0.85, 1.20] 則 stable phase
- [ ] **Compute 54.1 bottom-up estimate**
  - Bottom-up per US: US-1 ~3.5 hr / US-2 ~4 hr / US-3 ~3.5 hr / US-4 ~2.5 hr / US-5 ~2 hr / Day 0 ~1.5 hr / Day 4 closeout ~1.5 hr = ~18.5 hr
  - Calibrated: 18.5 × 0.55 = **~10.2 hr → commit 10-11 hr**
  - DoD: 與 plan §Workload 對齐

### 0.4 Pre-flight verify（main green baseline）
- [ ] **pytest collect baseline** — expect 1262 collected = 1258 passed + 4 skipped (matches main HEAD `7bf25e02`)
  - Verify: `cd backend && python -m pytest --collect-only -q | tail -3`
- [ ] **6 V2 lint manual run via `run_all.py`** — expect 6/6 green
  - Verify: `python scripts/lint/run_all.py` exit 0
  - DoD: pre-existing baseline green

### 0.5 Day 0 progress.md
- [ ] **Create `progress.md` at execution path**
  - Path: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-1-cat10-verification/progress.md`
  - Day 0 sections: Setup / Day-0 探勘 findings / SSE serializer pre-state / calibration / pre-flight / drift findings (if any) / next
- [ ] **Commit + push Day 0**
  - Commit message: `chore(plan, sprint-54-1): plan + checklist + Day 0 探勘 + progress`

---

## Day 1 — US-1 RulesBasedVerifier + VerifierRegistry Foundation

### 1.1 New `agent_harness/verification/types.py` — Rule ABC + 3 concrete types
- [ ] **Define Rule ABC + RegexRule + SchemaRule + FormatRule**
  - `Rule(ABC).check(output: str) -> tuple[bool, str | None, str | None]`（returns `(passed, reason, suggested_correction)`）
  - `RegexRule(pattern: str, expected_match: bool = True)` 用 `re.compile`
  - `SchemaRule(schema: dict)` 用 `jsonschema` lib（已在 requirements.txt？若無加入）
  - `FormatRule(check_fn: Callable[[str], tuple[bool, str | None]])` 自訂 callable
  - File header per file-header-convention
  - DoD: 4 classes defined; mypy --strict 0 errors

### 1.2 New `agent_harness/verification/rules_based.py`
- [ ] **Implement RulesBasedVerifier**
  - `__init__(rules: list[Rule], name: str = "rules_based")`
  - `verify()` async 依序跑 rules → 任一失敗即返回 `VerificationResult(passed=False)`
  - 全 pass → 返回 `VerificationResult(passed=True)`
  - File header per file-header-convention
  - DoD: 對齐 Verifier ABC + plan §Technical Spec skeleton

### 1.3 New `agent_harness/verification/registry.py`
- [ ] **Implement VerifierRegistry**
  - `register(verifier: Verifier) -> None`
  - `get_all() -> list[Verifier]`（returns in insertion order）
  - `clear() -> None`
  - Per-request DI pattern（不 module-level singleton；per AD-Test-1 53.6 lesson）
  - File header per file-header-convention
  - DoD: API 對齐 plan US-1 acceptance

### 1.4 Update `agent_harness/verification/__init__.py`
- [ ] **Re-export new classes**
  - 加 `RulesBasedVerifier` / `VerifierRegistry` / `Rule` / `RegexRule` / `SchemaRule` / `FormatRule`
  - 既有 Verifier export 保留
  - DoD: `from agent_harness.verification import RulesBasedVerifier, VerifierRegistry` works

### 1.5 New `tests/unit/agent_harness/verification/test_rules_based.py` — 8 cases
- [ ] **Implement 8 unit tests**
  - test_regex_rule_match_pass / test_regex_rule_no_match_fail
  - test_schema_rule_valid_json_pass / test_schema_rule_missing_field_fail
  - test_format_rule_callable_pass / test_format_rule_callable_fail
  - test_verifier_runs_all_rules_returns_first_failure
  - test_verifier_p95_under_200ms (10 iterations)
  - Verify: `pytest tests/unit/agent_harness/verification/test_rules_based.py -v` → 8 passed

### 1.6 New `tests/unit/agent_harness/verification/test_registry.py` — 3 cases
- [ ] **Implement 3 unit tests**
  - test_register_verifier / test_get_all_returns_in_order / test_clear
  - Verify: `pytest tests/unit/agent_harness/verification/test_registry.py -v` → 3 passed

### 1.7 Day 1 sanity checks
- [ ] **mypy --strict on touched files** → 0 errors
- [ ] **black + isort + flake8 on touched files** → clean
- [ ] **6 V2 lints via run_all.py** → 6/6 green
- [ ] **Backend full pytest** → ~1269 passed (1258 baseline + 11 new) / 0 fail

### 1.8 Day 1 commit + push + progress.md
- [ ] **Stage + commit + push**
  - Commit message: `feat(verification, sprint-54-1): US-1 RulesBasedVerifier + VerifierRegistry + 11 unit tests`
- [ ] **Update progress.md with Day 1 actuals** — batched into commit (53.7 pattern)

---

## Day 2 — US-2 LLMJudgeVerifier + Templates + AD-Cat9-1 Fallback

### 2.1 New `agent_harness/verification/templates/` — 4 default templates
- [ ] **Create templates/__init__.py with `load_template(name: str) -> str`**
  - Reads `.txt` file from same dir; raises `FileNotFoundError` if missing
  - DoD: helper function works for all 4 templates
- [ ] **Create 4 .txt template files**
  - `factual_consistency.txt`：含 `{output}` placeholder + 期望 LLM 返回 JSON `{"passed": bool, "score": float, "reason": str, "suggested_correction": str|null}`
  - `format_compliance.txt`：判斷 markdown / json / xml 格式
  - `safety_review.txt`：判斷 harmful / unsafe (Cat 9 fallback 用)
  - `pii_leak_check.txt`：判斷 PII (Cat 9 PII fallback 用)
  - DoD: 4 templates exist; 每個含 `{output}` placeholder + JSON output instruction

### 2.2 New `agent_harness/verification/llm_judge.py`
- [ ] **Implement LLMJudgeVerifier**
  - `__init__(*, chat_client: ChatClient, judge_template: str, name: str = "llm_judge")`
  - `verify()` async：構造 prompt → `chat_client.chat()` → parse JSON → return VerificationResult
  - **Fail-closed**：try/except over chat call AND JSON parse；任何 exception → `VerificationResult(passed=False, reason="judge_error: ...")`
  - **不 import openai/anthropic** — 透過 `from adapters._base.chat_client import ChatClient`
  - File header per file-header-convention
  - DoD: 對齐 plan §Technical Spec skeleton

### 2.3 New `tests/unit/agent_harness/verification/test_llm_judge.py` — 6 cases
- [ ] **Implement 6 unit tests using MockChatClient**
  - test_judge_returns_pass_for_consistent_output
  - test_judge_returns_fail_for_inconsistent_output
  - test_judge_chat_client_exception_fail_closed
  - test_judge_malformed_response_fail_closed
  - test_judge_loads_factual_consistency_template
  - test_judge_p95_under_5s (mock with 0.5s sleep)
  - Verify: `pytest tests/unit/agent_harness/verification/test_llm_judge.py -v` → 6 passed

### 2.4 New `tests/unit/agent_harness/verification/test_templates.py` — 2 cases
- [ ] **Implement 2 unit tests**
  - test_load_template_existing_returns_content
  - test_load_template_missing_raises_FileNotFoundError
  - Verify: 2 passed

### 2.5 Modify `agent_harness/guardrails/output/engine.py` — add llm_judge_fallback
- [ ] **Add `llm_judge_fallback: LLMJudgeVerifier | None = None` parameter**
  - Day 1 探勘 will identify exact engine signature; 加參數時保持 backward compat (default None)
  - When detector confidence < threshold AND fallback is not None → call fallback.verify() → use result
  - Audit log entry: `LLM_JUDGE_FALLBACK_USED` with detector name + tenant_id
  - DoD: backward compat preserved; existing 53.3/53.5 tests unaffected

### 2.6 New `tests/integration/agent_harness/guardrails/test_llm_judge_fallback.py` — 3 cases (closes AD-Cat9-1)
- [ ] **Implement 3 integration tests**
  - test_pii_detector_low_confidence_fallback_to_judge
  - test_jailbreak_detector_meta_discussion_fallback_pass
  - test_judge_fallback_audit_log_entry_emitted
  - Verify: 3 passed; AD-Cat9-1 closure evidence

### 2.7 Day 2 sanity checks
- [ ] **mypy --strict on touched files** → 0 errors
- [ ] **black + isort + flake8** → clean
- [ ] **6 V2 lints** → 6/6 green
- [ ] **LLM SDK leak check** specifically on `llm_judge.py` → 0 (only docstring false-positives if any)
  - Verify: `grep -E "^(from |import )(openai|anthropic)" backend/src/agent_harness/verification/llm_judge.py` → empty
- [ ] **Backend full pytest** → ~1280 passed (1269 + 11 new from Day 2) / 0 fail

### 2.8 Day 2 commit + push + progress.md
- [ ] **Stage + commit + push**
  - Commit message: `feat(verification, sprint-54-1): US-2 LLMJudgeVerifier + 4 templates + AD-Cat9-1 fallback closure`
- [ ] **Update progress.md with Day 2 actuals**

---

## Day 3 — US-3 AgentLoop Self-Correction Integration + SSE + Observability

### 3.1 Modify `agent_harness/orchestrator_loop/loop.py` — add verification hook
- [ ] **Update AgentLoop.__init__ signature**
  - Add `verifier_registry: VerifierRegistry | None = None`
  - Add `max_correction_attempts: int = 2`
  - Backward compat: existing callers default None → no behavior change
  - DoD: existing AgentLoop tests still pass
- [ ] **Implement verification hook before LoopCompleted yield**
  - For attempt in range(max_correction_attempts + 1):
    - For verifier in registry.get_all(): result = await verifier.verify(...)
    - If all pass: emit VerificationPassed × N + break
    - If any fail: emit VerificationFailed + append correction to state.messages + re-run LLM call (reuse existing turn flow) + continue
  - If max attempts exhausted: emit VerificationFailed + LoopCompleted(status="verification_failed")
  - DoD: hook 邏輯對齐 plan §Technical Spec skeleton

### 3.2 Modify `agent_harness/orchestrator_loop/sse.py` — add 2 isinstance branches
- [ ] **Per `feedback_sse_serializer_scope_check.md` 教訓**：grep + add isinstance branches
  - Add branch for VerificationPassed → JSON payload with verifier_name + score
  - Add branch for VerificationFailed → JSON payload with verifier_name + reason
  - Verify: `grep "VerificationPassed\|VerificationFailed" backend/src/agent_harness/orchestrator_loop/sse.py` → 2 matches
  - DoD: SSE event 可正確序列化；chat router e2e 不 raise NotImplementedError

### 3.3 Cat 12 Observability — tracer span + 3 metrics
- [ ] **Add tracer span around each verifier call**
  - `with self._tracer.start_span(f"verifier.{verifier.__class__.__name__}")`
  - Per `observability-instrumentation.md` 5 處必埋點 §6 self-correction is the new 6th point
- [ ] **Add 3 metrics**
  - `verification_pass_rate{verifier_type, tenant_id}` (gauge)
  - `verification_duration_seconds{verifier_type}` (histogram)
  - `verification_correction_attempts{outcome}` (counter)
  - DoD: metrics emitted in test pytest output (not just in production)

### 3.4 New `tests/unit/agent_harness/orchestrator_loop/test_loop_verification_hook.py` — 3 cases
- [ ] **Implement 3 unit tests**
  - test_hook_skipped_when_registry_none (backward compat)
  - test_hook_emits_passed_event_for_clean_output
  - test_hook_appends_correction_message_on_fail
  - Verify: 3 passed

### 3.5 New `tests/integration/agent_harness/verification/test_main_flow_verification.py` — 4 cases (主流量驗收)
- [ ] **Implement 4 e2e integration tests using MockChatClient**
  - test_loop_with_passing_verifier_completes_normally (no correction)
  - test_loop_with_failing_verifier_triggers_correction_then_passes (1 attempt)
  - test_loop_max_correction_attempts_emits_verification_failed (2 attempts exhausted)
  - test_loop_emits_verification_passed_event_in_sse (SSE serialize verify)
  - Verify: 4 passed; AP-9 主流量強制 evidence

### 3.6 Day 3 sanity checks
- [ ] **mypy --strict on touched files** → 0 errors
- [ ] **black + isort + flake8** → clean
- [ ] **6 V2 lints** → 6/6 green
- [ ] **Backend full pytest** → ~1287 passed (1280 + 7 new) / 0 fail
- [ ] **Existing AgentLoop tests unchanged**: ~70 既有 loop tests 全綠 (backward compat verify)

### 3.7 Day 3 commit + push + progress.md
- [ ] **Stage + commit + push**
  - Commit message: `feat(orchestrator-loop, sprint-54-1): US-3 self-correction loop + SSE serializer + observability`
- [ ] **Update progress.md with Day 3 actuals**

---

## Day 4 — US-4 Cat 9 SANITIZE/REROLL Bridging + US-5 verify Tool + Retrospective + PR

### 4.1 US-4 — Modify `agent_harness/guardrails/output/engine.py` — wire SANITIZE/REROLL to Cat 10
- [ ] **SANITIZE path: spawn LLMJudgeVerifier with safety_review.txt → mutate output**
  - When detector hits + action=SANITIZE: call judge → use `result.suggested_correction` to replace output
  - Emit `GuardrailTriggered(action="sanitize", mutated=True)`
  - Fail-closed: judge fails → block original (don't mutate; safer default)
  - DoD: AD-Cat9-2 closure
- [ ] **REROLL path: set _pending_reroll_with_correction flag + reuse AgentLoop self-correction**
  - When detector hits + action=REROLL: state._pending_reroll_with_correction = correction string
  - AgentLoop next turn picks up flag + appends to messages + retries LLM call (reuse US-3 path)
  - DoD: AD-Cat9-3 closure (replay verified)

### 4.2 US-4 — Update existing 53.3/53.5 SANITIZE tests (assertion upgrade)
- [ ] **Per Day 0 探勘 list, upgrade 1-2 specific tests**
  - From `assert action == GuardrailAction.SANITIZE` to `assert mutated_output != original_output AND action == SANITIZE`
  - Verify: existing test count unchanged; new assertions pass
  - DoD: AD-Cat9-2 closure 加強 (existing tests confirm mutation)

### 4.3 US-4 — New tests/unit/agent_harness/guardrails/test_sanitize_mutation.py — 3 cases
- [ ] **Implement 3 unit tests**
  - test_sanitize_action_replaces_output_with_correction
  - test_sanitize_action_emits_mutated_true
  - test_sanitize_falls_back_to_block_if_judge_fails
  - Verify: 3 passed

### 4.4 US-4 — New tests/integration/agent_harness/guardrails/test_reroll_replay.py — 2 cases
- [ ] **Implement 2 integration tests**
  - test_reroll_action_appends_correction_and_retries_llm_call
  - test_reroll_max_attempts_falls_back_to_block
  - Verify: 2 passed

### 4.5 US-5 — New `agent_harness/verification/tools.py` + verify tool registration
- [ ] **Implement make_verify_tool factory**
  - `make_verify_tool(registry: VerifierRegistry) -> ToolSpec`
  - input_schema = `{"output": str}`
  - handler runs registry.get_all() then returns `{"passed": bool, "results": list[dict]}`
  - File header per file-header-convention
- [ ] **Wire into AgentLoop init**
  - When `verifier_registry is not None and tool_registry is not None`: `tool_registry.register(make_verify_tool(verifier_registry))`
  - DoD: LLM 可 tool_call "verify" 獲得 verification result

### 4.6 US-5 — New tests/integration/agent_harness/verification/test_verify_tool.py — 2 cases
- [ ] **Implement 2 integration tests**
  - test_verify_tool_runs_registry_and_returns_results
  - test_verify_tool_callable_via_llm (e2e via mock LLM tool_call)
  - Verify: 2 passed

### 4.7 Sprint final verification
- [ ] **All 3 AD closure grep evidence**
  - AD-Cat9-1: `grep "llm_judge_fallback\|LLM_JUDGE_FALLBACK_USED" backend/src/` → matches
  - AD-Cat9-2: `pytest backend/tests/unit/agent_harness/guardrails/test_sanitize_mutation.py -v` → 3 passed
  - AD-Cat9-3: `pytest backend/tests/integration/agent_harness/guardrails/test_reroll_replay.py -v` → 2 passed
  - DoD: 3/3 evidence captured
- [ ] **Cat 10 Level 4 evidence**
  - `python -c "from agent_harness.verification import RulesBasedVerifier, LLMJudgeVerifier, VerifierRegistry; print('Cat 10 Level 4 imports OK')"`
  - 主流量 e2e test (test_main_flow_verification.py) all 4 cases passing
  - DoD: Cat 10 production-ready
- [ ] **Full sweep**
  - pytest 全綠 (~1294 expected = 1258 baseline + ~36 new)
  - mypy --strict on all touched files (0 errors)
  - black + isort + flake8 + run_all.py green
  - LLM SDK leak: 0 (especially `verification/`)
  - Frontend Playwright e2e 11 specs green (regression sanity)
  - Cat 10 coverage ≥ 80% (per code-quality.md)
  - DoD: all checks pass

### 4.8 Day 4 retrospective.md
- [ ] **Create retrospective.md**
  - Path: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-1-cat10-verification/retrospective.md`
- [ ] **Answer 6 mandatory questions per 53.7 template**
  - Q1 Goal achieved + Cat 10 Level 4 evidence + 3 AD closed grep
  - Q2 Estimated vs actual + **calibration multiplier 0.55 第二次驗證** (committed 10-11 hr; actual / committed ratio; if delta < 30% → multiplier stable phase confirmed; else round-2 adjust)
  - Q3 What went well (≥ 3)
  - Q4 What can improve (≥ 3 + follow-up actions)
  - Q5 V2 9-discipline self-check (per item ✅/⚠️ — especially AP-9 主流量強制)
  - Q6 New AD logged (54.2 candidates; e.g., VisualVerifier defer / frontend verification_panel / multi-language judge templates)

### 4.9 PR open + closeout
- [ ] **Final commit + push**
  - Commit message: `docs(closeout, sprint-54-1): retrospective + Day 4 progress + final marks`
- [ ] **Open PR**
  - Title: `Sprint 54.1: Cat 10 Verification Loops (Level 4 + 3 AD closed) — V2 18→19/22`
  - Body: Summary + plan link + checklist link + 5 USs status + 3 AD closed + Anti-pattern checklist (especially AP-9) + verification evidence
  - Command: `gh pr create --title "..." --body "..."`
- [ ] **Wait for 5 active CI checks**
  - Backend CI (PG16) / V2 Lint / E2E Tests / Frontend CI / Playwright E2E
- [ ] **Normal merge after green** (solo-dev policy: review_count=0)
  - Command: `gh pr merge <num> --merge --delete-branch`
- [ ] **Verify main HEAD has merge commit**

### 4.10 Cleanup + memory update
- [ ] **Pull main + verify**
- [ ] **Delete local feature branch**: `git branch -d feature/sprint-54-1-cat10-verification`
- [ ] **Verify main 5 active CI green post-merge**
- [ ] **Memory update**
  - Create: `memory/project_phase54_1_cat10_verification.md`
  - Add to MEMORY.md index
  - Mark V2 progress: **18/22 → 19/22 (86%)**; Cat 10 Level 4; 3 AD closed
- [ ] **Working tree clean check**: `git status --short`

### 4.11 Update SITUATION-V2-SESSION-START.md
- [ ] **Update §8 Open Items**
  - Move AD-Cat9-1 + AD-Cat9-2 + AD-Cat9-3 to Closed
  - Add new AD from 54.1 retrospective Q6 (if any)
  - Add 54.2 candidate scope (Cat 11 Subagent kickoff)
- [ ] **Update §9 milestones**
  - Add Sprint 54.1 row with merge SHA + Cat 10 Level 4 + 3 AD closed
  - Update header summary: V2 19/22 (86%)
- [ ] **Update §10 必做 if needed**
  - If calibration multiplier needs second-round adjust based on Q2 verify

---

## Verification Summary（Day 4 final 必填）

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | All 5 USs delivered (Cat 10 Level 4 + 3 AD closed) | [ ] | PR #__ merged |
| 2 | Cat 10 reaches Level 4 (主流量強制) | [ ] | test_main_flow_verification.py 4/4 green |
| 3 | AD-Cat9-1 closed (LLMJudgeVerifier fallback for 4 detectors) | [ ] | grep + integration test |
| 4 | AD-Cat9-2 closed (SANITIZE actually mutates output) | [ ] | test_sanitize_mutation.py 3/3 green + assertion upgrades |
| 5 | AD-Cat9-3 closed (REROLL replays LLM call via self-correction) | [ ] | test_reroll_replay.py 2/2 green |
| 6 | RulesBasedVerifier production (3 rule types + p95 < 200ms) | [ ] | test_rules_based.py 8/8 green |
| 7 | LLMJudgeVerifier production (4 templates + fail-closed) | [ ] | test_llm_judge.py 6/6 green |
| 8 | AgentLoop self-correction loop (max 2 attempts) | [ ] | test_loop_verification_hook.py 3/3 green |
| 9 | SSE serializer covers VerificationPassed / VerificationFailed | [ ] | grep sse.py 2 matches |
| 10 | verify tool registered + LLM callable | [ ] | test_verify_tool.py 2/2 green |
| 11 | Cat 12 observability (tracer span + 3 metrics + audit log) | [ ] | metrics emitted in test output |
| 12 | pytest ~1294 / 0 fail | [ ] | command output |
| 13 | mypy --strict clean on touched files | [ ] | command output |
| 14 | run_all.py green (6 V2 lints) | [ ] | wrapper output |
| 15 | LLM SDK leak: 0 (especially `verification/`) | [ ] | grep |
| 16 | Cat 10 coverage ≥ 80% | [ ] | pytest --cov |
| 17 | Frontend Playwright e2e 11 specs green | [ ] | CI |
| 18 | Anti-pattern checklist 11 points (especially AP-9) | [ ] | retrospective |
| 19 | retrospective.md filled (6 questions + calibration verify 第二次) | [ ] | file exists with all 6 |
| 20 | Memory updated (project_phase54_1 + index) | [ ] | files |
| 21 | SITUATION-V2-SESSION-START.md updated (§8 §9) | [ ] | file |
| 22 | Branches deleted (local + remote) | [ ] | git branch -a |
| 23 | V2 progress: **18/22 → 19/22 (86%)** | [ ] | memory + SITUATION-V2 §9 |
| 24 | All 3 AD closed in retrospective Q6 with evidence | [ ] | retrospective |
