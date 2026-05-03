# Sprint 53.2 — Error Handling Checklist

**Plan**: [sprint-53-2-plan.md](./sprint-53-2-plan.md)
**Branch**: `feature/sprint-53-2-error-handling` (off main `aaa3dd75`)
**Duration**: 5 days (Day 0-4 standard layout)

---

## Day 0 — Setup + Cat 8 Baseline + 53.x Carryover Reproduce (est. 3-4 hours)

### 0.1 Branch + plan + checklist commit
- [x] **Verify on main + clean working tree** _(HEAD aaa3dd75; only untracked phase-53-2 docs dir)_
- [x] **Verify branch protection still enforced** _(enforce_admins=true / review_count=1 / 8 status_checks)_
- [x] **Create feature branch** _(feature/sprint-53-2-error-handling)_
- [x] **Verify phase folder structure exists** _(planning + execution dirs created)_
- [x] **Commit Day 0 docs (plan + checklist)** _(commit 6ed1583d, 1599 lines)_

### 0.2 GitHub issues 建立
- [x] **Create 7 GitHub issues #40-46 + #47** _(8 total: #40-47; all sprint-53-2 labelled)_
- [x] **Verify #38 status** _(was auto-CLOSED by 53.1 PR #39 ref; xfail still in code; **REOPENED** 2026-05-03 to track US-7)_

### 0.3 Cat 8 既有結構 + baseline 記錄
- [x] **Cat 8 stub structure inventory** _(__init__.py + _abc.py + README.md ONLY; NO _contracts/errors.py; NO tests dir — Day 1 creates both)_
- [x] **Cat 8 既有 tests dir** _(missing — to be created Day 1)_
- [x] **Reference points: 8 files (plan estimated 17; -53% drift acceptable)**
- [x] **pytest baseline** _(596 passed / 4 skipped / 1 xfailed in 21.68s)_
- [x] **mypy baseline** _(202 src files clean)_
- [x] **LLM SDK leak baseline** _(0 violations)_
- [x] **6 V2 lint scripts baseline** _(ap1_pipeline_disguise / cross_category_import / duplicate_dataclass / llm_sdk_leak / promptbuilder_usage / sync_callback — all green)_
- [x] **CI Pipeline workflow baseline (AD-CI-1 reproduce)** _(5/5 last main push events FAILED since d4ba89ef 2026-05-01)_

### 0.4 #38 reproduce
- [x] **Run flaky test_router in isolation** _(2 passed / 1 xpassed — XPASS in isolation)_
- [x] **Run flaky test in full suite** _(596 passed / 1 xfailed — confirmed order-dependent flakiness)_
- [x] **Capture suspect leak source** _(isolation XPASS / full-suite xfailed → fixture/registry leak from upstream tests; Day 4 will narrow down)_

### 0.5 AD-CI-1 診斷
- [x] **Inspect last failed CI Pipeline run** _(run id 25252677119; failing job=Build Docker Images, step=Build Backend Docker image)_
- [x] **Identify root cause** _(error: "failed to read dockerfile: open Dockerfile: no such file or directory" — backend/Dockerfile missing; per issue #31 deferred)_
- [x] **Fix strategy decided** _(Day 4 US-8: conditional skip "Build Docker Images" job in ci.yml until #31 lands real V2 Dockerfile; do NOT write Dockerfile in 53.2)_

### 0.6 53.1 closeout bookkeeping branch verify
- [x] **Fetch closeout branch** _(HEAD 41aec40f; 2 commits ahead of main)_
- [x] **Verify diff content preview** _(2 files / +14 / -8 lines: retrospective.md + checklist.md docs-only edits; no src/ changes)_

### 0.7 Day 0 progress.md
- [x] **Day 0 progress.md** _(written at docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-error-handling/progress.md)_

---

## Day 1 — US-1 ErrorPolicy + US-2 RetryPolicy + ErrorRetried Event (est. 6-7 hours)

### 1.1 Update _contracts/errors.py
- [x] **Add new exception classes** _(created `_contracts/errors.py` with ErrorContext + AuthenticationError + MissingDataError + ToolExecutionError; re-exported via _contracts/__init__.py)_

### 1.2 Create policy.py (renamed from classifier.py per stub)
- [x] **Write `DefaultErrorPolicy` class** _(implements existing `ErrorPolicy` ABC: classify + should_retry + backoff_seconds; registry pattern with MRO walk; stdlib-only defaults)_
- [x] **Update `error_handling/__init__.py`** _(re-exported DefaultErrorPolicy)_

### 1.3 Create test_policy.py
- [x] **Create test_policy.py** _(19 tests pass: 10 classify + 4 should_retry + 4 backoff_seconds + 1 import smoke; covers all 4 ErrorClass cases + MRO + register)_

### 1.4 US-2 ErrorRetried event
- [x] **`ErrorRetried` already exists in stub `_contracts/events.py`** _(fields: attempt / error_class / backoff_ms — sufficient for 53.2; no code change needed)_

### 1.5 US-2 Create retry.py
- [x] **Write `RetryConfig` + `RetryPolicyMatrix` classes** _(layer-2 separation: policy.py owns "should retry?", retry.py owns "with what config?"; from_yaml + compute_backoff helper; mypy strict clean)_

### 1.6 Create retry_policies.yaml
- [x] **Create config file** _(`backend/config/retry_policies.yaml` with 4 ErrorClass defaults + salesforce_query per-tool override)_

### 1.7 Create test_retry.py
- [x] **Create test_retry.py** _(15 tests pass: 4 defaults + 3 resolution + 3 from_yaml + 5 compute_backoff)_

### 1.8 Update __init__.py
- [x] **Re-export RetryConfig + RetryPolicyMatrix + compute_backoff** _(exported via `agent_harness.error_handling`)_

### 1.9 Day 1 sanity checks
- [x] **mypy strict 仍 clean** _(205 src files clean, was 202 → +3 new files: errors.py + policy.py + retry.py)_
- [x] **All 6 V2 lint scripts 仍綠** _(ap1 + cross_category + duplicate_dataclass + llm_sdk_leak + promptbuilder + sync_callback all green)_
- [x] **Full pytest 不退步** _(596 → **630 passed** / 4 skip / 1 xfail (#38) / 0 fail; +34 new tests)_
- [x] **Cat 8 coverage Day 1 partial** _(`__init__` + `_abc` + `policy` + `retry` = **100%** coverage; 103/103 stmts; target ≥ 80%)_
- [x] **black + isort + flake8 + ruff** _(all green; `pytest` unused import removed from test_policy.py)_

### 1.10 Day 1 commit + push + verify CI
- [x] **Commit US-1 + US-2** _(commit f87c4a2f, +875/-88 lines, 11 files)_
- [x] **Push to feature branch** _(74fce70d → f87c4a2f)_
- [x] **CI green on this branch** _(Backend CI success on 2f565b60 after isort fix; other 7 workflows trigger on PR open at Day 4)_
- [x] **Close GitHub issues #40 + #41** _(both closed with verification comments)_

### 1.11 Day 1 progress.md update
- [x] **Append Day 1 progress.md** _(Day 1 section written with drift table + sanity matrix)_

---

## Day 2 — US-3 CircuitBreaker + US-4 ErrorBudget (est. 6-7 hours)

### 2.1 Create circuit_breaker.py
- [ ] **Write `CircuitState` enum + `CircuitBreakerStats` + `ProviderCircuitBreaker` class**
  - File: `backend/src/agent_harness/error_handling/circuit_breaker.py`
  - File header per convention
  - `CircuitState`: CLOSED / OPEN / HALF_OPEN
  - `ProviderCircuitBreaker(provider, threshold=5, recovery_timeout_seconds=60.0, half_open_max_calls=1)`
  - `is_open() -> bool` async with state-transition logic
  - `record_success() / record_failure()` async with asyncio.Lock
  - `CircuitOpenError(Exception)` class
  - DoD: mypy strict pass

### 2.2 Create test_circuit_breaker.py
- [ ] **Create test_circuit_breaker.py**
  - File: `backend/tests/unit/agent_harness/error_handling/test_circuit_breaker.py`
  - Tests:
    - `test_initial_state_closed`
    - `test_consecutive_failures_open_circuit` (threshold reached)
    - `test_open_to_half_open_after_recovery_timeout`
    - `test_half_open_success_closes_circuit`
    - `test_half_open_failure_reopens_circuit`
    - `test_record_success_resets_consecutive_failures`
    - `test_concurrent_record_under_lock` (asyncio.gather × 10)
    - `test_per_provider_isolation` (azure_openai vs anthropic)
  - DoD: ≥ 8 tests pass

### 2.3 Adapter 整合
- [ ] **Update `adapters/_base/chat_client.py`**
  - File: `backend/src/adapters/_base/chat_client.py`
  - Add `circuit_breaker: ProviderCircuitBreaker | None = None` to `__init__`
  - Pre-call check: `if self._circuit_breaker and await self._circuit_breaker.is_open(): raise CircuitOpenError(...)`
  - Wrap `_do_chat`: success → record_success；exception → record_failure；re-raise
  - DoD: 既有 chat_client tests 不退步
- [ ] **Update `adapters/azure_openai/adapter.py`**
  - DI hook：建構時可注入 circuit breaker
  - DoD: existing adapter tests pass

### 2.4 Adapter integration test
- [ ] **Create test_circuit_breaker_integration.py**
  - File: `backend/tests/integration/adapters/test_circuit_breaker_integration.py`
  - Tests:
    - `test_adapter_succeeds_normally_under_closed_circuit`
    - `test_adapter_records_failure_on_provider_exception`
    - `test_adapter_raises_circuit_open_after_threshold_failures`
    - `test_adapter_recovers_after_timeout`
  - DoD: ≥ 4 tests pass

### 2.5 Create budget.py
- [ ] **Write `BudgetStore` Protocol + `TenantErrorBudget` class**
  - File: `backend/src/agent_harness/error_handling/budget.py`
  - File header per convention
  - `BudgetStore(Protocol)`: `increment(key, ttl_seconds) -> int` / `get(key) -> int`
  - `TenantErrorBudget(store, max_per_day=1000, max_per_month=20000)`
  - `record(tenant_id, error_category)` async
  - `is_exceeded(tenant_id) -> tuple[bool, str | None]` async
  - 跳過 UNEXPECTED 不計入 budget（bug 不應計）
  - DoD: mypy strict pass

### 2.6 Create _redis_store.py
- [ ] **Write `RedisBudgetStore` impl**
  - File: `backend/src/agent_harness/error_handling/_redis_store.py`
  - 使用 `redis.asyncio` (cross-platform `# type: ignore` per code-quality.md)
  - `INCR` + `EXPIRE` 原子操作
  - DoD: type-safe；importable on both Linux + Windows CI

### 2.7 Create error_budgets.yaml
- [ ] **Create config file**
  - File: `backend/config/error_budgets.yaml`
  - defaults: max_per_day=1000, max_per_month=20000
  - per_tenant override 範例（一個 tenant 自訂上限）
  - DoD: YAML parseable

### 2.8 Create test_budget.py
- [ ] **Create test_budget.py**
  - File: `backend/tests/unit/agent_harness/error_handling/test_budget.py`
  - Tests with `fakeredis` or in-memory mock:
    - `test_record_increments_day_and_month_counters`
    - `test_unexpected_skipped_in_budget` (bug 不計入)
    - `test_is_exceeded_when_day_limit_hit`
    - `test_is_exceeded_when_month_limit_hit`
    - `test_per_tenant_isolation` (tenant_a 超支 → tenant_b 未受影響)
    - `test_ttl_resets_at_day_boundary` (mock time)
  - DoD: ≥ 6 tests pass

### 2.9 Update __init__.py
- [ ] **Re-export ProviderCircuitBreaker + CircuitOpenError + TenantErrorBudget**
  - DoD: imports work

### 2.10 Day 2 sanity checks
- [ ] **mypy strict 仍 clean**
- [ ] **All 6 V2 lint scripts 仍綠**
- [ ] **Full pytest 不退步**
  - DoD: ≥ 631 PASS（613 + ≥ 18 new tests）/ 1 xfail / 4 skip / 0 fail
- [ ] **Cat 8 coverage Day 2 partial**
  - DoD: ≥ 80%

### 2.11 Day 2 commit + push + verify CI
- [ ] **Commit US-3 + US-4**
  - Message: `feat(error-handling, sprint-53-2): US-3 CircuitBreaker per-provider + US-4 ErrorBudget per-tenant + adapter integration`
  - **Verify branch before commit**
- [ ] **Push + verify 8 workflow CI green**
- [ ] **Close GitHub issues #42 + #43**

### 2.12 Day 2 progress.md update
- [ ] **Append Day 2 progress.md**

---

## Day 3 — US-5 ErrorTerminator + US-6 AgentLoop Integration (上半) (est. 6-7 hours)

### 3.1 Add LoopTerminated event
- [ ] **Add `LoopTerminated` to `_contracts/events.py`**
  - frozen dataclass: reason / detail / last_state_version
  - DoD: importable

### 3.2 Create terminator.py
- [ ] **Write `TerminationReason` enum + `TerminationDecision` + `ErrorTerminator` class**
  - File: `backend/src/agent_harness/error_handling/terminator.py`
  - File header per convention
  - `TerminationReason`: BUDGET_EXCEEDED / CIRCUIT_OPEN / FATAL_EXCEPTION / MAX_RETRIES_EXHAUSTED
  - **明確 NOT 包含 Tripwire reasons**（per 17.md §6 邊界裁定）
  - `should_terminate(error, error_category, context, tenant_id) -> TerminationDecision`
  - DoD: mypy strict pass

### 3.3 Create test_terminator.py
- [ ] **Create test_terminator.py**
  - File: `backend/tests/unit/agent_harness/error_handling/test_terminator.py`
  - Tests:
    - `test_should_terminate_on_budget_exceeded`
    - `test_should_terminate_on_circuit_open`
    - `test_should_terminate_on_fatal_unexpected`
    - `test_should_terminate_on_max_retries_exhausted`
    - `test_should_not_terminate_on_transient_within_budget`
    - `test_should_not_terminate_on_llm_recoverable`
  - DoD: ≥ 6 tests pass

### 3.4 Cat 8 vs Cat 9 邊界守門
- [ ] **Grep `Tripwire` 在 error_handling/ 必須 = 0 hits**
  - `grep -rn "Tripwire\|tripwire" backend/src/agent_harness/error_handling/`
  - DoD: 0 hits（per 17.md §6 邊界裁定）
- [ ] **Update __init__.py**
  - Re-export `ErrorTerminator` + `TerminationReason` + `TerminationDecision`

### 3.5 US-6 AgentLoop integration (上半 — opt-in deps + classify hook)
- [ ] **Add Cat 8 deps to `AgentLoop.__init__`**
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - Add optional kwargs: `error_classifier` / `retry_policy` / `circuit_breakers` / `error_budget` / `error_terminator`
  - All default `None`（opt-in pattern；同 53.1 Reducer/Checkpointer pattern）
  - DoD: 既有 51.x + 53.1 baseline tests 不退步
- [ ] **Implement `_execute_tool_with_error_handling` helper**
  - 簽名：`async def _execute_tool_with_error_handling(self, tool_call, state, trace_context) -> tuple[LoopState, ToolResult | None]`
  - 邏輯：
    - while True 重試 loop
    - try execute → 成功 return
    - except → classify → record budget → check terminator
    - LLM_RECOVERABLE: 構造 error ToolResult → return（被 caller append to messages）
    - TRANSIENT: get retry_policy → backoff → retry
    - USER_FIXABLE: bubble (TODO Phase 53.4 HITL)
    - UNEXPECTED: bubble
    - terminator.should_terminate=True → checkpoint + emit LoopTerminated → return signal
  - DoD: mypy strict pass

### 3.6 Day 3 commit + push (中間 push 取得 CI 反饋)
- [ ] **Commit US-5 + US-6 partial**
  - Stage: `git add backend/src/agent_harness/error_handling/terminator.py backend/src/agent_harness/_contracts/events.py backend/src/agent_harness/orchestrator_loop/loop.py backend/tests/unit/agent_harness/error_handling/`
  - Message: `feat(error-handling, sprint-53-2): US-5 ErrorTerminator + US-6 AgentLoop deps integration (partial)`
  - **Verify branch before commit**
- [ ] **Push + verify 8 workflow CI green**
  - `gh run list --branch feature/sprint-53-2-error-handling --limit 3`
- [ ] **Close GitHub issue #44**

### 3.7 Day 3 sanity
- [ ] **mypy + 6 V2 lints + pytest 不退步**
- [ ] **51.x + 53.1 baseline preserved**
  - 跑 Cat 1 + Cat 7 既有 integration test suite
  - DoD: 全綠

### 3.8 Day 3 progress.md update
- [ ] **Append Day 3 progress.md**
  - Sections: US-5 ✅ / US-6 partial ✅ (deps + helper) / Remaining for Day 4 (US-6 lower half + US-7 + US-8 + US-9 + retro + PR)

---

## Day 4 — US-6 Lower Half + #38 + AD-CI-1 + 53.1 Closeout Bundle + Retrospective + PR (est. 7-8 hours)

### 4.1 US-6 AgentLoop integration (下半 — wire helper into main loop)
- [ ] **Replace direct tool execution with `_execute_tool_with_error_handling`**
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - 在主 loop 內 tool execution 點呼叫 helper
  - 處理 helper 返回的 `ToolResult | None`：None 代表 terminator 已 fire → break loop
  - DoD: 51.x + 53.1 baseline tests 不退步

### 4.2 US-6 Integration tests
- [ ] **Create test_loop_error_handling.py**
  - File: `backend/tests/integration/agent_harness/orchestrator_loop/test_loop_error_handling.py`
  - Tests:
    - `test_llm_recoverable_error_injects_error_result_into_messages`
    - `test_transient_error_retries_with_backoff_then_succeeds`
    - `test_max_retries_exhausted_triggers_terminator`
    - `test_circuit_open_triggers_terminator`
    - `test_budget_exceeded_triggers_terminator`
    - `test_fatal_unexpected_triggers_terminator_with_checkpoint`
  - DoD: ≥ 6 integration tests pass

### 4.3 US-6 commit + push + verify
- [ ] **Commit US-6 final**
  - Message: `feat(error-handling, sprint-53-2): US-6 AgentLoop tool-error chain (full integration)`
  - **Verify branch before commit**
- [ ] **Push + verify 8 workflow CI green**
- [ ] **Close GitHub issue #45**

### 4.4 US-7 #38 flaky test_router fix (AD-Cat7-2)
- [ ] **Apply fixture / DI registry fix per Day 0 reproduce findings**
  - 推測 fix 1: conftest.py 加 autouse fixture reset DI registry between tests
  - 推測 fix 2: `tests/unit/api/v1/chat/test_router.py` fixtures scope 改 function（從 session/module）
  - 推測 fix 3: 新 Cat 8 deps (RetryPolicy / CircuitBreaker / ErrorBudget) 確保 per-test instance（避免 global state leak）
  - DoD: fix 落地；mypy clean
- [ ] **Remove xfail decorator**
  - File: `backend/tests/unit/api/v1/chat/test_router.py::TestMultiTenantIsolation`
  - 移除 `@pytest.mark.xfail(reason="...", strict=False)` decorator + reason
  - DoD: 無 xfail decorator
- [ ] **Verify in isolation + full suite + random order**
  - `cd backend && python -m pytest tests/unit/api/v1/chat/test_router.py::TestMultiTenantIsolation -v`
  - `cd backend && python -m pytest tests/ --tb=no -q 2>&1 | tail -5`
  - `cd backend && python -m pytest tests/ --random-order 2>&1 | tail -5`（若已裝；否則加 to dev extras carryover）
  - DoD: 三種 run 都 pass；無 xfail
- [ ] **Close GitHub issue #38**
  - `gh issue close 38 --comment "Resolved by commit <hash>. Verified: full suite + random order pass."`

### 4.5 US-8 AD-CI-1 CI Pipeline push-to-main fix
- [ ] **Apply fix per Day 0 診斷 findings**
  - 推測 fix 1: ci.yml 修 push trigger 對齊 PR triggers
  - 推測 fix 2: alembic head conflict 修
  - 推測 fix 3: 加 setup script 補齊 push event 缺項
  - DoD: ci.yml / setup script 落地
- [ ] **Push to feature branch + verify ci.yml on push event green**
  - `gh run list --branch feature/sprint-53-2-error-handling --workflow ci.yml --limit 3`
  - DoD: latest run conclusion = success
- [ ] **Close GitHub issue #46**

### 4.6 US-9 53.1 closeout bookkeeping bundle
- [ ] **Merge `docs/sprint-53-1-closeout-bookkeeping` into 53.2 feature branch**
  - `git fetch origin docs/sprint-53-1-closeout-bookkeeping`
  - `git merge --no-ff origin/docs/sprint-53-1-closeout-bookkeeping -m "chore(closeout, sprint-53-1): bundle bookkeeping commits into 53.2"`
  - 或 cherry-pick：`git cherry-pick <commit-1-sha> <commit-2-sha>`
  - DoD: merge 無衝突；2 commits 在 feature branch
- [ ] **Verify content + push**
  - `git log --oneline -10`
  - `git push origin feature/sprint-53-2-error-handling`
  - DoD: closeout commits 可見；CI 綠
- [ ] **Close GitHub issue #47**

### 4.7 Sprint final verification
- [ ] **All 8 active CI workflow green on feature branch latest**
  - `gh run list --branch feature/sprint-53-2-error-handling --limit 8`
  - DoD: 全綠 on latest commit
- [ ] **pytest final baseline**
  - `cd backend && python -m pytest --tb=no -q 2>&1 | tail -5`
  - DoD: ≥ 615 PASS / 0 xfail（#38 已 reactivate）/ 4 skip / 0 fail
- [ ] **Cat 8 coverage final**
  - `cd backend && python -m pytest tests/ --cov=src/agent_harness/error_handling --cov-report=term 2>&1 | tail -10`
  - DoD: ≥ 80%
- [ ] **mypy strict + LLM SDK leak final**
  - DoD: 205+ src clean；LLM SDK leak = 0；6 V2 lints + black/isort/flake8/ruff green
- [ ] **Cat 8 vs Cat 9 邊界 grep evidence**
  - `grep -rn "Tripwire\|tripwire" backend/src/agent_harness/error_handling/`
  - DoD: 0 hits（per 17.md §6）
- [ ] **ErrorClassifier 真在 AgentLoop 用**
  - `grep -rn "error_classifier\.classify" backend/src/agent_harness/orchestrator_loop/`
  - DoD: ≥ 1 hit
- [ ] **CircuitBreaker 真在 Adapter 用**
  - `grep -rn "circuit_breaker\.is_open\|record_success\|record_failure" backend/src/adapters/`
  - DoD: ≥ 3 hits
- [ ] **ErrorTerminator 真在 AgentLoop 用**
  - `grep -rn "error_terminator\.should_terminate" backend/src/agent_harness/orchestrator_loop/`
  - DoD: ≥ 1 hit
- [ ] **AD-CI-1 fix 驗證**
  - `gh run list --workflow ci.yml --branch feature/sprint-53-2-error-handling --limit 3 --json conclusion`
  - DoD: 最近 3 run 全綠

### 4.8 Day 4 retrospective.md
- [ ] **Write retrospective.md**
  - Path: `docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-error-handling/retrospective.md`
  - 6 必答條 (per plan §Retrospective 必答)：
    1. 每個 US 真清了嗎？commit + verification + 8 active CI run id
    2. 跨切面紀律：admin-merge count（=0）/ temp-relax count（=0）/ Cat 8 coverage / Cat 8 vs Cat 9 grep evidence
    3. 砍 scope？（如 #38 / AD-CI-1 / closeout bundle 部分未解）
    4. GitHub issues #40-46 + #47 + #38 status table
    5. Audit Debt 累積？（如 ErrorBudget tenant override / Redis HA / per-tool circuit breaker discussion 等）
    6. 主流量整合驗收（ErrorClassifier 真用？RetryPolicy 真用？CircuitBreaker 在 Adapter 真接入？ErrorBudget 真用？ErrorTerminator 真用？LLM-recoverable 回注真實作？Cat 8 vs Cat 9 grep ＝ 0？coverage 真 ≥ 80%？）
  - DoD: 6 條全答 + 對齊 53.1 retrospective 結構

### 4.9 PR open + closeout
- [ ] **Push final commits**
  - `git push origin feature/sprint-53-2-error-handling`
- [ ] **Verify final CI green**
  - 8 workflow 全綠 on latest commit
- [ ] **Open PR**
  - Title: `feat(error-handling, sprint-53-2): Cat 8 Error Handling — ErrorClassifier + RetryPolicy + CircuitBreaker + ErrorBudget + ErrorTerminator + AgentLoop integration + #38 fix + AD-CI-1 fix + 53.1 closeout bundle`
  - Body 含：
    - Summary: 9 US ✅ + Cat 8 Level 4 達成 + #38 closed + AD-CI-1 closed + 53.1 closeout bundled
    - Each US verification 證據 (workflow run id + status)
    - GitHub issues #40-46 + #47 + #38 close URLs
    - Cat 8 coverage 數字
    - Cat 8 vs Cat 9 邊界 grep evidence (`Tripwire` in `error_handling/` = 0)
    - 53.1 closeout bundle 確認（2 commits merged）
    - Diff stat
  - DoD: PR opened；CI runs triggered
- [ ] **Wait for review approval (per branch protection)**
  - User reviews PR
  - DoD: 1 approval given (per protection rule required_approving_review_count=1)
- [ ] **Normal merge (NOT admin override, NOT temp-relax bootstrap)**
  - `gh pr merge <id> --merge` (or squash per project convention)
  - DoD: merge commit on main；branch protection enforce_admins=true 自動強制；無 bypass；**zero temp-relax**
- [ ] **Verify post-merge main CI green**
  - `gh run list --branch main --limit 8` 等 ~5 min
  - 8 workflow 全綠 on `main` HEAD
  - DoD: progress.md + retrospective.md §Q1 補上 main HEAD 的 run id；AD-CI-1 修復確認
- [ ] **Update memory**
  - V2 milestone: 14/22 sprints (64%)
  - Cat 8 Level 4 達成
  - phase 53.2 完成
  - #38 closure status
  - AD-CI-1 closure status
  - 53.1 closeout bookkeeping bundled

### 4.10 Cleanup
- [ ] **Delete local feature branch**
  - `git checkout main && git pull && git branch -d feature/sprint-53-2-error-handling`
  - DoD: branch removed local
- [ ] **Delete remote feature branch (if not auto-deleted)**
  - `git push origin --delete feature/sprint-53-2-error-handling`
- [ ] **Delete remote `docs/sprint-53-1-closeout-bookkeeping` branch**
  - `git push origin --delete docs/sprint-53-1-closeout-bookkeeping`
  - DoD: 53.1 closeout branch 已 cleanup（內容已 bundle 進 main）
- [ ] **Update `claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-20260501.md` if applicable**
  - Mark AD-Cat7-2 + AD-CI-1 closed by 53.2
  - DoD: §10 table updated（如有對應 entry）

---

## Verification Summary（Day 4 final 必填）

| Item | Status | Evidence |
|------|--------|----------|
| US-1 ErrorClassifier concrete impl | ⬜ | commit hash + coverage % |
| US-2 RetryPolicy matrix + ErrorRetried event | ⬜ | commit hash + YAML loaded test |
| US-3 CircuitBreaker per-provider | ⬜ | commit hash + adapter integration test pass |
| US-4 ErrorBudget per-tenant | ⬜ | commit hash + multi-tenant isolation test |
| US-5 ErrorTerminator | ⬜ | commit hash + 4 termination reasons unit tests |
| US-6 AgentLoop integration | ⬜ | grep error_classifier.classify ≥ 1 hit + integration test scenarios pass |
| US-7 #38 flaky test_router fix | ⬜ | xfail removed + random-order pass × 3 |
| US-8 AD-CI-1 CI Pipeline fix | ⬜ | ci.yml on push event green on main HEAD |
| US-9 53.1 closeout bookkeeping bundle | ⬜ | 2 commits merged + remote branch deleted |
| 8 active CI workflow green on main HEAD | ⬜ | 8 run ids |
| Cat 8 coverage ≥ 80% | ⬜ | pytest --cov output |
| pytest ≥ 615 PASS / 0 xfail / 0 fail | ⬜ | counts |
| mypy 205+ src clean | ⬜ | tail output |
| LLM SDK leak = 0 | ⬜ | tail output |
| 6 V2 lint scripts green | ⬜ | each exit 0 |
| Cat 8 vs Cat 9 邊界 (Tripwire in error_handling/) | ⬜ | grep = 0 hits |
| ErrorClassifier 真在 AgentLoop 用 | ⬜ | grep evidence |
| CircuitBreaker 真在 Adapter 用 | ⬜ | grep evidence (≥ 3 hits) |
| ErrorTerminator 真在 AgentLoop 用 | ⬜ | grep evidence |
| Sprint 53.2 PR normal merge (no admin, no temp-relax) | ⬜ | merge commit hash + protection status |
| V2 milestone 14/22 (64%) | ⬜ | memory + retrospective updated |

---

**權威排序**：本 checklist 對齊 [sprint-53-2-plan.md](./sprint-53-2-plan.md) Acceptance Criteria + Retrospective 必答 6 條。任何 Day 順序變動 / scope 砍必須在 progress.md + retrospective.md 透明列出（per 53.1 closeout 教訓 — branch protection enforce_admins=true 持續強制；本 sprint 必須 zero temp-relax）。
