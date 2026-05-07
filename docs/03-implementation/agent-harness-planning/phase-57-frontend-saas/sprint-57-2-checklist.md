# Sprint 57.2 — Checklist

> [Sprint 57.2 Plan](./sprint-57-2-plan.md) — Audit Cycle Lvl 2: Carryover ADs Closure + 11+1 範疇 Alignment Final Check
> **Branch**: `feature/sprint-57-2-audit-cycle-carryover`
> **Calibrated commit**: ~14-17 hr（`large multi-domain` 0.55 3rd application）

---

## Day 0 — 探勘 + 三-prong plan-vs-repo verify + branch create

### 0.1 Branch + baseline confirm

- [ ] **Branch create + baseline state captured**
  - DoD: `git checkout -b feature/sprint-57-2-audit-cycle-carryover` clean from main HEAD `96716a1a`
  - Command: `git checkout main && git pull && git checkout -b feature/sprint-57-2-audit-cycle-carryover`
- [ ] **pytest baseline 1557 confirmed**
  - DoD: `python -m pytest backend/tests --collect-only` 報 1557 / 4 skip
  - Command: `cd backend && python -m pytest --collect-only 2>&1 | tail -3`
- [ ] **mypy --strict baseline 0/293 source files confirmed**
  - DoD: 0 errors
  - Command: `cd backend && python -m mypy src --strict 2>&1 | tail -3`
- [ ] **8 V2 lints 8/8 baseline confirmed**
  - DoD: all 8 scripts return exit 0
  - Command: `python scripts/lint/run_all.py`
- [ ] **LLM SDK leak baseline 0 confirmed**
  - DoD: `grep -rn "^import openai\|^from openai\|^import anthropic\|^from anthropic" backend/src/agent_harness/ backend/src/business_domain/` returns 0
  - Command: `grep -rn "^import openai\|^from openai\|^import anthropic\|^from anthropic" backend/src/agent_harness/ backend/src/business_domain/ | wc -l`

### 0.2 三-prong plan-vs-repo verify（per sprint-workflow.md §Step 2.5）

#### Prong 1 — Path Verify（AD-Plan-2）

- [ ] **US-1 paths exist as plan asserts**
  - Verify: `backend/src/business_domain/cost_ledger/service.py` exists（56.3 introduced）
  - Verify: `backend/src/business_domain/cost_ledger/pricing_loader.py` exists
  - Verify: `backend/src/api/v1/chat/router.py` exists（觀察 LoopCompleted hook）
  - Verify: `backend/src/agent_harness/_contracts/events.py` exists（LoopCompleted definition）
  - Glob: `Glob("backend/src/business_domain/cost_ledger/*.py")` returns ≥ 2 files
- [ ] **US-2 paths exist as plan asserts**
  - Verify: `backend/src/agent_harness/orchestrator_loop/loop.py` exists
  - Verify: `backend/src/agent_harness/orchestrator_loop/_metrics.py` does NOT exist（plan asserts NEW）
  - Glob: `Glob("backend/src/agent_harness/orchestrator_loop/_metrics.py")` returns 0
- [ ] **US-3 paths exist as plan asserts**
  - Verify: `backend/src/agent_harness/guardrails/engine.py` exists
  - Verify: 4 detectors（pii / jailbreak / secrets_leak / role_confusion）存在於 `guardrails/`
  - Glob: `Glob("backend/src/agent_harness/guardrails/*_detector.py")` returns 4
- [ ] **US-4 paths exist as plan asserts**
  - Verify: `.github/workflows/deploy-production.yml` exists（55.6 introduced；workflow_dispatch only）
  - Glob: `Glob(".github/workflows/deploy-production.yml")` returns 1

#### Prong 2 — Content Verify（AD-Plan-3）

- [ ] **US-1 content drift check（cost_ledger 真正 default vs plan claim）**
  - Plan claim: `record_llm_call()` uses default `azure_openai/gpt-5.4` constants
  - Grep: `grep -n "azure_openai\|gpt-5.4\|provider:" backend/src/business_domain/cost_ledger/service.py`
  - Drift catalogue if find different defaults / parameter signatures than plan
- [ ] **US-2 content drift check（LoopCompleted last-event proxy）**
  - Plan claim: SLAMetricRecorder 用 LoopCompleted.total_turns / total_tokens last-event
  - Grep: `grep -n "total_turns\|total_tokens\|classify_loop_complexity" backend/src/platform_layer/observability/sla_metric_recorder.py`
  - Drift catalogue if find existing accumulator pattern already
- [ ] **US-3 content drift check（Cat 9 detector Stage 0 only）**
  - Plan claim: 4 detectors are Stage 0 advisory（audit log only, no block）
  - Grep: `grep -rn "stage\|block\|severity" backend/src/agent_harness/guardrails/`
  - Drift catalogue if find Stage 1 already partially wired
- [ ] **US-4 content drift check（deploy-production.yml workflow_dispatch only）**
  - Plan claim: trigger 是 `workflow_dispatch:` only（55.6 introduced state）
  - Grep: `grep -n "on:\|push:\|workflow_dispatch:\|branches:" .github/workflows/deploy-production.yml`
  - Drift catalogue if find push trigger already added between 55.6 and 57.2

#### Prong 3 — Schema Verify（AD-Plan-4-Schema-Grep — folded Sprint 57.1）

- [ ] **US-1 schema drift check（cost_ledger columns）**
  - Plan claim: cost_ledger 目前無 input_tokens / output_tokens 欄位（只有 total_tokens combined）
  - Grep: `grep -A 30 "class CostLedger\|cost_ledger" backend/src/infrastructure/db/models/`
  - Verify migration head version: `ls backend/src/infrastructure/db/migrations/versions/ | sort -V | tail -3` confirms 0016 latest（0017 not yet occupied）
  - Drift catalogue if find input_tokens / output_tokens already exist
- [ ] **US-1 RLS policy check（new column 不破壞 RLS）**
  - Verify: cost_ledger 既有 RLS policy 仍 valid after column add
  - Grep: `grep -A 3 "ENABLE ROW LEVEL SECURITY\|tenant_isolation_cost_ledger" backend/src/infrastructure/db/migrations/versions/0016_*.py`

### 0.3 D-findings catalogue + decision

- [ ] **D1-Dn catalogued in progress.md Day 0 section**
  - Format: `D{N}` ID + Finding + Implication + Cross-reference to plan §Risks（don't silently rewrite plan）
- [ ] **Go/no-go decision recorded**
  - Findings shift scope by ≤ 20% → continue Day 1
  - Findings shift scope by 20-50% → revise plan §Acceptance Criteria + §Workload + re-confirm with user
  - Findings shift scope by > 50% → abort sprint + redraft（per AD-Plan-1）

---

## Day 1 — US-1 Cost Ledger 精度（AD-Cost-Ledger-Token-Split + AD-Cost-Ledger-Provider-Attribution）

### 1.1 Alembic migration 0017

- [ ] **Migration 0017 file create**
  - DoD: `backend/src/infrastructure/db/migrations/versions/0017_cost_ledger_token_split.py` exists
  - Includes: `add_column input_tokens INTEGER NOT NULL DEFAULT 0` + same for output_tokens
  - Backfill: existing rows `input_tokens = total_tokens, output_tokens = 0`（保守 fallback）
  - Down migration: drop columns（保留 total_tokens unchanged）
  - Command: `alembic -c backend/alembic.ini revision --autogenerate -m "0017_cost_ledger_token_split"`
- [ ] **Migration up/down/up cycle clean**
  - DoD: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 三段全 success
  - Verify: schema reflects new columns after final upgrade

### 1.2 CostLedgerService.record_llm_call signature change

- [ ] **service.py 修改 record_llm_call signature**
  - DoD: `input_tokens` / `output_tokens` / `provider` / `model` 改為 required parameter（從 ChatResponse 真實值）
  - Backwards-compat: 保留 `total_tokens` derived from input + output（database constraint or property）
  - Command: `cd backend && python -m mypy src/business_domain/cost_ledger/ --strict`
- [ ] **Chat router observer wires 真實 ChatResponse attributes**
  - File: `backend/src/api/v1/chat/router.py` LoopCompleted observer
  - DoD: `event.usage.prompt_tokens` / `event.usage.completion_tokens` / `event.provider` / `event.model` 從 ChatResponse 直接讀
  - Best-effort failure pattern preserved（observer 失敗 silently log, 不阻塞 main flow）

### 1.3 Tests for US-1

- [ ] **Unit test: input/output token split accuracy**
  - File: `backend/tests/unit/business_domain/cost_ledger/test_token_split.py`
  - 5 tests: split correct / sum equals total / cached subtract / zero-token edge / negative input rejection
- [ ] **Integration test: chat router → cost ledger 真實 provider/model**
  - File: `backend/tests/integration/api/test_cost_ledger_provider_truthful.py`
  - 1 test: full chat flow with mock LLM ChatResponse with non-default provider/model → cost ledger entry 反映真實值

### 1.4 Day 1 quality gates

- [ ] **mypy --strict 0 errors**
- [ ] **flake8 0 violations**
- [ ] **pytest +6 tests pass（5 unit + 1 integration）**
- [ ] **8 V2 lints 8/8 green**
- [ ] **LLM SDK leak 0**

---

## Day 2 — US-2 LoopMetricsAccumulator（AD-Cat10-Cat11-LoopMetricsAccumulator）

### 2.1 LoopMetricsAccumulator class

- [ ] **`_metrics.py` file create with LoopMetricsAccumulator dataclass**
  - File: `backend/src/agent_harness/orchestrator_loop/_metrics.py`
  - Fields: `total_turns / total_tokens / verification_iterations / subagent_dispatched / cumulative_input_tokens / cumulative_output_tokens`
  - Method: `on_event(event: LoopEvent) -> None`（accumulate based on event type）
- [ ] **on_event handles 5 event types**
  - LLMResponded → accumulate input/output tokens + total
  - ToolCallExecuted → no-op（tools 不算 LLM token）
  - VerificationCompleted → increment verification_iterations
  - SubagentDispatched → increment subagent_dispatched
  - LoopCompleted → no-op（accumulator 已完成）

### 2.2 AgentLoop integration

- [ ] **AgentLoop inject accumulator**
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - DoD: `self._metrics = LoopMetricsAccumulator()` in __init__
  - DoD: 每個 yielded event 同時 `self._metrics.on_event(event)`
- [ ] **LoopCompleted payload 改用 accumulator 結果**
  - File: `backend/src/agent_harness/_contracts/events.py`
  - DoD: LoopCompleted 含 `total_turns / total_tokens` 從 accumulator 來
  - Backwards-compat: 既有 LoopCompleted consumers（SLAMetricRecorder 等）payload 仍 valid

### 2.3 Tests for US-2

- [ ] **Unit test: accumulator correctness**
  - File: `backend/tests/unit/agent_harness/orchestrator_loop/test_metrics_accumulator.py`
  - 5 tests: empty / single LLM call / verification correction loop / subagent dispatch count / mixed events
- [ ] **Integration test: multi-turn loop with verification → SLA report 反映真實 cumulative**
  - File: `backend/tests/integration/agent_harness/test_loop_metrics_e2e.py`
  - 1 test: verification correction triggers 2 LLM calls → accumulator total_turns = 2

### 2.4 Day 2 quality gates

- [ ] **mypy --strict 0 errors**
- [ ] **flake8 0 violations**
- [ ] **pytest +6 tests pass（5 unit + 1 integration）**
- [ ] **既有 LoopCompleted consumer regression tests 仍 pass**
- [ ] **8 V2 lints 8/8 green**

---

## Day 3 — US-3 Cat 9 Stage 1 wiring（AD-Cat9-1-WireDetectors）

### 3.1 GuardrailEngine Stage 1 method

- [ ] **GuardrailEngine.check_pre_tool() Stage 1 method**
  - File: `backend/src/agent_harness/guardrails/engine.py`
  - DoD: 新 method 接收 `tool_call: ToolCall + state: LoopState`；invoke 4 detector chain；return list of `DetectorResult`
  - Severity threshold configurable（default HIGH only triggers block）
- [ ] **AgentLoop pre-tool gate invoke**
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - DoD: 每個 tool_call 在 execute 前 invoke check_pre_tool
  - Detected with severity >= block_threshold → emit GuardrailTriggered SSE event + audit log + skip tool execution

### 3.2 Backwards-compat（Stage 0 advisory tests preserve）

- [ ] **Stage 0 advisory tests 仍 pass**
  - DoD: 既有 detector unit tests（200-case PII fixture / jailbreak fixture）regression-free
  - Command: `cd backend && python -m pytest tests/unit/agent_harness/guardrails/ -v`

### 3.3 Tests for US-3

- [ ] **Stage 1 block unit tests**
  - File: `backend/tests/unit/agent_harness/guardrails/test_stage1_block.py`
  - 4 tests per detector × 4 detectors = ~12-16 tests（PII block / Jailbreak block / SecretsLeak block / RoleConfusion block + each has below-threshold pass）
  - Conservative count: 4 tests minimum（1 per detector showing block path）
- [ ] **Integration test: chat router pre-tool block scenario**
  - File: `backend/tests/integration/api/test_chat_pre_tool_block.py`
  - 4 tests: 1 per detector triggering pre-tool block + GuardrailTriggered SSE event verify

### 3.4 Day 3 quality gates

- [ ] **mypy --strict 0 errors**
- [ ] **flake8 0 violations**
- [ ] **pytest +8 tests pass（4 unit + 4 integration minimum）**
- [ ] **既有 Cat 9 advisory tests 仍 pass**
- [ ] **8 V2 lints 8/8 green**

---

## Day 4 — US-4 + US-5 + closeout

### 4.1 US-4: deploy-production.yml 啟用（AD-CI-6）

- [ ] **5-point criteria verify**
  - 1. 5 active CI checks（Lint+Build / Lint+Test+Pg16 / Backend E2E / Frontend E2E chromium / v2-lints）30-day stable history
  - 2. enforce_admins=true confirmed in branch protection
  - 3. Production runner 配置（GitHub Actions production environment with secrets）
  - 4. Rollback playbook ≥ 1 page documented at `docs/13-deployment/rollback-playbook.md`（confirm exists or create）
  - 5. Staging-smoke job design 確認
- [ ] **deploy-production.yml trigger 改 push-to-main + workflow_dispatch dual**
  - File: `.github/workflows/deploy-production.yml`
  - DoD: `on: push: branches: [main]` + `workflow_dispatch:` 共存
- [ ] **Staging-smoke job 新增 pre-production gate**
  - DoD: `staging-smoke` job in deploy-production.yml；deploy job `needs: staging-smoke`
- [ ] **Branch protection 補入 deploy-production / staging-smoke required check**
  - Command: `gh api -X PATCH repos/{owner}/{repo}/branches/main/protection/required_status_checks --field contexts[]=staging-smoke`
- [ ] **Dry-run + production push verify**
  - 1 dry-run on test branch with deploy override
  - 1 production push（after Day 4 merge）verify trigger

### 4.2 US-5: 11+1 範疇 alignment audit

- [ ] **12 範疇 grep one-by-one**
  - Cat 1 Orchestrator Loop: spec ABC / public API / events vs `agent_harness/orchestrator_loop/`
  - Cat 2 Tool Layer: spec ToolSpec / ToolRegistry / ToolExecutor vs `agent_harness/tools/`
  - Cat 3 Memory: spec 5 layers vs `agent_harness/memory/`
  - Cat 4 Context Mgmt: spec Compactor ABC vs `agent_harness/context_mgmt/`
  - Cat 5 Prompt Construction: spec PromptBuilder vs `agent_harness/prompt_builder/`
  - Cat 6 Output Parsing: spec OutputParser vs `agent_harness/output_parser/`
  - Cat 7 State Mgmt: spec Reducer / Checkpointer vs `agent_harness/state_mgmt/`
  - Cat 8 Error Handling: spec ErrorPolicy / RetryPolicyMatrix vs `agent_harness/error_handling/`
  - Cat 9 Guardrails: spec Detector / Tripwire vs `agent_harness/guardrails/`
  - Cat 10 Verification: spec Verifier / VerifierRegistry vs `agent_harness/verification/`
  - Cat 11 Subagent: spec 4 modes（Fork/Teammate/Handoff/AsTool）vs `agent_harness/subagent/`
  - Cat 12 Observability: spec Tracer / TraceContext / MetricEvent vs `agent_harness/observability/`
- [ ] **D-findings catalogued in retrospective Q3**
  - Format: `Cat-N-Drift-{description}` for each drift
  - 若 drift > 3 條 → log AD-Cat-Alignment-Drift-1 process AD（後續 audit cycle 處理）

### 4.3 Closeout ceremony

- [ ] **progress.md final entry**
  - Today's accomplishments + remaining + notes
  - Calibration: `actual_total_hr / committed_total_hr` ratio
- [ ] **retrospective.md create**
  - Q1: Did well
  - Q2: Improve next sprint + calibration multiplier accuracy
  - Q3: 11+1 alignment audit D-findings list
  - Q4: New ADs logged this sprint
  - Q5: Phase 57+ next-sprint candidates（不寫 plan task detail）
- [ ] **PR open + CI green + squash merge**
  - PR title: `Sprint 57.2 — Phase 57+ Audit Cycle Lvl 2: Carryover ADs Closure + 11+1 Alignment`
  - Per solo-dev policy: enforce_admins=true / review_count=0 / 5 active CI checks required
- [ ] **Closeout PR（CLAUDE.md / SITUATION-V2 sync）**
  - Latest Sprint = 57.2
  - main HEAD update
  - Last Updated audit-cycle entry
- [ ] **Memory snapshot update（MEMORY.md + project_phase57_2_audit_cycle_lvl2.md）**
- [ ] **Cleanup branches**

### 4.4 Day 4 quality gates

- [ ] **pytest baseline 1557 → ≥ 1567 confirmed**
- [ ] **mypy --strict 0 errors**
- [ ] **8 V2 lints 8/8 green**
- [ ] **LLM SDK leak 0**
- [ ] **Frontend baseline unchanged（此 sprint 不動 frontend）**

---

## Definition of Done（mirror plan §Definition of Done）

- [ ] 5 carryover ADs all closed（AD-Cost-Ledger-Token-Split / Provider-Attribution / Cat10-Cat11-LoopMetricsAccumulator / Cat9-1-WireDetectors / CI-6）
- [ ] US-5 11+1 alignment audit 完成 + D-findings catalogued
- [ ] pytest 1557 → ≥ 1567
- [ ] mypy --strict 0 errors
- [ ] 8 V2 lints 8/8 green
- [ ] LLM SDK leak 0
- [ ] Day 0 三-prong verify D-findings catalogued in progress.md
- [ ] Retrospective Q1-Q5 written
- [ ] Calibration ratio computed + 13-sprint window stats updated
- [ ] PR open + CI green + squash merge to main
- [ ] Closeout PR + memory snapshot
- [ ] Phase 57+ next-sprint candidates Q5 列出（rolling planning 紀律 — 不寫 plan task detail）

---

## Reference

- [sprint-57-2-plan.md](./sprint-57-2-plan.md) — Authority document
- [sprint-workflow.md](../../../../.claude/rules/sprint-workflow.md) §Step 2.5（三-prong verify）/ §Workload Calibration / §Common Risk Classes
- [anti-patterns-checklist.md](../../../../.claude/rules/anti-patterns-checklist.md) AP-3 / AP-9
- [01-eleven-categories-spec.md](../01-eleven-categories-spec.md) — 11+1 範疇 alignment baseline
- [17-cross-category-interfaces.md](../17-cross-category-interfaces.md) §Cat 8 / 9 / 10 / 11 / 12 contracts
