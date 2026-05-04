# Sprint 54.1 — Cat 10 Verification Loops

> **Sprint Type**: V2 main progress sprint (Phase 54 kickoff)
> **Owner Categories**: Cat 10 (Verification Loops, primary) / Cat 9 (Guardrails — SANITIZE / REROLL bridging) / Cat 1 (AgentLoop integration) / Cat 12 (Observability埋點)
> **Phase**: 54 (Verification + Subagent — 2 sprints; this is 1/2)
> **Workload**: 5 days (Day 0-4); bottom-up est ~18-19 hr → calibrated commit **~10-11 hr** (multiplier 0.55 per AD-Sprint-Plan-1; second application after 53.7 ratio 1.01 validation)
> **Branch**: `feature/sprint-54-1-cat10-verification`
> **Plan Authority**: This document (per CLAUDE.md §Sprint Execution Workflow)
> **Roadmap Source**: 06-phase-roadmap.md §Phase 54 Sprint 54.1 + 01-eleven-categories-spec.md §範疇 10 + 17-cross-category-interfaces.md §1/§2.1/§3.1/§4.1
> **Carryover absorbed**: AD-Cat9-1 (LLM-as-judge fallback for 4 detectors) + AD-Cat9-2 (Output SANITIZE actually mutates) + AD-Cat9-3 (Output REROLL replays LLM call) — all 3 share Cat 10 infra

---

## Sprint Goal

Bring 範疇 10 (Verification Loops) from **stub (Level 0)** to **Level 4 (主流量強制)** by:
- **US-1**: Implement `RulesBasedVerifier` (3 rule types: regex / schema / format) + plugin `VerifierRegistry`
- **US-2**: Implement `LLMJudgeVerifier` via Cat 2 `ChatClient` ABC + Judge prompt template library + fail-closed semantics → also closes **AD-Cat9-1**
- **US-3**: Wire self-correction loop into `AgentLoop` (max 2 attempts) + emit `VerificationPassed` / `VerificationFailed` LoopEvents + extend SSE serializer + Cat 12 tracer + metric埋點
- **US-4**: Bridge Cat 10 `VerificationResult.suggested_correction` → Cat 9 `OutputGuardrailEngine` SANITIZE / REROLL actions → also closes **AD-Cat9-2 + AD-Cat9-3**
- **US-5**: Register `verify` tool in Cat 2 `ToolRegistry` (per 17.md §3.1) so LLM can self-trigger verification + Day 4 retrospective + closeout

Sprint 結束後：(a) 主流量 `AgentLoop.run()` 在 `LoopCompleted` 之前必跑 verifier；(b) `RulesBasedVerifier` + `LLMJudgeVerifier` 兩種 production-ready；(c) 失敗驅動 self-correction 最多 2 次；(d) Cat 9 SANITIZE / REROLL 動作有實際 mutation 行為（不再 stub）；(e) verify tool LLM 可呼叫；(f) **V2 進度 18/22 → 19/22 (86%)** 推進主進度。

**主流量驗收標準**：
- `pytest backend/tests/integration/agent_harness/verification/test_main_flow_verification.py` 跑 e2e: AgentLoop 完成 LLM call → verifier 跑 → 失敗 → 自動 self-correction (1 attempt) → verifier 再跑 → 過 → emit `VerificationPassed` → `LoopCompleted`
- SSE event stream 包含 `verification_passed` 或 `verification_failed` payload（serialize_loop_event 對 2 個 event 都有 isinstance branch）
- `RulesBasedVerifier.verify()` p95 < 200ms（spec SLO）；`LLMJudgeVerifier.verify()` p95 < 5s（spec SLO，含 LLM call）
- Verifier fail-closed：`Verifier.verify()` 拋例外時，AgentLoop 視為 `passed=False`（不 swallow，亦不繼續輸出原 output）
- AD-Cat9-1 closure: 4 個 Cat 9 detectors（pii/jailbreak/prompt-injection/secret）在 regex 拒判時 fallback 到 LLMJudgeVerifier；測試證明 fallback 觸發 + 結果寫入 audit log
- AD-Cat9-2 closure: `GuardrailAction.SANITIZE` 在 OutputGuardrailEngine 實際以 `VerificationResult.suggested_correction` 替換 output；既有 53.3/53.5 SANITIZE 測試從 `assert action == SANITIZE` 升級到 `assert mutated_output != original_output`
- AD-Cat9-3 closure: `GuardrailAction.REROLL` 透過 AgentLoop self-correction 實際 replay LLM call（不只標記）；REROLL 測試證明 messages append correction + 第二次 LLM call 發出
- 新 LoopEvents (`VerificationPassed` / `VerificationFailed`) 已在 `_contracts/events.py`（49.1 stub），本 sprint **不新增 event class**，只新增 emit 點 + SSE serialize branch

---

## Background

### V2 進度

- **18/22 sprints (82%)** completed (Phase 49-55 roadmap)
- 53.7 closed (audit cycle bundle: 9 AD closed + 2 BONUS V2 lint bug fixes; calibration multiplier 0.55 ratio 1.01 validated)
- main HEAD: `7bf25e02`
- Cat 9 達 Level 5（production-deployable e2e）；Cat 10 仍是 49.1 stub（Level 0：只有 ABC + VerificationResult contract）；本 sprint 推進 Cat 10 從 Level 0 → Level 4，V2 主進度 **18/22 → 19/22 (86%)**

### 為什麼 54.1 是 Cat 10 Verification 而不是繼續 audit cycle

53.7 retrospective Q5 + Q6 + SITUATION-V2-SESSION-START.md §8 列出 5 個候選 bundle scope。選 Cat 10 主流量（**Bundle B**）原因：

1. **主進度推進**：18/22 → 19/22 接近完成（86%）
2. **Cat 9 部分 carryover 自然解**：AD-Cat9-1 (LLM-judge fallback) / AD-Cat9-2 (SANITIZE mutate) / AD-Cat9-3 (REROLL replay) 都是 Cat 10 verifier infra 的延伸；單獨在 Cat 9 內處理會重造 LLM-judge subagent 機制；放在 Cat 10 一次處理 ROI 高
3. **AP-9 (No Verification Loop) 主流量強制**：04-anti-patterns.md AP-9 是 V1 教訓核心（agent 輸出未經驗證）；Cat 10 落地後本 anti-pattern 從「結構 stub」升級到「主流量強制」
4. **Cat 11 (54.2 next sprint) 依賴**：Subagent dispatcher 需要 verifier 對 subagent 輸出做品質把關；先做 Cat 10 為 Cat 11 鋪路
5. **Phase 55 (business domain) 依賴**：5 個業務領域工具（patrol / correlation / rootcause / audit / incident）的高風險動作（rootcause_apply_fix / incident_close）需 verifier 在執行前驗證 LLM 推理；Phase 55 啟動前 Cat 10 必須 ready

### 既有結構（Day 0 探勘已 grep 確認）

```
backend/src/agent_harness/
├── _contracts/
│   ├── verification.py                                     # ✅ VerificationResult dataclass (49.1 stub; 7 fields)
│   └── events.py                                           # ✅ VerificationPassed / VerificationFailed events (49.1 stub; per 17.md §4.1)
├── verification/                                           # 🚧 Cat 10 stub (49.1; Level 0)
│   ├── __init__.py                                         # ✅ exports Verifier
│   ├── _abc.py                                             # ✅ Verifier ABC (verify() async method)
│   └── README.md                                           # ✅ design notes
├── orchestrator_loop/
│   └── loop.py                                             # 🚧 AgentLoop — 待加 verification hook 在 LoopCompleted 前
├── guardrails/
│   ├── output/
│   │   └── engine.py                                       # 🚧 GuardrailAction.SANITIZE / REROLL 當前 stub（53.3）；待 wire Cat 10
│   └── ...
└── tools/
    └── registry.py                                         # 🚧 待註冊 verify tool（17.md §3.1）

backend/src/adapters/_base/
└── chat_client.py                                          # ✅ ChatClient ABC（LLM Provider Neutrality）；LLMJudgeVerifier 透過此 import

backend/src/agent_harness/_contracts/verification.py         # ✅ VerificationResult dataclass:
                                                             #    passed: bool / verifier_name: str
                                                             #    verifier_type: Literal["rules_based", "llm_judge", "external"]
                                                             #    score / reason / suggested_correction / metadata
```

### V2 紀律 9 項對齐確認

1. **Server-Side First** ✅ Verifier 全 server-side；無 client-side 假設；fail-closed 預設保護 multi-tenant 場景
2. **LLM Provider Neutrality** ✅ LLMJudgeVerifier 透過 `adapters/_base/ChatClient` ABC，**不 import openai/anthropic**；CI lint 強制（53.3 既有 leak check）
3. **CC Reference 不照搬** ✅ Anthropic CC 的 verifier 是 client-side filesystem-based hooks；V2 server-side 必須 stateless + database-backed audit；CC 概念 (rules / judge / visual) 保留，實作完全重寫
4. **17.md Single-source** ✅ VerificationResult / VerificationPassed / VerificationFailed / Verifier ABC 全在 49.1 stub；本 sprint **不新增 type / ABC**；如需擴 Literal（e.g. visual）必須同步更新 17.md §1.1
5. **11+1 範疇歸屬** ✅ 全部 verifier 實作在 `agent_harness/verification/`；template library 在 `verification/templates/`；Cat 9 wiring 改 `guardrails/output/engine.py`（owner=Cat 9）；verify tool 註冊改 `verification/tools.py` 並由 Cat 2 Registry 收
6. **04 anti-patterns** ✅ AP-9 (No Verification Loop) 直接被本 sprint 解；AP-3 (Cross-Directory Scattering) — verifier infra 只在 `verification/`；AP-4 (Potemkin Features) — 每 verifier 必有 unit test 證明 fail path
7. **Sprint workflow** ✅ plan → checklist → Day 0 探勘 → code → progress → retro；本文件依 53.7 plan 結構鏡射（13 sections / Day 0-4）
8. **File header convention** ✅ 所有新建 .py / .md 含 Purpose / Category / Scope / Modification History
9. **Multi-tenant rule** ✅ Verifier 不存 tenant data；LLMJudgeVerifier 走 ChatClient ABC（隱式經 tenant_id propagation 不 leak across tenants）；audit log entry 含 tenant_id

---

## User Stories

### US-1: RulesBasedVerifier + VerifierRegistry Foundation (Cat 10 Level 1 → Level 2)

**As** a Cat 10 Verification implementer
**I want** `RulesBasedVerifier` 實作三種 rule types（regex / JSON schema / output format）+ pluggable `VerifierRegistry` allowing multiple verifiers run sequentially per session
**So that** 主流量 AgentLoop 結束前可呼叫 cheap fast verifier (p95 < 200ms) 對輸出做基本驗證；後續 verifier 類型（LLM-judge / external）可透過 registry plugin 添加

**Acceptance**:
- 新建 `agent_harness/verification/rules_based.py`：`RulesBasedVerifier(Verifier)` 含 3 內建規則類型
  - `RegexRule(pattern, expected_match=True)`：output 匹配 / 不匹配 regex
  - `SchemaRule(json_schema)`：output 解析為 JSON 後對齐 schema（jsonschema lib）
  - `FormatRule(format_check_fn)`：自訂 callable 返回 bool
  - `verify()` 跑所有規則 → 任一失敗即返回 `VerificationResult(passed=False)`，含 `reason` + `suggested_correction`（從 failing rule 取）
- 新建 `agent_harness/verification/registry.py`：`VerifierRegistry` 含 `register(verifier)` / `get_all() -> list[Verifier]` / `clear()`；每 session 可有自己的 instance（per request DI）
- 新建 `agent_harness/verification/types.py`：`Rule` ABC + 3 concrete classes
- 既有 `verification/_abc.py` Verifier ABC 不變動（已 stable）
- 既有 `verification/__init__.py` re-exports 擴：加 `RulesBasedVerifier` / `VerifierRegistry` / `Rule` / `RegexRule` / `SchemaRule` / `FormatRule`
- 新建 `tests/unit/agent_harness/verification/test_rules_based.py`：≥ 8 cases
  - test_regex_rule_match_pass / test_regex_rule_no_match_fail
  - test_schema_rule_valid_json_pass / test_schema_rule_missing_field_fail
  - test_format_rule_callable_pass / test_format_rule_callable_fail
  - test_verifier_runs_all_rules_returns_first_failure
  - test_verifier_p95_under_200ms (10 iterations on 1KB output)
- 新建 `tests/unit/agent_harness/verification/test_registry.py`：≥ 3 cases
  - test_register_verifier / test_get_all_returns_in_order / test_clear

**Files**:
- 新建: `backend/src/agent_harness/verification/rules_based.py`
- 新建: `backend/src/agent_harness/verification/registry.py`
- 新建: `backend/src/agent_harness/verification/types.py`
- 修改: `backend/src/agent_harness/verification/__init__.py`（re-exports）
- 新建: `backend/tests/unit/agent_harness/verification/test_rules_based.py`
- 新建: `backend/tests/unit/agent_harness/verification/test_registry.py`

### US-2: LLMJudgeVerifier + Judge Prompt Template Library (closes AD-Cat9-1)

**As** a Cat 10 Verification implementer
**I want** `LLMJudgeVerifier` 透過 `ChatClient` ABC（LLM Provider Neutrality）spawn 獨立 LLM 呼叫對 output 做 judge + 4 個 default judge prompt templates + fail-closed semantics
**So that** 規則無法表達的 quality 維度（factual consistency / safety / format coherence）可由 LLM 評；同時 Cat 9 的 4 個 detectors（pii/jailbreak/prompt-injection/secret）regex 拒判時 fallback 到 LLM-judge（**closes AD-Cat9-1**）

**Acceptance**:
- 新建 `agent_harness/verification/llm_judge.py`：`LLMJudgeVerifier(Verifier)`
  - `__init__(chat_client: ChatClient, judge_template: str, model: str | None = None)`
  - `verify()` 構造 judge prompt（system + user + 待驗 output）→ `chat_client.chat()` → parse `passed: bool` + `score: float` + `reason: str` from JSON
  - **Fail-closed**：if `chat_client.chat()` raises any exception OR judge returns malformed response → `VerificationResult(passed=False, reason="judge_error: ...")`
  - **不 import openai/anthropic**（CI lint 強制；既有 53.3 leak check 涵蓋）
- 新建 `agent_harness/verification/templates/`：4 default templates 各為一 `.txt` file（純 prompt 字串）
  - `factual_consistency.txt`：判斷 output 是否與 source 信息一致
  - `format_compliance.txt`：判斷 output 是否符合 markdown / json / xml 格式要求
  - `safety_review.txt`：判斷 output 是否含 harmful / unsafe content（為 Cat 9 fallback 用）
  - `pii_leak_check.txt`：判斷 output 是否含 PII（為 Cat 9 PII detector regex 拒判 fallback 用）
- 新建 `agent_harness/verification/templates/__init__.py`：`load_template(name: str) -> str` helper
- 修改 `agent_harness/guardrails/output/engine.py`：加 optional `llm_judge_fallback: LLMJudgeVerifier | None = None` 參數；當 detector 在 `_LOW_CONFIDENCE_THRESHOLD`（既有 53.3 const；確認後微調）以下時 fallback 呼叫 judge → AD-Cat9-1 closure
- 新建 `tests/unit/agent_harness/verification/test_llm_judge.py`：≥ 6 cases
  - test_judge_returns_pass_for_consistent_output (mock ChatClient)
  - test_judge_returns_fail_for_inconsistent_output (mock ChatClient)
  - test_judge_chat_client_exception_fail_closed
  - test_judge_malformed_response_fail_closed
  - test_judge_loads_factual_consistency_template
  - test_judge_p95_under_5s (10 iterations with mock ChatClient that sleeps 0.5s)
- 新建 `tests/unit/agent_harness/verification/test_templates.py`：≥ 2 cases
  - test_load_template_existing / test_load_template_missing_raises
- 新建 `tests/integration/agent_harness/guardrails/test_llm_judge_fallback.py`：≥ 3 cases (closes AD-Cat9-1)
  - test_pii_detector_low_confidence_fallback_to_judge
  - test_jailbreak_detector_meta_discussion_fallback_pass
  - test_judge_fallback_audit_log_entry_emitted

**Files**:
- 新建: `backend/src/agent_harness/verification/llm_judge.py`
- 新建: `backend/src/agent_harness/verification/templates/__init__.py`
- 新建: `backend/src/agent_harness/verification/templates/factual_consistency.txt`
- 新建: `backend/src/agent_harness/verification/templates/format_compliance.txt`
- 新建: `backend/src/agent_harness/verification/templates/safety_review.txt`
- 新建: `backend/src/agent_harness/verification/templates/pii_leak_check.txt`
- 修改: `backend/src/agent_harness/guardrails/output/engine.py`（加 llm_judge_fallback 參數 + low-confidence path）
- 新建: `backend/tests/unit/agent_harness/verification/test_llm_judge.py`
- 新建: `backend/tests/unit/agent_harness/verification/test_templates.py`
- 新建: `backend/tests/integration/agent_harness/guardrails/test_llm_judge_fallback.py`

### US-3: AgentLoop Self-Correction Integration + SSE + Observability

**As** a Cat 1 Orchestrator integrator
**I want** AgentLoop 在 `LoopCompleted` 之前必跑 verifier registry → 失敗時觸發 self-correction（max 2 attempts；correction message append messages）→ emit `VerificationPassed` / `VerificationFailed` LoopEvents → SSE serializer cover 兩 events → Cat 12 tracer span + metric
**So that** 主流量驗收的 V2 主進度推進；AP-9 (No Verification Loop) 從 stub 升級主流量強制

**Acceptance**:
- 修改 `agent_harness/orchestrator_loop/loop.py`：`AgentLoop.run()` 在最後 `yield LoopCompleted` 之前加 verification hook
  - `__init__` 加 `verifier_registry: VerifierRegistry | None = None` + `max_correction_attempts: int = 2`
  - 在 LLM 給出 final output 後，若 `verifier_registry is not None`：跑 `for verifier in registry.get_all(): result = await verifier.verify(...)` → 任一 fail → 構造 correction message append `state.messages` → 重 LLM call（attempt += 1；至 max_correction_attempts）→ 全 pass 才 emit `VerificationPassed` + `LoopCompleted`
  - 若 max attempts 用盡仍 fail：emit `VerificationFailed` + `LoopCompleted(status="verification_failed")`（不 swallow）
- 修改 `agent_harness/orchestrator_loop/sse.py`：`serialize_loop_event` 加 2 個 isinstance branches for `VerificationPassed` / `VerificationFailed`（per `feedback_sse_serializer_scope_check.md` — Day 0 探勘必 grep）
- 修改 `agent_harness/orchestrator_loop/loop.py`：tracer span（per `observability-instrumentation.md` 5 處必埋點 §3 LLM call + §6 self-correction 是新增第 6 處）
- 新建 metric: `verification_pass_rate` (gauge) + `verification_duration_seconds` (histogram) + `verification_correction_attempts` (counter)
- 新建 `tests/integration/agent_harness/verification/test_main_flow_verification.py`：≥ 4 cases
  - test_loop_with_passing_verifier_completes_normally (no correction needed)
  - test_loop_with_failing_verifier_triggers_correction_then_passes
  - test_loop_max_correction_attempts_emits_verification_failed
  - test_loop_emits_verification_passed_event_in_sse
- 新建 `tests/unit/agent_harness/orchestrator_loop/test_loop_verification_hook.py`：≥ 3 cases
  - test_hook_skipped_when_registry_none
  - test_hook_emits_passed_event_for_clean_output
  - test_hook_appends_correction_message_on_fail

**Files**:
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（add verifier_registry param + correction loop + 2 event emits + tracer + metrics）
- 修改: `backend/src/agent_harness/orchestrator_loop/sse.py`（add 2 isinstance branches）
- 新建: `backend/tests/integration/agent_harness/verification/test_main_flow_verification.py`
- 新建: `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_verification_hook.py`

### US-4: Cat 10 → Cat 9 SANITIZE / REROLL Bridging (closes AD-Cat9-2 + AD-Cat9-3)

**As** a Cat 9 Guardrails maintainer
**I want** Cat 9 OutputGuardrailEngine 的 `GuardrailAction.SANITIZE` 實際以 `VerificationResult.suggested_correction` 替換 output（**不再 stub**），`GuardrailAction.REROLL` 透過 AgentLoop self-correction loop 實際 replay LLM call（**不再標記**）
**So that** AD-Cat9-2 + AD-Cat9-3 兩個 53.3 carryover 一次性 closure；Cat 9 production-grade SANITIZE / REROLL 可信

**Acceptance**:
- 修改 `agent_harness/guardrails/output/engine.py`：
  - `GuardrailAction.SANITIZE` 處理路徑：當 detector 偵測命中 → spawn LLMJudgeVerifier with `safety_review.txt` template → 取 `VerificationResult.suggested_correction` → 替換 LoopState 的 final_output → emit `GuardrailTriggered(action="sanitize", mutated=True)`
  - `GuardrailAction.REROLL` 處理路徑：當 detector 偵測命中 → 在 LoopState 標 `_pending_reroll_with_correction = result.suggested_correction` → AgentLoop self-correction loop 在下一 turn 自動 append 該 correction 為 user message → 重 LLM call（reuse US-3 correction infra；不另寫 reroll 邏輯）
- 修改 `agent_harness/orchestrator_loop/loop.py`：correction loop 處理 `_pending_reroll_with_correction` flag（與 verifier 失敗 correction 走同一 path）
- 既有 53.3/53.5 SANITIZE 測試從 `assert action == SANITIZE` 升級為 `assert mutated_output != original_output`
- 新建 `tests/unit/agent_harness/guardrails/test_sanitize_mutation.py`：≥ 3 cases (closes AD-Cat9-2)
  - test_sanitize_action_replaces_output_with_correction
  - test_sanitize_action_emits_mutated_true
  - test_sanitize_falls_back_to_original_if_judge_fails (fail-closed: original blocked but not mutated)
- 新建 `tests/integration/agent_harness/guardrails/test_reroll_replay.py`：≥ 2 cases (closes AD-Cat9-3)
  - test_reroll_action_appends_correction_and_retries_llm_call
  - test_reroll_max_attempts_falls_back_to_block

**Files**:
- 修改: `backend/src/agent_harness/guardrails/output/engine.py`（SANITIZE / REROLL 路徑 wire Cat 10）
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（correction loop 接 _pending_reroll_with_correction flag — 視 Day 1 探勘是否能 reuse US-3 path）
- 修改: 1-2 個既有 53.3/53.5 SANITIZE 測試 (升級 assertion)
- 新建: `backend/tests/unit/agent_harness/guardrails/test_sanitize_mutation.py`
- 新建: `backend/tests/integration/agent_harness/guardrails/test_reroll_replay.py`

### US-5: verify Tool Registration + Cat 12 Observability + Day 4 Closeout

**As** an LLM consumer of the agent harness
**I want** `verify` tool 註冊到 Cat 2 ToolRegistry（per 17.md §3.1）讓 LLM 可 self-trigger verification 在 mid-loop（不只 final output 時跑），加上完整 Cat 12 observability + Day 4 retrospective
**So that** Cat 10 達 Level 4（主流量強制 + LLM 自呼叫 + 完整觀測性 + retrospective 文件）

**Acceptance**:
- 新建 `agent_harness/verification/tools.py`：`make_verify_tool(registry: VerifierRegistry) -> ToolSpec` factory
  - ToolSpec name="verify"，input_schema = `{"output": str}`，returns `{"passed": bool, "results": list[dict]}`
  - handler 跑 verifier registry 後返回所有 result 結構化
  - 註冊到 ToolRegistry：在 AgentLoop init 時呼叫 `registry.register(make_verify_tool(verifier_registry))`
- Cat 12 observability 完整化（per `observability-instrumentation.md`）：
  - Tracer span: `verifier.{verifier_name}` 圈住每 verify call
  - Metric: `verification_pass_rate{verifier_type, tenant_id}` (gauge)
  - Metric: `verification_duration_seconds{verifier_type}` (histogram, p50/p95/p99)
  - Metric: `verification_correction_attempts{outcome}` (counter)
  - Audit log entry: `VERIFICATION_PASSED` / `VERIFICATION_FAILED` 含 `verifier_name` / `score` / `reason` / `tenant_id`
- 新建 `tests/integration/agent_harness/verification/test_verify_tool.py`：≥ 2 cases
  - test_verify_tool_runs_registry_and_returns_results
  - test_verify_tool_callable_via_llm (e2e via mock LLM tool_call)
- 新建 retrospective.md (Day 4) per 53.7 6-question template + calibration multiplier verification
- 新建 progress.md daily entries (Day 0-4)

**Files**:
- 新建: `backend/src/agent_harness/verification/tools.py`
- 修改: `backend/src/agent_harness/orchestrator_loop/loop.py`（register verify tool 在 init）
- 新建: `backend/tests/integration/agent_harness/verification/test_verify_tool.py`
- 新建: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-1-cat10-verification/progress.md`
- 新建: `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-1-cat10-verification/retrospective.md`

---

## Technical Specifications

### File Skeleton — `agent_harness/verification/rules_based.py`

```python
"""
File: backend/src/agent_harness/verification/rules_based.py
Purpose: Rules-based verifier (regex / JSON schema / format check); fast cheap verifier (p95 < 200ms).
Category: 範疇 10 (Verification Loops)
Scope: Sprint 54.1 US-1
"""
from __future__ import annotations
from agent_harness._contracts import LoopState, TraceContext, VerificationResult
from agent_harness.verification._abc import Verifier
from agent_harness.verification.types import Rule

class RulesBasedVerifier(Verifier):
    def __init__(self, rules: list[Rule], name: str = "rules_based"):
        self._rules = rules
        self._name = name

    async def verify(self, *, output: str, state: LoopState,
                     trace_context: TraceContext | None = None) -> VerificationResult:
        for rule in self._rules:
            ok, reason, suggestion = rule.check(output)
            if not ok:
                return VerificationResult(
                    passed=False, verifier_name=self._name,
                    verifier_type="rules_based", reason=reason,
                    suggested_correction=suggestion,
                )
        return VerificationResult(passed=True, verifier_name=self._name, verifier_type="rules_based")
```

### File Skeleton — `agent_harness/verification/llm_judge.py`

```python
"""
File: backend/src/agent_harness/verification/llm_judge.py
Purpose: LLM-as-judge verifier; spawn ChatClient call (LLM provider neutral) for quality dimensions regex can't express. Fail-closed.
Category: 範疇 10 (Verification Loops)
Scope: Sprint 54.1 US-2; closes AD-Cat9-1
"""
from __future__ import annotations
import json
from agent_harness._contracts import Message, VerificationResult
from agent_harness.verification._abc import Verifier
from agent_harness.verification.templates import load_template
from adapters._base.chat_client import ChatClient

class LLMJudgeVerifier(Verifier):
    def __init__(self, *, chat_client: ChatClient, judge_template: str, name: str = "llm_judge"):
        self._chat = chat_client
        self._template = judge_template  # template name OR raw prompt
        self._name = name

    async def verify(self, *, output, state, trace_context=None):
        try:
            prompt = self._build_prompt(output)
            resp = await self._chat.chat(messages=[Message(role="user", content=prompt)], tools=[])
            return self._parse_response(resp.content)
        except Exception as e:
            # Fail-closed: any error → passed=False
            return VerificationResult(
                passed=False, verifier_name=self._name, verifier_type="llm_judge",
                reason=f"judge_error: {type(e).__name__}: {e}",
            )

    def _build_prompt(self, output: str) -> str:
        template = load_template(self._template) if not self._template.startswith("{") else self._template
        return template.replace("{output}", output)

    def _parse_response(self, content: str) -> VerificationResult:
        # Expect JSON: {"passed": bool, "score": float, "reason": str, "suggested_correction": str | null}
        try:
            data = json.loads(content)
            return VerificationResult(
                passed=bool(data["passed"]), verifier_name=self._name, verifier_type="llm_judge",
                score=data.get("score"), reason=data.get("reason"),
                suggested_correction=data.get("suggested_correction"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            return VerificationResult(
                passed=False, verifier_name=self._name, verifier_type="llm_judge",
                reason=f"malformed_judge_response: {e}",
            )
```

### File Skeleton — AgentLoop verification hook (excerpt for US-3)

```python
# backend/src/agent_harness/orchestrator_loop/loop.py — additions for US-3

class AgentLoop:
    def __init__(self, *, ..., verifier_registry: VerifierRegistry | None = None,
                 max_correction_attempts: int = 2):
        ...
        self._verifier_registry = verifier_registry
        self._max_corrections = max_correction_attempts

    async def run(self, ...) -> AsyncIterator[LoopEvent]:
        ...
        # After LLM produces final output, before LoopCompleted:
        if self._verifier_registry is not None:
            output = ...  # from final assistant message
            for attempt in range(self._max_corrections + 1):
                all_passed = True
                for verifier in self._verifier_registry.get_all():
                    with self._tracer.start_span(f"verifier.{verifier.__class__.__name__}"):
                        result = await verifier.verify(output=output, state=state)
                    if result.passed:
                        yield VerificationPassed(verifier_name=result.verifier_name, score=result.score)
                    else:
                        yield VerificationFailed(verifier_name=result.verifier_name, reason=result.reason)
                        if attempt < self._max_corrections and result.suggested_correction:
                            state.messages.append(Message(role="user",
                                content=f"Verification failed: {result.reason}. {result.suggested_correction}"))
                            # re-run LLM (reuse existing turn loop)
                            output = await self._rerun_llm(state)
                            all_passed = False
                            break  # restart verifier loop with new output
                if all_passed:
                    break
            self._metrics.record("verification_correction_attempts", attempt,
                                 attributes={"outcome": "passed" if all_passed else "failed"})
        yield LoopCompleted(status="completed" if all_passed else "verification_failed")
```

### Pre-Push Lint Chain (unchanged from 53.7)

```bash
black backend/src --check && isort backend/src --check && flake8 backend/src && mypy backend/src --strict
python scripts/lint/run_all.py  # 6 V2 lints (per AD-Lint-1 closure 53.7)
cd frontend && npm run lint && npm run build  # if frontend touched (54.1 = backend-only)
```

---

## File Change List

### 新建（19 個）

**Cat 10 source** (10):
1. `backend/src/agent_harness/verification/rules_based.py`
2. `backend/src/agent_harness/verification/llm_judge.py`
3. `backend/src/agent_harness/verification/registry.py`
4. `backend/src/agent_harness/verification/types.py`
5. `backend/src/agent_harness/verification/tools.py`
6. `backend/src/agent_harness/verification/templates/__init__.py`
7. `backend/src/agent_harness/verification/templates/factual_consistency.txt`
8. `backend/src/agent_harness/verification/templates/format_compliance.txt`
9. `backend/src/agent_harness/verification/templates/safety_review.txt`
10. `backend/src/agent_harness/verification/templates/pii_leak_check.txt`

**Tests** (8):
11. `backend/tests/unit/agent_harness/verification/test_rules_based.py`
12. `backend/tests/unit/agent_harness/verification/test_registry.py`
13. `backend/tests/unit/agent_harness/verification/test_llm_judge.py`
14. `backend/tests/unit/agent_harness/verification/test_templates.py`
15. `backend/tests/integration/agent_harness/guardrails/test_llm_judge_fallback.py`
16. `backend/tests/unit/agent_harness/orchestrator_loop/test_loop_verification_hook.py`
17. `backend/tests/integration/agent_harness/verification/test_main_flow_verification.py`
18. `backend/tests/unit/agent_harness/guardrails/test_sanitize_mutation.py`
19. `backend/tests/integration/agent_harness/guardrails/test_reroll_replay.py`
20. `backend/tests/integration/agent_harness/verification/test_verify_tool.py`

**Documentation** (2):
21. `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-1-cat10-verification/progress.md`
22. `docs/03-implementation/agent-harness-execution/phase-54-verification-subagent/sprint-54-1-cat10-verification/retrospective.md`

### 修改（4 個）

1. `backend/src/agent_harness/verification/__init__.py`（re-exports 擴：RulesBasedVerifier / LLMJudgeVerifier / VerifierRegistry / Rule / RegexRule / SchemaRule / FormatRule）
2. `backend/src/agent_harness/orchestrator_loop/loop.py`（verifier_registry param + correction loop + verify tool register + tracer/metrics）
3. `backend/src/agent_harness/orchestrator_loop/sse.py`（add 2 isinstance branches for VerificationPassed / VerificationFailed）
4. `backend/src/agent_harness/guardrails/output/engine.py`（llm_judge_fallback param + SANITIZE/REROLL wire Cat 10）

### 修改（1-2 個既有測試 — assertion upgrade）

5. 1-2 個既有 53.3/53.5 SANITIZE 測試 (Day 1 探勘列出具體文件清單)

---

## Acceptance Criteria

### 主流量端到端驗收

- [ ] **US-1 RulesBasedVerifier production**: `RulesBasedVerifier` 跑 3 種規則類型 + p95 < 200ms 驗證；VerifierRegistry plugin pattern works
- [ ] **US-2 LLMJudgeVerifier + AD-Cat9-1 closure**: `LLMJudgeVerifier` 透過 ChatClient ABC 跑；4 templates 載入成功；4 Cat 9 detectors low-confidence path fallback 到 judge；audit log 紀錄 fallback 使用
- [ ] **US-3 AgentLoop self-correction**: 主流量 e2e 測試 — 失敗 verifier → correction → re-pass → LoopCompleted；SSE event stream 含 verification_passed payload
- [ ] **US-4 AD-Cat9-2 + AD-Cat9-3 closure**: SANITIZE 測試從 `assert action == SANITIZE` 升級到 `assert mutated_output != original_output`；REROLL 測試證明 LLM call replay
- [ ] **US-5 verify tool callable**: LLM 透過 tool_call 呼叫 verify tool；observability 完整（tracer + 3 metrics + audit log）

### 品質門檻

- [ ] pytest 全綠（baseline 1258 → 預期 ~1290+ passed，+30-35 from 54.1 new tests）
- [ ] mypy --strict 0 errors（所有 verification/ + 改動 loop.py / sse.py / engine.py）
- [ ] flake8 + black + isort green（pre-push 跑）
- [ ] 6 V2 lints green（透過 `run_all.py`）
- [ ] LLM SDK leak: 0（特別檢查 `llm_judge.py` 不 import openai/anthropic）
- [ ] Cat 10 coverage ≥ 80%（per code-quality.md range owner target）
- [ ] 既有 Frontend e2e 11 specs 全綠（不應受 backend-only 改動影響）
- [ ] CI: 5 active checks green (Backend / V2 Lint / E2E / Frontend CI / Playwright E2E)

### 範疇對齐

- [ ] **Cat 10 reaches Level 4**: 主流量強制 verification + 2 verifier types (rules + judge) + self-correction loop + verify tool + observability
- [ ] **AD-Cat9-1 closed**: 4 detectors fallback to LLMJudgeVerifier; integration test green
- [ ] **AD-Cat9-2 closed**: SANITIZE actually mutates output via `suggested_correction`; assertion upgraded
- [ ] **AD-Cat9-3 closed**: REROLL replays LLM call via AgentLoop self-correction loop
- [ ] **17.md compliance**: VerificationResult / VerificationPassed / VerificationFailed / Verifier ABC unchanged (single-source preserved); no new types added

---

## Deliverables（見 checklist 詳細）

US-1 到 US-5 共 5 個 User Stories；checklist 拆分到 Day 0-4。

---

## Dependencies & Risks

### Dependencies

| Dependency | 來自 | 必須狀態 |
|------------|------|---------|
| 49.1 Cat 10 stub (Verifier ABC + VerificationResult contract + VerificationPassed/Failed events) | 49.1 | ✅ all in place; verified by Day 0 探勘 |
| 50.1 Cat 6 OutputParser + Cat 1 AgentLoop run() AsyncIterator | 50.1 | ✅ merged main |
| 53.2 Cat 8 ErrorPolicy (verifier exception fallback uses fail-closed) | 53.2 | ✅ merged main |
| 53.3 Cat 9 OutputGuardrailEngine + GuardrailAction enum | 53.3 | ✅ merged main (US-4 修改 engine.py) |
| 53.4 §HITL Centralization (verifier 不需 HITL；但 high-risk verification fail 可選擇 escalate) | 53.4 | ✅ merged main; 不阻塞本 sprint |
| 53.7 calibration multiplier 0.55 + sprint-workflow.md §Workload Calibration | 53.7 | ✅ merged main; 本 sprint plan §Workload 應用 |
| ChatClient ABC (LLM Provider Neutrality) | 49.3 + 50.x | ✅ stable; LLMJudgeVerifier 透過此 |

### Risks (per `sprint-workflow.md` §Common Risk Classes)

| Risk | Class | Mitigation |
|------|-------|-----------|
| Self-correction loop 與既有 turn loop 整合可能 mid-LLM-call 衝突（state.messages mutation 時序） | logic | Day 1 US-3 探勘 spec out 具體 attempt boundary；先寫 unit test for `test_hook_appends_correction_message_on_fail` 鎖行為 |
| LLM-judge p95 < 5s SLO 在 mock test 易達；real LLM call 在 CI 無預算 | infra | 用 mock ChatClient 跑 SLO；real LLM smoke test 留 manual / CARRY |
| Fail-closed semantics 可能讓 happy path 過於嚴格（judge 偶發 timeout 即視為 fail） | logic | judge timeout 應透過 Cat 8 ErrorPolicy retry once；retry 失敗才走 fail-closed；US-2 acceptance 含此 case |
| AD-Cat9-2/3 closure 需要既有 53.3/53.5 SANITIZE/REROLL 測試 assertion 升級；可能找不到對應 test | A (paths-filter risk class proxy — 探勘) | Day 1 US-4 探勘必 grep `GuardrailAction.SANITIZE` 在 test 檔案出現位置；確認後升級 1-2 個 test；找不到則 carryover |
| `feedback_sse_serializer_scope_check.md` 教訓：US-3 加 2 個 LoopEvent emits 但 SSE serializer 漏 isinstance branch → 主流量 chat router 拋 NotImplementedError | A (Day 0 探勘類) | Day 0 + Day 3 sanity check `grep "VerificationPassed\|VerificationFailed" backend/src/agent_harness/orchestrator_loop/sse.py` |
| Module-level singleton issue (per AD-Test-1 / 53.6 教訓): VerifierRegistry 可能在 module-level cache 跨 event loop | C (singleton class) | VerifierRegistry per-request DI（不 cache module-level）；testing.md §Module-level Singleton Reset Pattern 不適用於本 sprint |
| Cross-platform mypy `unused-ignore` (per AD-Lint-2 / 52.6 教訓) | B | 已知 cross-platform mypy 行為差；如需用 `# type: ignore[X, unused-ignore]` 雙 ignore code |
| `test_main_flow_verification.py` 初次跑可能因 mock ChatClient 簽名與 real ChatClient 偏差 fail | logic | Day 3 US-3 測試先用既有 50.2 mock ChatClient pattern (test fixtures `_test_factories.py`) |

### 主流量驗證承諾

54.1 不允許「Cat 10 標 Level 4 但 verification 在主流量為 opt-in / disabled」交付。`AgentLoop.run()` 主流量必須在 `verifier_registry is not None` 時跑驗證 + emit events；驗收測試從 chat router 入口（POST /chat）e2e 走完整流程。54.1 是 V2 主進度推進（18/22 → 19/22）；交付即更新 SITUATION-V2-SESSION-START.md §9 milestones + 累計進度。

---

## Audit Carryover Section

### 從 53.x 反激活（in scope；本 sprint 處理）

- ✅ **AD-Cat9-1** LLM-as-judge fallback for 4 detectors (US-2)
- ✅ **AD-Cat9-2** Output SANITIZE actually mutates output via `suggested_correction` (US-4)
- ✅ **AD-Cat9-3** Output REROLL replays LLM call via AgentLoop self-correction (US-4)

### Defer 至 54.2 / Phase 55 / Audit cycle bundle（不在本 sprint scope）

- 🚧 **AD-Cat9-5** ToolGuardrail max-calls-per-session counter → 53.8 / future audit cycle（需 session state 耦合 + Cat 7 reducer）
- 🚧 **AD-Cat9-6** WORMAuditLog real-DB integration tests → 53.8 / future audit cycle
- 🚧 **AD-Cat7-1** Full sole-mutator pattern (grep-zero refactor) → 54.2 / Phase 55（與 Cat 11 Subagent state 整合）
- 🚧 **AD-Cat8-1/2/3** Cat 8 carryover → Phase 55 / future audit cycle
- 🚧 **AD-Hitl-7** Per-tenant HITLPolicy DB persistence → 53.8 / future audit cycle
- 🚧 **AD-Plan-1** Day-0 plan-vs-repo verify rule → next audit cycle (already partially applied to 54.1 plan via Day 0 探勘 in checklist)
- 🚧 **AD-Lint-2** Drop per-day calibrated targets → next checklist template iteration (54.1 checklist 已不寫 per-day targets)
- 🚧 **AD-CI-5** required_status_checks paths-filter long-term fix → independent infra track
- 🚧 **AD-CI-6** Deploy to Production chronic fail → independent infra track
- 🚧 **#31** V2 Dockerfile → independent infra track
- 🚧 **VisualVerifier** (Playwright screenshot) — spec 列出但 Day 4 retro 視為 Phase 55+ defer（V2 server-side 場景使用率低；保留 ABC stub 即可）
- 🚧 **Frontend `verification_panel`** (06-roadmap mentions) — Day 4 retro 評估是否在 54.2 / 55.x frontend sprint 處理

### 54.1 新 Audit Debt（保留位置；retro 補充）

`AD-Cat10-*` / `AD-Verifier-*` 可能在 retrospective Q4 加入（e.g., judge prompt template 在多語言場景需擴；correction loop attempt boundary 細節調整需求）。

---

## §10 Process 修補落地檢核

- [ ] Plan 文件起草前讀 53.7 plan + checklist 作 template (per `feedback_sprint_plan_use_prior_template.md`) ✅ done
- [ ] Checklist 同樣以 53.7 為 template（Day 0-4，每 task 3-6 sub-bullets，含 DoD + Verify command；不寫 per-day calibrated targets per AD-Lint-2）
- [ ] Pre-push lint 完整跑 black + isort + flake8 + mypy + run_all.py（per AD-Lint-1 53.7 closure）
- [ ] Day 0 探勘 必 grep VerificationPassed / VerificationFailed 在 SSE serializer 出現位置（per `feedback_sse_serializer_scope_check.md`）
- [ ] Day 0 探勘 必 grep §Technical Spec assertions vs repo state（per AD-Plan-1 53.7 lesson）
- [ ] PR commit message 含 scope + sprint ID + Co-Authored-By
- [ ] Anti-pattern checklist 11 條 PR 前自檢（特別 AP-9 主流量強制；AP-3 範疇歸屬；AP-4 Potemkin）
- [ ] CARRY items 清單可追溯到 53.3 retrospective Q4（AD-Cat9-1/2/3）
- [ ] V2 lint 6 scripts CI green（透過 run_all.py）
- [ ] Frontend lint + type check + build green（不應受 backend-only 改動影響）
- [ ] LLM SDK leak: 0（grep openai/anthropic in `verification/`）
- [ ] Cat 10 coverage ≥ 80%

---

## Retrospective 必答（per W3-2 + 52.6 + 53.x 教訓 + AD-Sprint-Plan-1 calibration verify）

Day 4 retrospective.md 必答 6 題：

1. **Sprint Goal achieved?**（Yes/No + Cat 10 達 Level 4 evidence + 3 AD closed grep / test 證據）
2. **Estimated vs actual hours**（per US；總計；**+ calibration multiplier 0.55 第二次驗證：actual / committed ratio；本 sprint 是 53.7 後第二次應用 0.55，若連續 2 sprint ratio 偏差 < 30% 則 multiplier 進入 stable phase**）
3. **What went well**（≥ 3 items；含 banked buffer 來源）
4. **What can improve**（≥ 3 items + 對應的 follow-up action）
5. **V2 9-discipline self-check**（逐項 ✅/⚠️ 評估；特別 AP-9 主流量強制驗證）
6. **Audit Debt logged**（54.1 新發現的 issue + 54.2 candidate scope 候選清單；本 sprint 結束後 V2 進度 19/22）

---

## Sprint Closeout

- [ ] All 5 USs delivered with 主流量 verification（Cat 10 Level 4 + 3 AD closed）
- [ ] PR open + 5 active CI checks → green
- [ ] Normal merge to main (solo-dev policy: review_count=0; no temp-relax needed)
- [ ] retrospective.md filled (6 questions; **含 calibration multiplier 第二次 accuracy verification**)
- [ ] Memory update (project_phase54_1_cat10_verification.md + index)
- [ ] Branch deleted (local + remote)
- [ ] V2 progress: **18/22 → 19/22 (86%)**（主進度推進 — 不是 carryover bundle）
- [ ] Cat 10 reaches Level 4 (主流量強制)
- [ ] AD-Cat9-1 + AD-Cat9-2 + AD-Cat9-3 closed in retrospective Q6 with grep / test evidence
- [ ] SITUATION-V2-SESSION-START.md §8 (Open Items) + §9 (milestones) updated
- [ ] AP-9 (No Verification Loop) 從 04-anti-patterns.md 角度標 closed (主流量強制)
