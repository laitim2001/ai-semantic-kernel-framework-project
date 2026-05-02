# Sprint 53.1 — State Management Checklist

**Plan**: [sprint-53-1-plan.md](./sprint-53-1-plan.md)
**Branch**: `feature/sprint-53-1-state-mgmt` (off main `404b8147`)
**Duration**: 5 days (Day 0-4 standard layout)

---

## Day 0 — Setup + Cat 7 Baseline + AI-20 Quick Win (est. 2-3 hours)

### 0.1 Branch + plan + checklist commit
- [ ] **Verify on main + clean working tree**
  - `git checkout main && git pull && git status --short`
  - DoD: HEAD `404b8147`（or newer if main moved）+ working tree empty
- [ ] **Verify branch protection still enforced**
  - `gh api repos/laitim2001/ai-semantic-kernel-framework-project/branches/main/protection -q '.enforce_admins.enabled'`
  - DoD: returns `true`（不再走 52.6 temp-relax bootstrap）
- [ ] **Create feature branch**
  - `git checkout -b feature/sprint-53-1-state-mgmt`
  - DoD: `git branch --show-current` returns `feature/sprint-53-1-state-mgmt`
- [ ] **Verify phase folder structure exists**
  - planning: `docs/03-implementation/agent-harness-planning/phase-53-1-state-mgmt/sprint-53-1-{plan,checklist}.md`
  - execution (create): `docs/03-implementation/agent-harness-execution/phase-53-1/sprint-53-1-state-mgmt/`
  - DoD: `ls -d` confirms both
- [ ] **Commit Day 0 docs (plan + checklist)**
  - Files: this plan + this checklist
  - Commit message: `docs(state-mgmt, sprint-53-1): Day 0 plan + checklist`
  - **Verify branch before commit**: `git branch --show-current`
  - DoD: `git log -1` shows Day 0 commit on feature branch

### 0.2 GitHub issues 建立
- [ ] **Create 6 GitHub issues #32-37**
  - 模仿 52.6 #21-26 格式 — title + body 含 plan link + DoD
  - #32 US-1 Reducer concrete impl
  - #33 US-2 DBCheckpointer + alembic + time-travel
  - #34 US-3 Transient/durable split runtime enforcement
  - #35 US-4 AgentLoop integration with Reducer + Checkpointer
  - #36 US-6 pyproject.toml [dev] add ruff (52.6 AI-20)
  - #37 US-7 code-quality.md cross-platform mypy docs (52.6 AI-21)
  - DoD: `gh issue list -l sprint-53-1 -s open` returns 6 rows; URLs 列入 progress.md
- [ ] **Verify #27 status**
  - `gh issue view 27 --json state,title,labels`
  - DoD: open；labels 含 `sprint-52-6` + reactivation plan in body；本 sprint 將大幅推進

### 0.3 Cat 7 既有結構 + baseline 記錄
- [ ] **Cat 7 stub structure inventory**
  - `ls backend/src/agent_harness/state_mgmt/ backend/src/agent_harness/_contracts/state.py`
  - DoD: 確認 `_abc.py` (Checkpointer + Reducer ABC) + `__init__.py` + `README.md` + `_contracts/state.py` (LoopState/StateVersion/Transient/Durable dataclasses)
- [ ] **Cat 7 既有 tests dir**
  - `ls backend/tests/unit/agent_harness/state_mgmt/ backend/tests/integration/agent_harness/state_mgmt/ 2>&1 || echo "(missing — to be created)"`
  - DoD: 記錄是否需 mkdir
- [ ] **Reference points: 21 files referencing state**
  - `grep -rln "Checkpointer\|LoopState\|StateSnapshot" backend/src/agent_harness/ | wc -l`
  - DoD: count 對齊 21（or noted 差異）
- [ ] **pytest baseline**
  - `cd backend && python -m pytest --tb=no -q 2>&1 | tail -5`
  - DoD: `550 PASS / 14 xfailed / 4 skipped / 0 failed` recorded（per Sprint 52.6 closeout）
- [ ] **mypy baseline**
  - `cd backend && python -m mypy --strict src 2>&1 | tail -3`
  - DoD: 200 src files clean recorded
- [ ] **LLM SDK leak baseline**
  - `python scripts/lint/check_llm_sdk_leak.py --root backend/src 2>&1 | tail -2`
  - DoD: 0 violations recorded
- [ ] **alembic head baseline**
  - `cd backend && alembic heads 2>&1 | head -3`
  - DoD: 1 head recorded（為 US-2 migration 對齊 parent）

### 0.4 US-6 (AI-20) dev extras quick win
- [ ] **Edit `backend/pyproject.toml`**
  - 在 `[project.optional-dependencies] dev = [...]` 加 `"ruff>=0.6,<1.0"`（如已存在則跳過）
  - DoD: `grep "ruff" backend/pyproject.toml` shows entry under [dev]
- [ ] **Verify in fresh venv (or current)**
  - `cd backend && pip install -e .[dev] 2>&1 | tail -5`
  - `ruff --version`
  - DoD: ruff installed via [dev]; version output OK
- [ ] **Commit US-6**
  - Stage: `git add backend/pyproject.toml`
  - Message: `chore(deps, sprint-53-1): US-6 add ruff to [dev] extras (52.6 AI-20)`
  - **Verify branch before commit**: `git branch --show-current`
- [ ] **Push to feature branch**
  - `git push origin feature/sprint-53-1-state-mgmt`
- [ ] **Close GitHub issue #36**
  - `gh issue close 36 --comment "Resolved by commit <hash>. Verified: pip install -e .[dev] installs ruff."`

### 0.5 #27 catalog 對齊
- [ ] **List 14 xfail tests with current decorator state**
  - `grep -rn "@pytest.mark.xfail" backend/tests/ | head -20`
  - DoD: 14 hits across 6 files；reasons 對齊 Sprint 52.6 plan §US-7 表
- [ ] **Run 14 tests in isolation to capture current failure mode**
  - `cd backend && python -m pytest tests/integration/memory/test_memory_tools_integration.py tests/integration/memory/test_tenant_isolation.py tests/integration/orchestrator_loop/test_cancellation_safety.py tests/unit/api/v1/chat/test_router.py::TestMultiTenantIsolation tests/e2e/test_lead_then_verify_workflow.py tests/integration/agent_harness/tools/test_builtin_tools.py --no-header -rf 2>&1 | tail -30`
  - DoD: 14 個 xfailed (不是 fail)；error messages 記錄到 progress.md（為 Day 3-4 reactivation 提供 baseline）

### 0.6 Day 0 progress.md
- [ ] **Day 0 progress.md**
  - Path: `docs/03-implementation/agent-harness-execution/phase-53-1/sprint-53-1-state-mgmt/progress.md`
  - Sections: Day 0 setup / Cat 7 baseline / 6 GitHub issue URLs / #27 14 xfail captured failure modes / US-6 ✅ AI-20 closed / Remaining for Day 1
  - DoD: 6 issue URLs + Cat 7 baseline metrics + #27 baseline 已列

---

## Day 1 — US-1 Reducer Concrete Impl (est. 5-6 hours)

### 1.1 Create reducer.py
- [ ] **Write `DefaultReducer` class**
  - File: `backend/src/agent_harness/state_mgmt/reducer.py`
  - File header per `file-header-convention.md`：Purpose / Category 7 / Scope Sprint 53.1 / Description / Modification History
  - Implement `merge(state, update, *, source_category, trace_context=None) -> LoopState`
  - asyncio.Lock for thread safety
  - Monotonic version increment
  - DoD: file 存在；mypy --strict pass for new file
- [ ] **Implement `_merge_transient` helper**
  - Handle `messages_append` (additive list extend), `current_turn` (replace), `token_usage_so_far` (replace), `pending_tool_calls_set` (replace), `pending_tool_calls_clear` (set to [])
  - DoD: dataclass 重建；frozen contract 守住
- [ ] **Implement `_merge_durable` helper**
  - Handle `pending_approval_ids_add` / `pending_approval_ids_remove` / `conversation_summary` (replace) / `last_checkpoint_version` (replace) / `metadata_set`
  - DoD: dataclass 重建

### 1.2 Update state_mgmt/__init__.py
- [ ] **Re-export DefaultReducer**
  - Edit `backend/src/agent_harness/state_mgmt/__init__.py`
  - Add: `from agent_harness.state_mgmt.reducer import DefaultReducer`
  - Update `__all__`
  - DoD: `python -c "from agent_harness.state_mgmt import DefaultReducer"` works

### 1.3 Unit tests
- [ ] **Create test_reducer.py**
  - File: `backend/tests/unit/agent_harness/state_mgmt/test_reducer.py`
  - File header per convention
  - Tests:
    - `test_merge_increments_version_monotonically`
    - `test_merge_records_source_category`
    - `test_merge_appends_messages`
    - `test_merge_replaces_current_turn`
    - `test_merge_durable_pending_approval_add_remove`
    - `test_parallel_merge_under_lock` (asyncio.gather × 10 → version 連續無洞)
    - `test_merge_emits_tracer_event` (mock TraceContext)
  - DoD: ≥ 7 tests pass
- [ ] **Run unit tests + coverage**
  - `cd backend && python -m pytest tests/unit/agent_harness/state_mgmt/test_reducer.py -v --cov=src/agent_harness/state_mgmt/reducer --cov-report=term-missing`
  - DoD: coverage ≥ 85%；no regressions in baseline 550 PASS

### 1.4 Day 1 sanity checks
- [ ] **mypy strict 仍 clean**
  - `cd backend && python -m mypy --strict src 2>&1 | tail -3`
  - DoD: 200+ files clean
- [ ] **All 6 V2 lint scripts 仍綠**
  - `python scripts/lint/check_llm_sdk_leak.py --root backend/src && python scripts/lint/check_cross_category_import.py --root backend/src/agent_harness && python scripts/lint/check_promptbuilder_usage.py --root backend/src && ...`
  - DoD: 全 exit 0
- [ ] **Full pytest 不退步**
  - `cd backend && python -m pytest --tb=no -q 2>&1 | tail -5`
  - DoD: ≥ 557 PASS（550 baseline + ≥ 7 new reducer tests）/ 14 xfail / 4 skip / 0 fail

### 1.5 Day 1 commit + push + verify CI
- [ ] **Commit US-1**
  - Stage: `git add backend/src/agent_harness/state_mgmt/reducer.py backend/src/agent_harness/state_mgmt/__init__.py backend/tests/unit/agent_harness/state_mgmt/`
  - Message: `feat(state-mgmt, sprint-53-1): US-1 DefaultReducer concrete impl + unit tests`
  - **Verify branch before commit**
- [ ] **Push to feature branch**
  - `git push origin feature/sprint-53-1-state-mgmt`
- [ ] **Verify backend-ci.yml + ci.yml + V2 Lint green on this branch**
  - `gh run list --branch feature/sprint-53-1-state-mgmt --limit 3`
  - 等 ~3 min；`gh run view <id> --json conclusion`
  - DoD: 8 active workflow 全 success on this push
- [ ] **Close GitHub issue #32**
  - `gh issue close 32 --comment "Resolved by commit <hash>. Coverage: XX%. Verified: 7 unit tests pass; mypy strict clean; lint scripts pass."`

### 1.6 Day 1 progress.md update
- [ ] **Append Day 1 progress.md**
  - Sections: Today's accomplishments (US-1 ✅) / coverage % / Remaining for Day 2

---

## Day 2 — US-2 DBCheckpointer + alembic + US-3 Transient/Durable Enforcement (est. 6-7 hours)

### 2.1 Create _db_models.py (SQLAlchemy)
- [ ] **Write `StateSnapshotORM` model**
  - File: `backend/src/agent_harness/state_mgmt/_db_models.py`
  - File header per convention
  - Columns: id (UUID PK) / session_id / tenant_id / version / parent_version / created_at / created_by_category / durable_state (JSONB) / transient_summary (JSONB) / size_bytes
  - UNIQUE (session_id, version)
  - FK tenant_id → tenants.id
  - DoD: mypy strict pass

### 2.2 Create alembic migration
- [ ] **Generate alembic revision**
  - `cd backend && alembic revision -m "add_state_snapshots_table_for_cat7" --autogenerate`
  - DoD: file under `backend/alembic/versions/` 產生；parent_revision 對齊 Day 0.3 head
- [ ] **Verify migration content**
  - 開 generated file，確認 `op.create_table('state_snapshots', ...)` + `op.create_index(...)` × 2
  - 必要時 hand-edit 確保 column / index 與 §Tech Spec §US-2 schema 對齊
  - DoD: SQL diff 符合預期
- [ ] **Test migration round-trip**
  - `cd backend && alembic upgrade head 2>&1 | tail -5`
  - `alembic downgrade -1 2>&1 | tail -3`
  - `alembic upgrade head 2>&1 | tail -3`
  - DoD: 三步皆 success；無 schema drift

### 2.3 Create checkpointer.py
- [ ] **Write `DBCheckpointer` class**
  - File: `backend/src/agent_harness/state_mgmt/checkpointer.py`
  - File header per convention
  - Implement `save(state, *, trace_context=None) -> StateVersion`
  - Implement `load(*, version, trace_context=None) -> LoopState`
  - Implement `time_travel(*, target_version, trace_context=None) -> LoopState`
  - Tenant isolation：every query WHERE tenant_id = state.durable.tenant_id
  - Tracer events per `observability-instrumentation.md` §5
  - DoD: mypy strict pass

### 2.4 Implement transient/durable serialization (US-3)
- [ ] **Write `_serialize_state_for_db(state) -> dict[str, Any]`** helper
  - durable_state JSONB ← `dataclasses.asdict(state.durable)` with UUID→str / datetime→isoformat
  - transient_summary JSONB ← `{"current_turn": ..., "token_usage_so_far": ..., "elapsed_ms": ...}` (NOT messages / pending_tool_calls)
  - DoD: byte size 預估 < 5KB for typical session
- [ ] **Write `_deserialize_state_from_db(row) -> LoopState`** helper
  - Rebuild DurableState from durable_state JSONB
  - Rebuild TransientState with empty messages / pending_tool_calls + scalars from transient_summary
  - Rebuild StateVersion (frozen)
  - DoD: round-trip equality on durable fields

### 2.5 Update state_mgmt/__init__.py + README
- [ ] **Re-export DBCheckpointer**
  - Edit `__init__.py`：`from agent_harness.state_mgmt.checkpointer import DBCheckpointer`
  - DoD: import works
- [ ] **Update README.md (US-3 docs)**
  - 移除 "skeleton" / "Implementation Phase: 53.1" 字眼
  - 加 §Implementation 段落：DBCheckpointer + DefaultReducer 實作描述
  - §Transient vs Durable 升級為實際行為（save 不入 messages buffer；load rehydrate empty）
  - DoD: README 反映實際行為

### 2.6 Unit + integration tests
- [ ] **Create test_checkpointer.py (unit)**
  - File: `backend/tests/unit/agent_harness/state_mgmt/test_checkpointer.py`
  - Mock DB session
  - Tests: save dict shape / load deserialization / time_travel logic / tenant_id 強制
  - DoD: ≥ 6 tests pass
- [ ] **Create test_checkpointer_db.py (integration)**
  - File: `backend/tests/integration/agent_harness/state_mgmt/test_checkpointer_db.py`
  - Real PG fixture (per `multi-tenant-data.md` test pattern)
  - Tests: round-trip save→load equality / time_travel v1→v2→load v1 / tenant isolation (tenant_b cannot load tenant_a snapshot) / size constraint < 5KB
  - DoD: ≥ 4 integration tests pass
- [ ] **Run tests + coverage**
  - `cd backend && python -m pytest tests/unit/agent_harness/state_mgmt/ tests/integration/agent_harness/state_mgmt/ -v --cov=src/agent_harness/state_mgmt --cov-report=term-missing`
  - DoD: Cat 7 coverage ≥ 85%

### 2.7 Day 2 sanity + commit + push + verify CI
- [ ] **mypy strict + lint scripts + full pytest baseline 不退步**
  - 同 1.4
  - DoD: 全綠；test count ≥ 567 PASS（baseline 550 + 7 reducer + ≥ 10 checkpointer）
- [ ] **Commit US-2 + US-3**
  - Stage: `git add backend/src/agent_harness/state_mgmt/ backend/alembic/versions/ backend/tests/`
  - Message: `feat(state-mgmt, sprint-53-1): US-2 + US-3 DBCheckpointer + alembic + transient/durable split`
  - **Verify branch before commit**
- [ ] **Push**
- [ ] **Verify 8 active CI workflow green on this push**
  - `gh run list --branch feature/sprint-53-1-state-mgmt --limit 3`
  - DoD: 全 success；ci.yml Tests step include alembic upgrade + new tests
- [ ] **Close GitHub issues #33 + #34**
  - `gh issue close 33 --comment "..."` / `gh issue close 34 --comment "..."`

### 2.8 Day 2 progress.md update

---

## Day 3 — US-4 AgentLoop Integration + #27 Reactivation 上半 (est. 7-8 hours)

### 3.1 US-4 AgentLoop dependency injection
- [ ] **Update AgentLoop signature**
  - Edit `backend/src/agent_harness/orchestrator_loop/loop.py`
  - Add constructor params: `reducer: Reducer`, `checkpointer: Checkpointer`
  - Store as instance attributes
  - DoD: mypy strict pass
- [ ] **Update Loop ABC if needed**
  - `backend/src/agent_harness/orchestrator_loop/_abc.py`
  - 檢查是否 ABC 簽名也需更新（如有 abstract `__init__`）
  - DoD: ABC 與 concrete 對齊

### 3.2 US-4 mutation 全走 Reducer
- [ ] **Replace direct state mutation with Reducer.merge calls**
  - Grep `state.transient.messages.append\|state.transient.current_turn = \|state.durable.` in `orchestrator_loop/`
  - Replace each with `state = await self.reducer.merge(state, {...}, source_category="orchestrator_loop", trace_context=...)`
  - DoD: grep `state\.transient\.\w+\s*[=.+]` in `orchestrator_loop/` returns 0 mutating cases (only reads)
- [ ] **Add checkpoint after each safe point**
  - After LLM call → `await self.checkpointer.save(state, ...)`
  - After tool execution → `await self.checkpointer.save(state, ...)`
  - After verification → `await self.checkpointer.save(state, ...)`
  - On HITL pause → force checkpoint
  - DoD: grep `checkpointer.save` in `orchestrator_loop/` ≥ 3 hits

### 3.3 US-4 SSE event 升級
- [ ] **Add `state_version` to LoopEvent**
  - Edit `backend/src/agent_harness/_contracts/events.py`
  - Add `state_version: int | None = None` field
  - Update event emission sites in `loop.py` to set `state_version=state.version.version`
  - DoD: mypy strict pass; existing event tests 不退步

### 3.4 US-4 router DI update
- [ ] **Update `backend/src/api/v1/chat/router.py` DI**
  - 在 chat handler / loop factory 加 reducer + checkpointer instance（dependency injection 對齊既有 pattern）
  - DoD: chat endpoint 仍可 invoke loop；DI 不報錯
- [ ] **Run integration test on chat router**
  - `cd backend && python -m pytest tests/integration/api/v1/chat/ -v 2>&1 | tail -10`
  - DoD: 既有 chat tests 不退步

### 3.5 US-4 integration test
- [ ] **Update `tests/integration/agent_harness/orchestrator_loop/test_loop.py`**
  - Add test: `test_loop_writes_state_snapshots_to_db`
    - Run 3-turn loop with 1 tool call + 1 verify
    - Assert DB `state_snapshots` table has ≥ 5 rows for the session
  - Add test: `test_loop_uses_reducer_for_mutation`
    - Mock Reducer; assert merge called with each safe point
  - DoD: 2 new tests pass; existing 不退步

### 3.6 Day 3 mid-day commit + push (US-4)
- [ ] **Commit US-4**
  - Stage: `git add backend/src/agent_harness/orchestrator_loop/ backend/src/agent_harness/_contracts/events.py backend/src/api/v1/chat/router.py backend/tests/integration/`
  - Message: `feat(orchestrator-loop, sprint-53-1): US-4 integrate Reducer + Checkpointer; SSE state_version`
  - **Verify branch before commit**
- [ ] **Push + verify CI green**
  - `git push origin feature/sprint-53-1-state-mgmt`
  - `gh run list --branch ... --limit 3`
  - DoD: 8 workflow green
- [ ] **Close GitHub issue #35**

### 3.7 #27 reactivation 上半 — Cat 7 native + ExecutionContext 6+2
- [ ] **Reactivate `test_cancellation_safety.py` × 1**
  - Remove `@pytest.mark.xfail` decorator
  - Run: `cd backend && python -m pytest tests/integration/orchestrator_loop/test_cancellation_safety.py -v`
  - 如 fail: 修對應 source code（cancel 時 force checkpoint pattern via US-4）
  - DoD: test pass without xfail
- [ ] **Reactivate `test_memory_tools_integration.py` × 6**
  - Remove xfail × 6
  - Run isolated; 失敗 = ExecutionContext drift；修對應 memory module 對齐 Reducer pattern
  - DoD: 6/6 pass（or partial pass + new issue for residual）
- [ ] **Reactivate `test_tenant_isolation.py` × 2**
  - Remove xfail × 2
  - Run; 修 tenant_id flow through LoopState.durable
  - DoD: 2/2 pass

### 3.8 Day 3 sanity + commit + push (#27 上半)
- [ ] **Run full pytest**
  - `cd backend && python -m pytest --tb=no -q 2>&1 | tail -8`
  - DoD: ≥ 562 PASS / ≤ 5 xfail (剩 lead_then_verify × 2 + router × 1 + builtin_tools × 2 待 Day 4) / 0 fail
- [ ] **mypy + lint baselines**
  - 同 1.4
- [ ] **Commit #27 上半**
  - Stage: `git add backend/tests/ backend/src/`（如 source 有對齐改動）
  - Message: `fix(state-mgmt, sprint-53-1): #27 reactivate 9 xfail (cancellation + memory + tenant)`
  - **Verify branch before commit**
- [ ] **Push + verify CI green**

### 3.9 Day 3 progress.md update

---

## Day 4 — #27 下半 + US-7 Docs + Retrospective + Closeout (est. 5-6 hours)

### 4.1 #27 reactivation 下半 — 剩餘 5 xfail
- [ ] **Reactivate `test_router.py::TestMultiTenantIsolation` × 1**
  - Remove xfail × 1
  - Run; 修 tenant context dep injection
  - DoD: pass
- [ ] **Reactivate `test_lead_then_verify_workflow.py` × 2 (E2E demo)**
  - Remove xfail × 2
  - Run E2E; 修 demo 對齐新 state checkpoint sequence
  - DoD: 2/2 pass
- [ ] **Try reactivate `test_builtin_tools.py` × 2 (CARRY-035)**
  - Remove xfail × 2; run
  - **降規模門檻**：如 > 2 hours 不解 → revert xfail decorator + 開新 GitHub issue + Audit Debt
  - DoD: 2/2 pass OR 2/2 留 xfail 加 new issue link in reason

### 4.2 #27 status update
- [ ] **Decide #27 closure**
  - 如 14/14 reactivate → `gh issue close 27 --comment "All 14 reactivated by Sprint 53.1 commits <hash list>."`
  - 如 partial (例如 12/14) → `gh issue edit 27 --body "Updated 2026-05-XX: 12/14 reactivated by Sprint 53.1; remaining 2 (test_builtin_tools.py CARRY-035) tracked in #38."`
  - DoD: #27 状态明確

### 4.3 US-7 cross-platform mypy docs (AI-21)
- [ ] **Edit `.claude/rules/code-quality.md`**
  - Add §Cross-platform mypy `# type: ignore[X, unused-ignore]` Pattern 章節
  - Include 3 examples (Optional dependency / platform-specific import / conditional Optional unwrap)
  - Link to 52.6 retrospective Q4
  - DoD: 章節新增；structure 對齐既有章節風格
- [ ] **Commit US-7**
  - Stage: `git add .claude/rules/code-quality.md`
  - Message: `docs(rules, sprint-53-1): US-7 add cross-platform mypy pattern (52.6 AI-21)`
  - **Verify branch before commit**
- [ ] **Close GitHub issue #37**

### 4.4 #27 reactivation final commit
- [ ] **Commit #27 下半**
  - Stage: `git add backend/tests/ backend/src/`
  - Message: `fix(tests, sprint-53-1): #27 reactivate remaining 5 xfail (router + e2e + builtin_tools)`
  - **Verify branch before commit**
- [ ] **Push + verify CI green**

### 4.5 Sprint final verification
- [ ] **All 8 active CI workflow green on feature branch latest**
  - `gh run list --branch feature/sprint-53-1-state-mgmt --limit 8`
  - DoD: 全綠 on latest commit
- [ ] **pytest final baseline**
  - `cd backend && python -m pytest --tb=no -q 2>&1 | tail -5`
  - DoD: ≥ 562 PASS / ≤ 2 xfail (carryover) / 4 skip / 0 fail
- [ ] **Cat 7 coverage final**
  - `cd backend && python -m pytest tests/ --cov=src/agent_harness/state_mgmt --cov-report=term 2>&1 | tail -10`
  - DoD: ≥ 85%
- [ ] **mypy strict + LLM SDK leak final**
  - 同 1.4
  - DoD: 全綠；無退步
- [ ] **Reducer-as-sole-mutator grep evidence**
  - `grep -rn "state\.transient\.\w*\.append\|state\.durable\.\w*\s*=" backend/src/agent_harness/orchestrator_loop/`
  - DoD: 0 hits（all mutation via reducer）
- [ ] **Checkpointer 真在 AgentLoop 用**
  - `grep -rn "checkpointer\.save" backend/src/agent_harness/orchestrator_loop/`
  - DoD: ≥ 3 hits

### 4.6 Day 4 retrospective.md
- [ ] **Write retrospective.md**
  - Path: `docs/03-implementation/agent-harness-execution/phase-53-1/sprint-53-1-state-mgmt/retrospective.md`
  - 6 必答條 (per plan §Retrospective 必答)：
    1. 每個 US 真清了嗎？commit + verification + 8 active CI run id
    2. 跨切面紀律：admin-merge count（=0）/ Cat 7 coverage / Reducer-as-sole-mutator grep evidence
    3. 砍 scope？（CARRY-035 / 部分 #27）
    4. GitHub issues #32-37 + #27 status table
    5. Audit Debt 累積？（state retention policy / serialization edge cases / etc）
    6. 主流量整合驗收（Reducer 真用？Checkpointer 真用？state_snapshots DB row 數？time_travel round-trip？coverage 真 ≥ 85%？）
  - DoD: 6 條全答 + 對齊 52.6 retrospective 結構

### 4.7 PR open + closeout
- [ ] **Push final commits**
  - `git push origin feature/sprint-53-1-state-mgmt`
- [ ] **Verify final CI green**
  - 8 workflow 全綠 on latest commit
- [ ] **Open PR**
  - Title: `feat(state-mgmt, sprint-53-1): Cat 7 State Management — Reducer + DBCheckpointer + AgentLoop integration + #27 reactivation`
  - Body 含：
    - Summary: 7 US ✅ + Cat 7 Level 3 達成 + #27 status
    - Each US verification 證據 (workflow run id + status)
    - GitHub issues #32-37 close URLs + #27 status
    - Cat 7 coverage 數字
    - Reducer-as-sole-mutator grep evidence
    - state_snapshots DB row 整合 test 證據
    - Diff stat
  - DoD: PR opened；CI runs triggered
- [ ] **Wait for review approval (per branch protection)**
  - User reviews PR
  - DoD: 1 approval given (per protection rule required_approving_review_count=1)
- [ ] **Normal merge (NOT admin override)**
  - `gh pr merge <id> --merge` (or squash per project convention)
  - DoD: merge commit on main；branch protection enforce_admins=true 自動強制；無 bypass
- [ ] **Verify post-merge main CI green**
  - `gh run list --branch main --limit 8` 等 ~5 min
  - 8 workflow 全綠 on `main` HEAD
  - DoD: progress.md + retrospective.md §Q1 補上 main HEAD 的 run id
- [ ] **Update memory**
  - V2 milestone: 13/22 sprints (59%)
  - Cat 7 Level 3 達成
  - phase 53 啟動
  - #27 closure status

### 4.8 Cleanup
- [ ] **Delete local feature branch**
  - `git checkout main && git pull && git branch -d feature/sprint-53-1-state-mgmt`
  - DoD: branch removed local
- [ ] **Delete remote feature branch (if not auto-deleted)**
  - `git push origin --delete feature/sprint-53-1-state-mgmt`
- [ ] **Update `claudedocs/5-status/V2-AUDIT-OPEN-ISSUES-20260501.md` if applicable**
  - Mark relevant audit debt items closed by 53.1
  - DoD: §10 table updated（如有對應 entry）

---

## Verification Summary（Day 4 final 必填）

| Item | Status | Evidence |
|------|--------|----------|
| US-1 Reducer concrete impl | ⬜ | commit hash + coverage % |
| US-2 DBCheckpointer + alembic | ⬜ | commit hash + alembic upgrade head success |
| US-3 Transient/durable split | ⬜ | DB row size < 5KB test pass |
| US-4 AgentLoop integration | ⬜ | grep checkpointer.save ≥ 3 hits in orchestrator_loop/ |
| US-5 #27 14 xfail reactivation | ⬜ | 14/14 or partial X/14 + new issue |
| US-6 ruff in [dev] (52.6 AI-20) | ⬜ | pip install -e .[dev] verified |
| US-7 cross-platform mypy docs (52.6 AI-21) | ⬜ | section in code-quality.md |
| 8 active CI workflow green on main HEAD | ⬜ | 8 run ids |
| Cat 7 coverage ≥ 85% | ⬜ | pytest --cov output |
| pytest ≥ 562 PASS / ≤ 2 xfail / 0 fail | ⬜ | counts |
| mypy 200+ src clean | ⬜ | tail output |
| LLM SDK leak = 0 | ⬜ | tail output |
| 6 V2 lint scripts green | ⬜ | each exit 0 |
| Reducer-as-sole-mutator (orchestrator_loop) | ⬜ | grep evidence (0 mutations) |
| Sprint 53.1 PR normal merge (no admin) | ⬜ | merge commit hash + protection status |
| V2 milestone 13/22 (59%) | ⬜ | memory + retrospective updated |

---

**權威排序**：本 checklist 對齐 [sprint-53-1-plan.md](./sprint-53-1-plan.md) Acceptance Criteria + Retrospective 必答 6 條。任何 Day 順序變動 / scope 砍必須在 progress.md + retrospective.md 透明列出（per 52.6 closeout 教訓 — branch protection 已 enforce_admins=true，技術上不可 admin bypass，行為紀律配合）。
