# Sprint 53.3 — Guardrails 核心 Checklist

**Plan**: [sprint-53-3-plan.md](./sprint-53-3-plan.md)
**Branch**: `feature/sprint-53-3-guardrails` (off main `149de254`)
**Duration**: 5 days (Day 0-4 standard layout)

---

## Day 0 — Setup + Cat 9 Baseline + Cat 8 Carryover Prep (est. 3-4 hours)

### 0.1 Branch + plan + checklist commit
- [x] **Verify on main + clean working tree** _(HEAD 149de254; status clean)_
- [x] **Verify branch protection still enforced** _(enforce_admins=true / review_count=0 solo-dev / 4 checks: Lint+Type Check+Test (PG16) + Backend E2E + E2E Summary + v2-lints)_
- [x] **Create feature branch** _(feature/sprint-53-3-guardrails created and tracking origin)_
- [x] **Verify phase folder structure exists** _(planning + execution dirs both created)_
- [x] **Commit Day 0 docs (plan + checklist)** _(commit `dab68b8c`, +1707 lines, plan + checklist)_

### 0.2 GitHub issues 建立
- [x] **Create 9 GitHub issues #53-61** _(label `sprint-53-3` created (#0E8A16); 9 issues #53-#61 all created with sprint-53-3 label; URLs recorded in progress.md Day 0 section)_

### 0.3 Cat 9 既有結構 + baseline 記錄
- [x] **Cat 9 stub structure inventory** _(`__init__.py` + `_abc.py` + `README.md` ONLY; no concrete impls; no input/output/tool/audit subdirs)_
- [x] **Cat 9 既有 tests dir** _(MISSING — Day 1 will create `tests/unit/agent_harness/guardrails/`)_
- [x] **Reference points** _(baseline pre-integration; Day 4 will compare orchestrator_loop count)_
- [x] **pytest baseline** _(680 passed / 4 skipped / 0 xfailed / 0 failed in 23.62s — matches 53.2 final)_
- [x] **mypy baseline** _(210 src files clean; "Success: no issues found in 210 source files")_
- [x] **LLM SDK leak baseline** _(0 violations: "OK: no LLM SDK leak under backend\src")_
- [x] **6 V2 lint scripts baseline** _(all green: AP-1 / AP-3 cross-category / AP-4 duplicate-dataclass / AP-8 promptbuilder 0 violations / AP-11 sync-callback / LLM-SDK)_
- [x] **4 active CI required checks baseline** _(main HEAD 149de254: V2 Lint ✓ / Backend CI ✓ / E2E Tests ✓; all required checks green; "Deploy to Production" failure unrelated to required set)_

### 0.4 Cat 8 carryover prep
- [x] **Verify 53.2 RedisBudgetStore baseline coverage** _(53.2 baseline = 0% coverage; US-8 Day 4 fix to ≥ 80%)_
- [x] **Add fakeredis>=2.20 to pyproject dev deps (US-8 setup)** _(fakeredis 2.35.1 installed via pip install -e ".[dev]"; FakeRedis import verified)_
- [x] **Verify ToolResult struct (US-9 prep)** _(located at `_contracts/tools.py:126`: tool_call_id / tool_name / **success: bool** / content / result_content_types / **error: str | None** / duration_ms; Day 1 add `error_class: str | None = None` after error)_
- [x] **Verify DefaultErrorPolicy classify path (US-9 prep)** _(MRO walk path confirmed; Day 1 add `_registry_by_str` mapping + `register_by_string` method)_

### 0.5 Cat 9 baseline reproduce — boundary check (strict pattern)
- [x] **Verify Cat 8 vs Cat 9 邊界 baseline (Tripwire in error_handling/)** _(strict pattern: `^import.*Tripwire | ^from.*Tripwire | class Tripwire | = Tripwire( | Tripwire()` = **0 hits** ✓; loose grep has 8 hits in docstrings/README — intentional boundary documentation)_
- [x] **Verify ErrorTerminator in guardrails/ baseline** _(strict pattern: `^import.*ErrorTerminator | ^from.*ErrorTerminator | class ErrorTerminator | = ErrorTerminator( | error_terminator.` = **0 hits** ✓; loose grep has 3 hits in docstring/README — intentional)_

### 0.6 alembic baseline (US-6 prep)
- [x] **Verify alembic head on main** _(head = `0010_pg_partman`; US-6 Day 3 will add `<timestamp>_add_audit_log_v2` revision on top)_
- [x] **Verify PG JSONB support in dev DB** _(implicit; existing usage in checkpointer + audit_log models confirms JSONB ok)_

### 0.7 Day 0 progress.md
- [x] **Day 0 progress.md** _(written at `docs/03-implementation/agent-harness-execution/phase-53-3/sprint-53-3-guardrails/progress.md` with full baseline numbers + Day 0 estimated/actual table; Day 0 on schedule ~2.25 hours)_

---

## Day 1 — US-1 GuardrailEngine + US-2 Input (上半) + US-9 ToolResult.error_class (est. 6-7 hours)

### 1.1 US-9 ToolResult.error_class field（先做小 task）
- [x] **Add `error_class` field to ToolResult** _(after `error: str | None`; default None preserves existing serialization)_
- [x] **Update ToolExecutor exception path** _(only the `try/except` path writes `error_class`; `_fail()` paths intentionally None — non-exception failures)_
- [x] **Enhance DefaultErrorPolicy.classify** _(added `_registry_by_str` mirror + `register_by_string()` + `classify_by_string()`; defaults route through `register()` to populate both views)_

### 1.2 US-9 tests
- [x] **Augment test_executor.py with error_class case** _(2 new tests: error_class set on exception path / None on non-exception failure)_
- [x] **Augment test_policy.py with by-string lookup case** _(new TestClassifyByString class with 6 tests: defaults mirror / register auto-mirror / register_by_string direct / idempotent / unknown→FATAL / strict-no-MRO)_
- [x] **Close GitHub issue #61** _(closed via `gh issue close` after merge verification)_

### 1.3 US-1 GuardrailEngine framework
- [x] **Create engine.py** _(`_RegisteredGuardrail` + `GuardrailEngine` with register / check_input / check_output / check_tool_call / batch_check_tool_calls; per-type chain priority sort; fail-fast on first non-PASS; mypy strict clean)_

### 1.4 GuardrailTriggered event
- [x] **`GuardrailTriggered` already exists in `_contracts/events.py:225`** _(stub created Sprint 49.1; fields guardrail_type/action/reason — sufficient for 53.3 emission. `TripwireTriggered` also stub at line 232; both re-exported via `_contracts/__init__`)_

### 1.5 guardrails.yaml config
- [x] **Create `backend/config/guardrails.yaml`** _(input: pii_detector priority=10; output/tool empty placeholders for Day 2/3 detectors; declarative engine factory hints documented)_

### 1.6 test_engine.py
- [x] **Create `backend/tests/unit/agent_harness/guardrails/test_engine.py`** _(12 tests pass: empty chains × 3 / priority order / default priority 100 / fail-fast block / fail-fast sanitize / type isolation / batch empty / batch parallel timing < 200ms for 5×50ms / batch per-call block isolation / type registration; engine.py 100% coverage)_

### 1.7 US-2 Input guardrails (上半) — PIIDetector
- [x] **Create `guardrails/input/__init__.py`** _(re-exports PIIDetector)_
- [x] **Create `guardrails/input/pii_detector.py`** _(4 patterns email/phone/ssn/credit_card; threshold-based BLOCK (≥2 hits) / ESCALATE (1 hit) / PASS (0); span-based dedup by priority — ssn > credit_card > email > phone — prevents double-count when patterns overlap. Lookaround guards on phone regex prevent partial-match within CC sub-runs)_
- [x] **Create `tests/fixtures/guardrails/pii_redteam.yaml`** _(38 positives across 5 categories: 5 email + 5 phone + 4 ssn + 4 cc + 6 multi-PII + 6 edge / 12 negatives; expected_action ESCALATE/BLOCK/PASS per case)_
- [x] **Create `test_input_pii.py`** _(53 tests: 3 invariants + 4 smoke + 3 content extraction + 38 redteam positives + 12 redteam negatives + 1 accuracy summary aggregate; all pass; PII positive accuracy 100% / negative accuracy 100% — exceeds 95% target)_

### 1.8 Day 1 sanity checks
- [x] **mypy strict 仍 clean** _(213 src files clean; baseline 210 + 3 new = engine.py + pii_detector.py + input/__init__.py)_
- [x] **All 6 V2 lint scripts 仍綠** _(ap1 / cross_category / duplicate_dataclass / llm_sdk_leak / promptbuilder / sync_callback all green; AP-8 PromptBuilder 0 violations)_
- [x] **Full pytest 不退步** _(680 baseline → **753 passed** / 4 skip / 0 xfail / 0 fail; +73 new = 8 US-9 + 12 US-1 + 53 US-2)_
- [x] **Cat 9 coverage Day 1 partial** _(98% total: __init__ 100% / _abc 100% / engine 100% / input/__init__ 100% / pii_detector 94%; target ≥ 80% well exceeded)_
- [x] **black + isort + flake8 + ruff** _(black auto-formatted 4 files; isort fixed 2; flake8 caught E501 line-too-long on phone regex → split into multi-line raw-string concat; ruff All checks passed!)_

### 1.9 Day 1 commit + push + verify CI
- [ ] **Commit US-1 + US-2 上半 + US-9**
- [ ] **Push to feature branch**
- [ ] **CI green on this branch (Backend CI 必綠)**
- [ ] **Close GitHub issues #53 (US-1) + #61 (US-9)** _(US-2 #54 stays open — Day 2 finishes JailbreakDetector)_

### 1.10 Day 1 progress.md update
- [ ] **Append Day 1 progress.md** with deliverables / drift table / sanity matrix

---

## Day 2 — US-2 Finish (Jailbreak) + US-3 Output Guardrails (est. 6-7 hours)

### 2.1 US-2 JailbreakDetector
- [ ] **Create `guardrails/input/jailbreak_detector.py`**
  - PATTERNS list (ignore previous instructions / system prompt / jailbreak / DAN / developer mode)
  - `check()` returns BLOCK on hit；optional embedding similarity flag (defer if not configured)
  - DoD: mypy strict clean
- [ ] **Create `tests/fixtures/guardrails/jailbreak_redteam.yaml`**
  - 30+ positive cases；10+ negatives
- [ ] **Create `test_input_jailbreak.py`**
  - parametrize；assert ≥ 90% accuracy on positives
  - DoD: pass

### 2.2 US-3 Output guardrails — ToxicityDetector
- [ ] **Create `guardrails/output/__init__.py`**
- [ ] **Create `guardrails/output/toxicity_detector.py`**
  - PATTERNS dict (hate / harassment / violence / sexual) with severity levels
  - `check()` returns BLOCK (HIGH) / SANITIZE (MEDIUM, with sanitized_content) / REROLL (LOW) / PASS
  - DoD: mypy strict clean
- [ ] **Create `tests/fixtures/guardrails/toxicity_cases.yaml`** (20+ cases)
- [ ] **Create `test_output_toxicity.py`** parametrize；assert action mapping correct

### 2.3 US-3 Output guardrails — SensitiveInfoDetector
- [ ] **Create `guardrails/output/sensitive_info_detector.py`**
  - SYSTEM_PROMPT_LEAK_PATTERNS
  - tenant cross-leak detection (fetch other tenant ids via DI helper)
  - `check()` returns BLOCK with risk_level=CRITICAL
  - DoD: mypy strict clean；tenant_id fetcher injectable for test
- [ ] **Create `tests/fixtures/guardrails/sensitive_leak_cases.yaml`** (15+ cases incl. cross-tenant)
- [ ] **Create `test_output_sensitive_info.py`**
  - 含 multi-tenant cross-leak test (tenant A output 含 tenant B UUID → BLOCK)
  - DoD: pass

### 2.4 Update guardrails/__init__.py
- [ ] **Re-export PIIDetector + JailbreakDetector + ToxicityDetector + SensitiveInfoDetector**

### 2.5 Day 2 sanity checks
- [ ] **mypy --strict** all green (新增 ~4 files)
- [ ] **6 V2 lint scripts** all green
- [ ] **Full pytest 不退步**
  - DoD: Day 1 + Day 2 增量 ≥ +60 tests；0 fail
- [ ] **Cat 9 coverage Day 2**
  - DoD: input + output detectors ≥ 90%；engine 仍 ≥ 90%
- [ ] **black/isort/flake8/ruff** all green

### 2.6 Day 2 commit + push + verify CI
- [ ] **Commit US-2 finish + US-3**
  - Message: `feat(guardrails, sprint-53-3): US-2 JailbreakDetector + US-3 Toxicity + SensitiveInfo detectors`
  - **Verify branch before commit**
- [ ] **Push + verify Backend CI green**
  - DoD: success on latest
- [ ] **Close GitHub issues #54 + #55**

### 2.7 Day 2 progress.md update

---

## Day 3 — US-4 CapabilityMatrix + US-5 Tripwire + US-6 WORM (上半) (est. 6-7 hours)

### 3.1 US-4 CapabilityMatrix + ToolGuardrail
- [ ] **Create `guardrails/tool/__init__.py`**
- [ ] **Create `guardrails/tool/capability_matrix.py`**
  - `Capability` enum (≥ 8 capabilities)
  - `PermissionRule` dataclass (role_required / tenant_scope / max_calls / requires_approval)
  - `CapabilityMatrix` class (capability_to_tools / permission_rules / get_capability / get_rule / from_yaml)
  - DoD: mypy strict clean
- [ ] **Create `backend/config/capability_matrix.yaml`**
  - capability list + permission rules per tool（per plan TS）
  - DoD: YAML loadable
- [ ] **Create `guardrails/tool/tool_guardrail.py`**
  - `ToolGuardrail(Guardrail)` impl: lookup → role check → tenant scope check → max calls (state.transient) → approval gate stub (defer 53.4)
  - DoD: mypy strict clean
- [ ] **Create `test_capability_matrix.py`** + `test_tool_guardrail.py`
  - capability lookup / rule lookup / from_yaml
  - tool guardrail pass / block (role) / block (unknown tool) / escalate (requires_approval)
  - multi-tenant test：tenant A admin cannot affect tenant B
  - DoD: ≥ 12 tests pass
- [ ] **Close GitHub issue #56**

### 3.2 US-5 Tripwire concrete impl
- [ ] **Create `guardrails/tripwire.py`**
  - `DefaultTripwire(TripwireABC)` impl
  - 4 internal patterns: pii_leak_detected / prompt_injection_detected / unauthorized_tool_access / unsafe_output_detected
  - register_pattern (extensibility) + trigger_check (any-pattern fail-fast)
  - async-safe (no shared mutable state issues)
  - DoD: mypy strict clean
- [ ] **Add `TripwireTriggered` event**
  - File: `_contracts/events.py`
  - frozen dataclass: `pattern_name / detail`
  - re-export via `_contracts/__init__.py`
- [ ] **Cat 8 vs Cat 9 邊界守門 strict check**
  - `grep -rn "ErrorTerminator\|error_terminator" backend/src/agent_harness/guardrails/` = 0
  - `grep -rn "Tripwire\|tripwire" backend/src/agent_harness/error_handling/` = 0
  - DoD: 雙向 0 hits（保留 docstring 提及 boundary）
- [ ] **Create `test_tripwire.py`**
  - register / trigger / no-match / multiple patterns / async safety / register_pattern extensibility
  - DoD: ≥ 8 tests pass
- [ ] **Update guardrails/__init__.py**
  - re-export DefaultTripwire + TripwireTriggered
- [ ] **Close GitHub issue #57**

### 3.3 US-6 WORM audit log (上半) — schema + ORM model
- [ ] **Create `backend/src/infrastructure/db/models/audit_log_v2.py`**
  - SQLAlchemy ORM model with id / tenant_id / timestamp / event_type / content (JSONB) / prev_hash / entry_hash (UNIQUE)
  - DoD: mypy strict clean
- [ ] **Create alembic migration**
  - `cd backend && python -m alembic revision --autogenerate -m "add audit_log_v2 with hash chain"`
  - Verify migration file at `backend/alembic/versions/<timestamp>_add_audit_log_v2.py`
  - Add explicit indexes if missing：`idx_audit_v2_tenant_ts` on (tenant_id, timestamp)
  - DoD: `alembic upgrade head` succeed locally + on dev DB
- [ ] **Create `guardrails/audit/__init__.py`**
- [ ] **Create `guardrails/audit/worm_log.py`**
  - WORMAuditLog class with append() method
  - hash chain logic: SELECT prev FOR UPDATE → compute SHA-256 → INSERT
  - DoD: mypy strict clean

### 3.4 Day 3 sanity (中間 push)
- [ ] **mypy --strict** all green (新增 ~6 files Day 3)
- [ ] **6 V2 lint scripts** all green
- [ ] **Full pytest 不退步**
  - DoD: Day 2 + Day 3 增量；0 fail
- [ ] **Cat 9 coverage Day 3 partial**
  - DoD: tool + tripwire ≥ 90%；audit (worm_log Day 3 部分覆蓋)；其他 ≥ 90%

### 3.5 Day 3 commit + push (中間 push 取得 CI 反饋)
- [ ] **Commit US-4 + US-5 + US-6 partial**
  - Message: `feat(guardrails, sprint-53-3): US-4 CapabilityMatrix + ToolGuardrail + US-5 Tripwire + US-6 WORM (partial)`
  - **Verify branch before commit**
- [ ] **Push + verify Backend CI green**
  - 重點：alembic migration 在 Linux CI 環境跑得起來
  - DoD: success on latest

### 3.6 Day 3 progress.md update

---

## Day 4 — US-6 Finish + US-7 AgentLoop Integration + US-8 fakeredis + Retrospective + PR (est. full day)

### 4.1 US-6 finish — chain_verifier + tests
- [ ] **Create `guardrails/audit/chain_verifier.py`**
  - `ChainVerificationResult` dataclass (valid / broken_at_id / total_entries)
  - `verify_chain(session_factory, tenant_id, *, from_id, to_id) -> ChainVerificationResult`
  - 順序遍歷重算 entry_hash 比對
  - DoD: mypy strict clean
- [ ] **Create integration tests**
  - `tests/integration/agent_harness/guardrails/test_worm_log.py`
    - append 100 entries → verify chain valid
    - concurrent append (asyncio.gather × 10) → chain still valid
    - tenant isolation: tamper tenant A entry 50 → verify_chain(A) fail at id 50；verify_chain(B) still valid
    - append latency p95 < 20ms (pytest-benchmark)
  - DoD: ≥ 6 integration tests pass
- [ ] **Update guardrails/__init__.py**
  - re-export WORMAuditLog + verify_chain + ChainVerificationResult
- [ ] **Close GitHub issue #58**

### 4.2 US-7 AgentLoop 3 layer integration
- [ ] **Add Cat 9 deps to AgentLoop.__init__**
  - File: `backend/src/agent_harness/orchestrator_loop/loop.py`
  - 5 opt-in kwargs: guardrail_engine / tripwire / audit_log / capability_matrix / (HITL stub for ESCALATE defer 53.4)
  - 保留 51.x + 53.1 + 53.2 既有 deps
  - DoD: mypy strict clean
- [ ] **Implement 3 切點 wiring in run()**
  - **Loop start**: input check + tripwire check → BLOCK/ESCALATE handling
  - **Per tool call**: tool check + tripwire check → BLOCK/ESCALATE handling (block → ToolResult is_error inject)
  - **Loop end**: output check + tripwire check → BLOCK/SANITIZE/REROLL handling (REROLL max 1 retry)
  - 每切點 audit_log.append (if injected)
  - emit GuardrailTriggered + TripwireTriggered events
  - DoD: 3 切點全 wire；51.x + 53.1 + 53.2 baseline tests 不退步
- [ ] **Update _abc.py if interface changed**

### 4.3 US-7 integration tests
- [ ] **Create `test_loop_guardrails.py`**
  - File: `backend/tests/integration/agent_harness/orchestrator_loop/test_loop_guardrails.py`
  - 6 scenarios:
    - test_input_pii_detected_blocks_loop
    - test_input_jailbreak_triggers_tripwire
    - test_tool_unauthorized_blocked_and_llm_notified
    - test_output_toxicity_high_blocks_response
    - test_output_sensitive_info_sanitizes_content
    - test_output_low_severity_rerolls_once
  - 每 scenario 驗證 audit_log.append 被呼叫 + 對應 event emitted
  - DoD: 6 tests pass

### 4.4 US-8 fakeredis + RedisBudgetStore integration test
- [ ] **Verify fakeredis dep installed (Day 0 已加)**
- [ ] **Create `test_redis_budget_store.py`**
  - File: `backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py`
  - 7+ tests: increment atomicity (concurrent INCR × 100) / get / TTL correct / multi-tenant key isolation / pipeline transaction / get on missing key / EXPIRE refresh
  - DoD: ≥ 7 tests pass；`_redis_store.py` coverage ≥ 80%
- [ ] **Verify 53.2 既有 budget tests 不退步**
  - `pytest tests/unit/agent_harness/error_handling/test_budget.py -v`
  - DoD: 11 既有 tests 仍 pass
- [ ] **Close GitHub issue #60**

### 4.5 Sprint final verification
- [ ] **All 4 active CI required checks green on feature branch latest**
  - `gh run list --branch feature/sprint-53-3-guardrails --limit 6`
  - DoD: 4 active required checks 全綠 on latest commit
- [ ] **pytest final baseline**
  - `cd backend && python -m pytest --tb=no -q 2>&1 | tail -5`
  - DoD: ≥ 760 PASS / 0 xfail / 4 skip / 0 fail
- [ ] **Cat 9 coverage final**
  - `cd backend && python -m pytest tests/ --cov=src/agent_harness/guardrails --cov-report=term 2>&1 | tail -10`
  - DoD: ≥ 80%
- [ ] **mypy strict + LLM SDK leak final**
  - DoD: 220+ src clean；LLM SDK leak = 0；6 V2 lints + black/isort/flake8/ruff green
- [ ] **Cat 9 邊界 grep evidence (雙向)**
  - `grep -rn "Tripwire\|tripwire" backend/src/agent_harness/error_handling/`
  - `grep -rn "ErrorTerminator\|error_terminator" backend/src/agent_harness/guardrails/`
  - DoD: 雙向皆 0 hits
- [ ] **GuardrailEngine 真在 AgentLoop 用（3 切點）**
  - `grep -rn "guardrail_engine\.check_input\|check_output\|check_tool_call" backend/src/agent_harness/orchestrator_loop/`
  - DoD: ≥ 3 hits
- [ ] **Tripwire 真在 AgentLoop 用（3 切點）**
  - `grep -rn "tripwire\.trigger_check" backend/src/agent_harness/orchestrator_loop/`
  - DoD: ≥ 3 hits
- [ ] **WORMAuditLog 真在 AgentLoop 用**
  - `grep -rn "audit_log\.append" backend/src/agent_harness/orchestrator_loop/`
  - DoD: ≥ 2 hits
- [ ] **PII / Jailbreak red-team accuracy**
  - 跑 fixture-driven tests + count
  - DoD: PII ≥ 95% / Jailbreak ≥ 90%
- [ ] **WORM tamper test**
  - integration test 結果
  - DoD: tamper at id 50 → verify_chain fail at exact id 50

### 4.6 Day 4 retrospective.md
- [ ] **Write retrospective.md**
  - Path: `docs/03-implementation/agent-harness-execution/phase-53-3/sprint-53-3-guardrails/retrospective.md`
  - 6 必答條 (per plan §Retrospective 必答)：
    1. Q1 What went well: 每 US commit + verification + 4 active CI run id
    2. Q2 What didn't go well: admin-merge=0 / temp-relax=0 / Cat 9 coverage / Cat 8 vs Cat 9 雙向 grep evidence
    3. Q3 What we learned: generalizable lessons (PII FP modes / WORM PG version diff / 3 layer engine vs Cat 8 retry interaction)
    4. Q4 Audit Debt deferred: list with ID + target sprint
    5. Q5 Next steps: rolling planning carryover candidates only
    6. Q6 主流量整合驗收: GuardrailEngine 真用 (3 切點) / Tripwire 真用 (3 切點) / WORMAuditLog 真寫 (2 切點) / 6 scenarios 全過 / Cat 9 vs Cat 8 雙向 grep=0 / coverage ≥ 80% / red-team accuracy / WORM tamper test
  - DoD: 6 條全答 + 對齊 53.2 retrospective 結構

### 4.7 PR open + closeout
- [ ] **Push final commits**
  - `git push origin feature/sprint-53-3-guardrails`
- [ ] **Verify final CI green (4 active required checks)**
- [ ] **Open PR**
  - Title: `feat(guardrails, sprint-53-3): Cat 9 Guardrails 核心 — GuardrailEngine + 3 layer detectors + Tripwire + CapabilityMatrix + WORM audit log + AgentLoop 3 layer integration + Cat 8 carryover (fakeredis + ToolResult.error_class)`
  - Body 含：
    - Summary: 9 US ✅ + Cat 9 Level 4 達成 + AD-Cat8-1 + AD-Cat8-3 closed
    - Each US verification 證據 (workflow run id + status)
    - GitHub issues #53-61 close URLs
    - Cat 9 coverage 數字
    - Cat 8 vs Cat 9 邊界 grep evidence (雙向：error_handling/ no Tripwire + guardrails/ no ErrorTerminator)
    - Red-team accuracy: PII / Jailbreak
    - WORM tamper test result
    - 3 切點 grep evidence (input/output/tool_call + tripwire × 3 + audit_log × 2)
    - Diff stat
  - DoD: PR opened；CI runs triggered
- [ ] **Wait for review approval (or self-merge per solo-dev policy)**
  - User reviews PR (if applicable)
  - DoD: 0 approvals needed (review_count=0)；4 active required CI green
- [ ] **Normal merge (NOT admin override, NOT temp-relax bootstrap)**
  - `gh pr merge <id> --merge` (or squash per project convention)
  - DoD: merge commit on main；branch protection enforce_admins=true 自動強制；無 bypass；**zero temp-relax**
- [ ] **Verify post-merge main CI green**
  - `gh run list --branch main --limit 4` 等 ~5 min
  - DoD: 4 active required CI checks 全綠 on `main` HEAD；progress.md + retrospective.md §Q1 補上 main HEAD run id
- [ ] **Update memory**
  - V2 milestone: 15/22 sprints (68%)
  - Cat 9 Level 4 達成
  - phase 53.3 完成
  - AD-Cat8-1 + AD-Cat8-3 closed
  - 衍生 audit debt（如 AD-Cat9-1/2/3）紀錄

### 4.8 Cleanup
- [ ] **Delete local feature branch**
  - `git checkout main && git pull && git branch -d feature/sprint-53-3-guardrails`
- [ ] **Delete remote feature branch (if not auto-deleted)**
  - `git push origin --delete feature/sprint-53-3-guardrails`
- [ ] **Update `claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-*` if applicable**
  - Mark AD-Cat8-1 + AD-Cat8-3 closed by 53.3
  - DoD: status doc updated（如有對應 entry）

---

## Verification Summary（Day 4 final 必填）

| Item | Status | Evidence |
|------|--------|----------|
| US-1 GuardrailEngine framework | ⬜ | commit hash + coverage % |
| US-2 Input guardrails (PII + Jailbreak) | ⬜ | commit hash + red-team accuracy ≥ 95% / 90% |
| US-3 Output guardrails (Toxicity + SensitiveInfo) | ⬜ | commit hash + cross-tenant isolation test pass |
| US-4 CapabilityMatrix + ToolGuardrail | ⬜ | commit hash + multi-tenant test pass |
| US-5 Tripwire ABC + plug-in registry | ⬜ | commit hash + 4 patterns registered |
| US-6 WORM audit log + hash chain | ⬜ | commit hash + tamper test fail at exact id |
| US-7 AgentLoop 3 layer integration | ⬜ | grep evidence (3 切點 × engine + 3 切點 × tripwire + 2 切點 × audit_log) + 6 scenarios pass |
| US-8 fakeredis + RedisBudgetStore | ⬜ | commit hash + _redis_store coverage ≥ 80% |
| US-9 ToolResult.error_class | ⬜ | commit hash + by-string lookup test pass |
| 4 active CI required checks green on main HEAD | ⬜ | 4 run ids |
| Cat 9 coverage ≥ 80% | ⬜ | pytest --cov output |
| pytest ≥ 760 PASS / 0 xfail / 0 fail | ⬜ | counts |
| mypy 220+ src clean | ⬜ | tail output |
| LLM SDK leak = 0 | ⬜ | tail output |
| 6 V2 lint scripts green | ⬜ | each exit 0 |
| Cat 9 vs Cat 8 邊界 (Tripwire in error_handling/) | ⬜ | grep = 0 hits |
| Cat 9 vs Cat 8 邊界 (ErrorTerminator in guardrails/) | ⬜ | grep = 0 hits |
| GuardrailEngine 3 切點真用 | ⬜ | grep evidence ≥ 3 hits |
| Tripwire 3 切點真用 | ⬜ | grep evidence ≥ 3 hits |
| WORMAuditLog 真寫 | ⬜ | grep evidence ≥ 2 hits |
| PII detection accuracy | ⬜ | red-team pct ≥ 95% |
| Jailbreak detection accuracy | ⬜ | red-team pct ≥ 90% |
| WORM tamper test | ⬜ | fail at exact id evidence |
| Sprint 53.3 PR normal merge (no admin, no temp-relax) | ⬜ | merge commit hash + protection status |
| V2 milestone 15/22 (68%) | ⬜ | memory + retrospective updated |

---

**權威排序**：本 checklist 對齊 [sprint-53-3-plan.md](./sprint-53-3-plan.md) Acceptance Criteria + Retrospective 必答 6 條。任何 Day 順序變動 / scope 砍必須在 progress.md + retrospective.md 透明列出（per 53.1 / 53.2 closeout 教訓 — branch protection enforce_admins=true + review_count=0 持續強制；本 sprint 必須 zero temp-relax）。
