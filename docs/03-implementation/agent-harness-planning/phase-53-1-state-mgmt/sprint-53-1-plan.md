# Sprint 53.1 — State Management (Cat 7)

**Phase**: phase-53-1-state-mgmt
**Sprint**: 53.1
**Duration**: 5 days (Day 0-4 standard layout)
**Status**: TODO → IN PROGRESS → DONE
**Created**: 2026-05-02
**Owner**: User-spawned session 2026-05-02+ (rename: v2-rebuild-main-session-20260502)
**Branch**: feature/sprint-53-1-state-mgmt (off main `404b8147`)

---

## Sprint Goal

實作 V2 範疇 7 (State Management)：把 49.1 落地的 `Checkpointer` + `Reducer` ABC stub 升級為**生產級實作** — DB-backed snapshot + monotonic version + transient/durable split + time-travel + Reducer-as-sole-mutator pattern + AgentLoop 整合。同時 reactivate Sprint 52.6 標記的 14 個 xfail tests（#27 umbrella；ExecutionContext drift 透過 Reducer pattern 一次清理），並 bundle Sprint 52.6 carryover AI-20（dev extras）+ AI-21（cross-platform `# type: ignore` docs）。**這是 V2 第 13 sprint（55% → 59%）**，也是 phase 53 啟動 sprint。

---

## Background

### Cat 7 history

- **Sprint 49.1 (Phase 49 Foundation)** 落地 ABC stub：
  - `backend/src/agent_harness/_contracts/state.py`：`StateVersion` (frozen) / `TransientState` / `DurableState` / `LoopState` dataclasses
  - `backend/src/agent_harness/state_mgmt/_abc.py`：`Checkpointer` (save / load / time_travel) + `Reducer` (merge) ABCs
  - `backend/src/agent_harness/state_mgmt/README.md`：明確標 "Implementation Phase: 53.1"
- **21 個檔案 reference state/checkpointer**（loop / prompt_builder / context_mgmt / verification / hitl 等已預期 Cat 7 整合點），但**沒有**concrete impl

### 53.1 為何啟動 phase 53

per `06-phase-roadmap.md`：
- 53.1 — State Mgmt (Cat 7) ← **本 sprint**
- 53.2 — Error Handling (Cat 8)
- 53.3 + 53.4 — Guardrails & Safety (Cat 9)

State Management 是 Cat 8 / Cat 9 的前置：
- Error Handling 需要 Reducer 來 merge 重試後的 partial state
- Guardrails Tripwire 需要 Checkpointer 在 deny 點存 snapshot 供 audit + replay
- HITL pause/resume（Sprint 52.x bundle）已有部分 stub，53.1 將完整化

### Sprint 52.6 carryover bundling

per Sprint 52.6 retrospective (`docs/03-implementation/agent-harness-execution/phase-52-6/sprint-52-6-ci-restoration/retrospective.md`)：

- **#27 umbrella xfail reactivation**（14 tests across 6 files）— 53.1 priority per AI-16
  - 1 個是 Cat 7 native（`test_cancellation_safety.py`）
  - 13 個是 ExecutionContext drift / multi-tenant 測試 — 透過 Reducer pattern 統一 state mutation 後可一併修
- **AI-20**：`pyproject.toml [dev]` extras 補齊 ruff（防 ci.yml command-not-found 再現）— Day 0 trivial
- **AI-21**：`.claude/rules/code-quality.md` cross-platform `# type: ignore[X, unused-ignore]` 章節 — Day 4 docs
- **明確排除**：AI-22（dummy red PR test enforce_admins）→ 單獨 chaos test PR；#29/#30/#31/AI-19 → 53.x+ 非 53.1

### Branch protection 已生效（since Sprint 52.6）

- `enforce_admins=true` block admin bypass；8 status checks + 1 review required
- 53.1 PR 走**正常** review flow（user approve → 我 merge）；**不**重複 52.6 temp-relax bootstrap
- 詳見 `13-deployment-and-devops.md` §Branch Protection

詳見：
- `01-eleven-categories-spec.md` §範疇 7 State Management
- `17-cross-category-interfaces.md` §1.1 (LoopState single-source) + §2.1 (Checkpointer / Reducer ABCs)
- `agent_harness/state_mgmt/README.md`（Sprint 49.1 stub readme）
- Sprint 52.6 retrospective AI-16 / AI-20 / AI-21

---

## User Stories

### US-1：作為 V2 開發者，我希望 `Reducer` 有 production-grade concrete impl，以便所有範疇能透過單一 mutator 安全地更新 LoopState（消除 mutation race + audit trail）

- **驗收**：
  - `DefaultReducer.merge(state, update, source_category=...)` 正確套用 update 並單調 +1 version
  - Audit trail：每次 merge 記錄 `source_category` + `version` + `created_at`
  - Frozen `StateVersion` 確保 version object immutability
  - Unit tests ≥ 90% coverage（per `code-quality.md` Cat 7 target ≥ 85%）
  - 並行 merge 兩個來源（透過 asyncio.Lock）— version 不衝突
- **影響檔案**：`backend/src/agent_harness/state_mgmt/reducer.py` (new)；test files
- **GitHub Issue**：#32（Day 0 建立）

### US-2：作為平台維護者，我希望 `DBCheckpointer` 用 PostgreSQL 持久化 LoopState snapshots + 支援 time-travel，以便 HITL pause / error recovery / debugging replay 可以重建任意 past version

- **驗收**：
  - alembic migration 建 `state_snapshots` table（schema 見 §Tech Spec §US-2）
  - `DBCheckpointer.save(state)` 序列化 LoopState → JSONB → DB
  - `DBCheckpointer.load(version=N)` 反序列化 → LoopState
  - `DBCheckpointer.time_travel(target_version=K)` reload 任一過去版本
  - tenant_id 強制隔離（per `multi-tenant-data.md`）
  - Round-trip test：save → load → 結構等價（含 messages buffer + pending approvals）
- **影響檔案**：
  - `backend/src/agent_harness/state_mgmt/checkpointer.py` (new)
  - `backend/src/agent_harness/state_mgmt/_db_models.py` (new — SQLAlchemy)
  - `backend/alembic/versions/<rev>_add_state_snapshots.py` (new)
  - test files
- **GitHub Issue**：#33

### US-3：作為範疇 7 owner，我希望 transient/durable state split 在 runtime 真的被分離（transient 不入 DB；durable 才持久化），以便 process restart 後可從 durable 重建（而 transient buffers 不浪費 DB storage）

- **驗收**：
  - `DBCheckpointer.save()` 只持久化 `DurableState` + 必要的 transient 摘要（如 `current_turn` / `token_usage_so_far`）
  - `DBCheckpointer.load()` 後 transient buffers (messages list, pending_tool_calls) 為 empty — 由 caller 從 messages history rehydrate
  - Test: save heavy transient state → DB row size < 5KB（per session）
  - 文件 `state_mgmt/README.md` §Transient vs Durable split 升級為實際行為描述（移除 "skeleton" 字眼）
- **影響檔案**：
  - `backend/src/agent_harness/state_mgmt/checkpointer.py`（serialize 邏輯）
  - `backend/src/agent_harness/state_mgmt/README.md`
- **GitHub Issue**：#34

### US-4：作為 AgentLoop owner，我希望 `AgentLoop` 在每個 safe point（after tool / after verify / on HITL pause）自動呼叫 Reducer + Checkpointer，以便狀態變化可追蹤 + 可恢復

- **驗收**：
  - `AgentLoop.run()` 內部 mutation 全部走 `Reducer.merge()`（不再裸寫 `state.transient.messages.append(...)`）
  - 每 turn 結束 + 工具執行後 + verification pass/fail 後呼叫 `Checkpointer.save()`
  - HITL pause 時 force checkpoint（為 resume 做準備）
  - SSE stream 事件含 `state_version`（前端可顯示版本軌跡）
  - 整合 test：3-turn 對話 + 1 tool call + 1 verify → DB 至少 5 個 snapshot
  - **不退步** Cat 1 Loop unit / integration tests（51.x baseline）
- **影響檔案**：
  - `backend/src/agent_harness/orchestrator_loop/loop.py`
  - `backend/src/agent_harness/orchestrator_loop/_abc.py`（如需新接口）
  - 可能 `backend/src/api/v1/chat/router.py`（傳遞 Reducer + Checkpointer dep injection）
  - test files
- **GitHub Issue**：#35

### US-5：作為 #27 umbrella owner，我希望 14 個 pre-existing xfail tests 在 53.1 內 reactivate（移除 xfail decorator + 確保通過），以便 strict=True 的 xfail safety net 不變成永久 dead code

- **驗收**：14 個 tests 移除 `@pytest.mark.xfail`，其中：
  - **必修**（Cat 7 直接相關）：
    - `tests/integration/orchestrator_loop/test_cancellation_safety.py` × 1（透過 US-4 checkpoint-on-cancel pattern）
    - `tests/integration/memory/test_memory_tools_integration.py` × 6（ExecutionContext mismatch → 透過 Reducer 收斂 state mutation 一次性 fix）
    - `tests/integration/memory/test_tenant_isolation.py` × 2（multi-tenant + ExecutionContext）
    - `tests/unit/api/v1/chat/test_router.py::TestMultiTenantIsolation` × 1
    - `tests/e2e/test_lead_then_verify_workflow.py` × 2
  - **CARRY-035**（與 Cat 7 無強相依）：`tests/integration/agent_harness/tools/test_builtin_tools.py` × 2
    - 若 53.1 完成主 5 US 後仍 fail：開新 GitHub issue + retrospective Audit Debt 列為 53.2+；**不**強塞 53.1
- **#27 close**：14 個全 reactivate → close；少數 carryover → keep open with reduced scope
- **影響檔案**：上述 6 test files（移除 xfail decorator + reason）；可能修 source code 對齊新 Reducer pattern
- **GitHub Issue**：#27（既有；本 sprint 大幅推進，可能 close 或 retain partial scope）

### US-6：作為 CI 維護者，我希望 `pyproject.toml [project.optional-dependencies.dev]` 補齊 ruff，以便 ci.yml 的 dev install 不再 silent miss command（Sprint 52.6 retrospective AI-20）

- **驗收**：
  - `pyproject.toml` `[project.optional-dependencies] dev = [..., "ruff>=0.6,<1.0", ...]`
  - `pip install -e .[dev]` after fresh venv → `ruff` 可用
  - ci.yml 的 ruff step 不再依賴 separate install
- **影響檔案**：`backend/pyproject.toml`
- **GitHub Issue**：#36

### US-7：作為文件維護者，我希望 `.claude/rules/code-quality.md` 加 cross-platform `# type: ignore[X, unused-ignore]` 章節，以便其他開發者遇到 Linux/Windows mypy 不一致時有標準解（Sprint 52.6 retrospective AI-21）

- **驗收**：
  - 新章節「Cross-platform mypy: `# type: ignore[X, unused-ignore]` pattern」加入 `.claude/rules/code-quality.md`
  - 含具體例（cross-platform import / Optional unwrap 等常見 case）
  - 含 link to Sprint 52.6 retrospective Q4
- **影響檔案**：`.claude/rules/code-quality.md`
- **GitHub Issue**：#37

---

## Technical Specifications

### US-1 — Reducer concrete impl

**設計**：

```python
# backend/src/agent_harness/state_mgmt/reducer.py
from datetime import datetime, timezone
import asyncio
from typing import Any
from agent_harness._contracts import LoopState, StateVersion, TraceContext
from agent_harness.state_mgmt._abc import Reducer


class DefaultReducer(Reducer):
    """In-memory reducer with monotonic versioning + audit trail.

    Thread-safe via asyncio.Lock. Each merge returns a NEW LoopState
    (frozen StateVersion), preserving immutability semantics.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def merge(
        self,
        state: LoopState,
        update: dict[str, Any],
        *,
        source_category: str,
        trace_context: TraceContext | None = None,
    ) -> LoopState:
        async with self._lock:
            new_version = StateVersion(
                version=state.version.version + 1,
                parent_version=state.version.version,
                created_at=datetime.now(timezone.utc),
                created_by_category=source_category,
            )
            # Apply update (transient or durable fields)
            new_transient = self._merge_transient(state.transient, update.get("transient", {}))
            new_durable = self._merge_durable(state.durable, update.get("durable", {}))
            return LoopState(
                transient=new_transient,
                durable=new_durable,
                version=new_version,
            )

    def _merge_transient(self, current: TransientState, patch: dict) -> TransientState: ...
    def _merge_durable(self, current: DurableState, patch: dict) -> DurableState: ...
```

**Update protocol**（dict-based for flexibility，type-checked via `TypedDict` 或 dataclass per-category）：

```python
{
    "transient": {
        "messages_append": [Message(...)],     # additive
        "current_turn": 5,                     # replace
        "token_usage_so_far": 1234,            # replace
    },
    "durable": {
        "pending_approval_ids_add": [uuid1],   # additive
        "conversation_summary": "...",         # replace
    },
}
```

**Audit trail**：每次 merge 透過 OTel tracer 發 `reducer_merge` event（per `observability-instrumentation.md`）。

**驗證**：
- Unit tests：merge messages append / metadata update / parallel merge 場景
- Coverage ≥ 85% (per code-quality.md Cat 7 target)

**Effort**: 1 day（Day 1）

### US-2 — DBCheckpointer + alembic + time-travel

**Schema**（`alembic/versions/XXXX_add_state_snapshots.py`）：

```sql
CREATE TABLE state_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    version INT NOT NULL,
    parent_version INT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_category TEXT NOT NULL,
    durable_state JSONB NOT NULL,
    transient_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    size_bytes BIGINT NOT NULL,
    UNIQUE (session_id, version),
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX idx_state_snapshots_session_version ON state_snapshots(session_id, version DESC);
CREATE INDEX idx_state_snapshots_tenant ON state_snapshots(tenant_id);
```

**DBCheckpointer 實作**：

```python
class DBCheckpointer(Checkpointer):
    def __init__(self, db_session: AsyncSession): ...
    async def save(self, state: LoopState, *, trace_context=None) -> StateVersion: ...
    async def load(self, *, version: int, trace_context=None) -> LoopState: ...
    async def time_travel(self, *, target_version: int, trace_context=None) -> LoopState: ...
```

- **Tenant 隔離**：每個 query WHERE tenant_id=current_tenant；違反 `multi-tenant-data.md` 規則即 lint fail
- **Serialization**：dataclass → dict → JSONB；datetime UTC ISO；UUID → str
- **Time-travel**：`WHERE session_id=X AND version=K` retrieve；rehydrate transient as empty
- **Tracer**：每 save / load 發 `state_checkpoint_save` / `state_checkpoint_load` span（per `observability-instrumentation.md` §5）

**驗證**：
- Round-trip test (in-memory → DB → load → equality)
- Time-travel test (save v1, v2, v3; load v2; expect v2 state)
- Tenant isolation test (tenant_a save → tenant_b cannot load)
- DB row size < 5KB per snapshot (transient buffer 不入 DB)

**Effort**: 1.5 day（Day 2）

### US-3 — Transient/durable split runtime enforcement

**設計**：
- `DBCheckpointer.save()` 只入 `state.durable` + transient 摘要（current_turn / token_usage_so_far / elapsed_ms）— **不**入 messages buffer / pending_tool_calls
- `DBCheckpointer.load()` rehydrate `TransientState(messages=[], pending_tool_calls=[], current_turn=summary["current_turn"], ...)` — caller responsibility 從 messages history table 補 messages

**Documentation update**：`state_mgmt/README.md` §Transient vs Durable 升級為「實際行為 + 為何這樣設計」；移除 "skeleton" 字眼。

**驗證**：
- Test: 大型 messages list (100 messages) → save → DB row JSONB size < 5KB
- Test: load 後 transient.messages = []，由 test caller 模擬 rehydration

**Effort**: 0.5 day（Day 2 末）

### US-4 — AgentLoop integration

**設計**：

```python
# backend/src/agent_harness/orchestrator_loop/loop.py
class AgentLoop:
    def __init__(
        self,
        chat_client: ChatClient,
        tool_executor: ToolExecutor,
        prompt_builder: PromptBuilder,
        verifier: Verifier,
        reducer: Reducer,           # ← new dep
        checkpointer: Checkpointer,  # ← new dep
        ...
    ): ...

    async def run(self, *, messages, tools, ..., trace_context=None):
        state = LoopState(transient=..., durable=..., version=StateVersion(0, ...))

        async for turn_num in range(max_turns):
            # ... LLM call ...
            response = await self.chat_client.chat(...)

            # MUTATION via Reducer (NOT direct)
            state = await self.reducer.merge(
                state,
                {"transient": {"messages_append": [response.message], "current_turn": turn_num + 1}},
                source_category="orchestrator_loop",
                trace_context=trace_context,
            )

            # CHECKPOINT after LLM call
            await self.checkpointer.save(state, trace_context=trace_context)

            if response.stop_reason == StopReason.TOOL_USE:
                for tc in response.tool_calls:
                    result = await self.tool_executor.execute(tc, ...)
                    state = await self.reducer.merge(
                        state,
                        {"transient": {"messages_append": [result_message]}},
                        source_category="tools",
                    )
                    await self.checkpointer.save(state, ...)  # checkpoint after each tool

            # ... verifier ...
            verify_result = await self.verifier.verify(...)
            state = await self.reducer.merge(
                state,
                {"durable": {"verification_result": verify_result.passed}},
                source_category="verification",
            )
            await self.checkpointer.save(state, ...)
```

**SSE event 升級**：`LoopEvent` 加 `state_version: int` 欄位；前端 `chat-v2.html` / Vue chat-v2 page 顯示版本徵章（optional UI work — 不在本 sprint scope，僅 backend 發 event）

**驗證**：
- Cat 1 既有 unit tests **不退步**（51.x baseline）
- 整合 test：3-turn loop + 1 tool + 1 verify → DB ≥ 5 snapshots
- HITL pause: force checkpoint + version 連續

**Effort**: 1 day（Day 3 上半）

### US-5 — #27 umbrella xfail reactivation

**設計**：
1. **Day 3 下半 + Day 4 上半** 集中處理
2. 每個 test file 按下表處理：

| File | xfail count | 53.1 fix path |
|------|-------------|---------------|
| `test_cancellation_safety.py` | 1 | US-4 checkpoint-on-cancel pattern 直接 cover |
| `test_memory_tools_integration.py` | 6 | Reducer 統一 mutation → ExecutionContext drift 收斂；如 ExecutionContext 接口本身需改，併入本 sprint |
| `test_tenant_isolation.py` | 2 | tenant_id 沿 LoopState.durable 流；US-2 強制 |
| `test_router.py::TestMultiTenantIsolation` | 1 | API 層 tenant context dep injection 對齐 |
| `test_lead_then_verify_workflow.py` | 2 | E2E demo via state checkpoint sequence |
| `test_builtin_tools.py` (CARRY-035) | 2 | 試修；如 > 2 hour 不解 → 開新 issue + Audit Debt |

3. **降規模門檻**：若任 test 修補 > 半天 → 留 xfail + 開新 issue + Audit Debt 記錄；本 sprint 不強制全 14 全綠
4. `gh issue close 27`（如 14/14 reactivate）or `gh issue edit 27 --body "Updated: X/14 reactivated; Y carryover to 53.x"`（部分）

**驗證**：
- pytest baseline：**target** 564 PASS / 0 xfail / 4 skipped / 0 fail（理想）
- **acceptable**：≥ 12/14 reactivate；≤ 2 xfail carryover with new issue
- mypy + LLM SDK leak 不退步

**Effort**: 1.5 day（Day 3 下半 + Day 4 上半）

### US-6 — pyproject.toml dev extras

**設計**：

```toml
# backend/pyproject.toml
[project.optional-dependencies]
dev = [
    "black>=24.0,<26.0",
    "isort>=5.13",
    "flake8>=7.0",
    "mypy>=1.11",
    "ruff>=0.6,<1.0",        # ← add
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    # ... existing
]
```

**驗證**：
- 新 venv: `pip install -e .[dev]` → `ruff --version` works
- ci.yml install step run logs 顯示 ruff 已 installed via [dev]

**Effort**: 15 min（Day 0 trivial）

### US-7 — code-quality.md cross-platform docs

**設計**：

```markdown
## Cross-platform `# type: ignore[X, unused-ignore]` Pattern

### When to use

當同一 import / unwrap 在 Linux 與 Windows mypy 行為不一致（例如 stub 包僅一邊安裝），標準解：

```python
from foo import Bar  # type: ignore[import-not-found, unused-ignore]
```

- `[import-not-found]` 抑制找不到 stub 的 platform
- `[unused-ignore]` 讓另一 platform（有 stub）不抱怨「無用的 ignore」

### Examples
1. Optional dependency: `redis.asyncio` (...)
2. Platform-specific module: `winreg` (...)
3. Conditional Optional unwrap (...)

### Source

per Sprint 52.6 retrospective Q4 (`docs/03-implementation/agent-harness-execution/phase-52-6/sprint-52-6-ci-restoration/retrospective.md`)
```

**Effort**: 0.5 hour（Day 4 docs）

---

## File Change List

### US-1 (Reducer)
- ➕ `backend/src/agent_harness/state_mgmt/reducer.py` (new)
- ➕ `backend/tests/unit/agent_harness/state_mgmt/test_reducer.py` (new)

### US-2 (DBCheckpointer + alembic + time-travel)
- ➕ `backend/src/agent_harness/state_mgmt/checkpointer.py` (new)
- ➕ `backend/src/agent_harness/state_mgmt/_db_models.py` (new — SQLAlchemy)
- ➕ `backend/alembic/versions/XXXX_add_state_snapshots.py` (new)
- ➕ `backend/tests/unit/agent_harness/state_mgmt/test_checkpointer.py` (new)
- ➕ `backend/tests/integration/agent_harness/state_mgmt/test_checkpointer_db.py` (new)
- ✏️ `backend/src/agent_harness/state_mgmt/__init__.py`（re-export concrete classes）

### US-3 (Transient/durable split)
- ✏️ `backend/src/agent_harness/state_mgmt/checkpointer.py`（serialize 邏輯）
- ✏️ `backend/src/agent_harness/state_mgmt/README.md`（升級實際行為描述）

### US-4 (AgentLoop integration)
- ✏️ `backend/src/agent_harness/orchestrator_loop/loop.py`
- 可能 ✏️ `backend/src/agent_harness/orchestrator_loop/_abc.py`（dep injection）
- ✏️ `backend/src/agent_harness/_contracts/events.py`（LoopEvent.state_version）
- 可能 ✏️ `backend/src/api/v1/chat/router.py`（DI: Reducer + Checkpointer）
- ✏️ `backend/tests/integration/agent_harness/orchestrator_loop/test_loop.py`

### US-5 (#27 reactivation)
- ✏️ `backend/tests/e2e/test_lead_then_verify_workflow.py`（移 xfail × 2）
- ✏️ `backend/tests/integration/agent_harness/tools/test_builtin_tools.py`（移 xfail × 2 — CARRY-035；如不解則保留 + 新 issue）
- ✏️ `backend/tests/integration/memory/test_memory_tools_integration.py`（移 xfail × 6）
- ✏️ `backend/tests/integration/memory/test_tenant_isolation.py`（移 xfail × 2）
- ✏️ `backend/tests/integration/orchestrator_loop/test_cancellation_safety.py`（移 xfail × 1）
- ✏️ `backend/tests/unit/api/v1/chat/test_router.py`（移 xfail × 1）
- 可能 ✏️ `backend/src/agent_harness/memory/...`（ExecutionContext 對齐）
- 可能 ✏️ `backend/src/agent_harness/orchestrator_loop/...`（cancellation 對齐）

### US-6 (dev extras)
- ✏️ `backend/pyproject.toml`（[dev] 加 ruff）

### US-7 (cross-platform docs)
- ✏️ `.claude/rules/code-quality.md`（加 §Cross-platform mypy 章節）

---

## Acceptance Criteria

### Sprint-level（必過）

- [ ] 7 user stories 全 ✅（US-1 ~ US-7）
- [ ] `cd backend && python -m pytest --tb=no -q` exit 0：
  - **理想**：564 PASS / 0 xfail / 4 skipped / 0 failed
  - **可接受**：≥ 562 PASS / ≤ 2 xfail (carryover with new issue) / 4 skipped / 0 failed
- [ ] `cd backend && mypy --strict src` 200+ files clean（Cat 7 新增 ~3 files；不退步）
- [ ] `python scripts/lint/check_llm_sdk_leak.py --root backend/src` LLM SDK leak = 0
- [ ] 6 個 V2 lint scripts 全綠（含 cross-category-import / promptbuilder-usage / 其他 49.4-50.1 落地）
- [ ] alembic upgrade head 成功（state_snapshots table 可建）
- [ ] 8 個 active CI workflow 在 53.1 PR 全綠（V2 Lint / Backend CI / CI Pipeline / E2E Tests / Frontend CI + 其他）
- [ ] 6 GitHub issues #32-37 全 close；#27 close (14/14) or 部分 close + reduced scope
- [ ] Cat 7 coverage ≥ 85%（per code-quality.md target）

### 跨切面紀律

- [ ] **Normal merge**：53.1 PR 走正常 review flow（user approve → 我 merge）；**不**用 admin override（branch protection enforce_admins=true 已生效）
- [ ] **No silent xfail**：未解的 test 必須有對應新 GitHub issue + retrospective Audit Debt 記錄
- [ ] **No new Potemkin**：Reducer / Checkpointer 必須在主流量（AgentLoop）真實使用 — US-4 是反 AP-4 守門

### 主流量整合驗收（per W3 process fix #6）

- [ ] **Reducer 真在 AgentLoop 用嗎？** Grep `reducer.merge` 在 `orchestrator_loop/` ≥ 3 處
- [ ] **Checkpointer 真在 AgentLoop 用嗎？** Grep `checkpointer.save` 在 `orchestrator_loop/` ≥ 3 處
- [ ] **State persistence 主流量驗證**：3-turn 對話 E2E test → DB `state_snapshots` table ≥ 5 rows
- [ ] **Time-travel 真用嗎？** test 含 `time_travel(target_version=K)` round-trip
- [ ] **Cat 7 coverage 真達標嗎？** `pytest --cov=src/agent_harness/state_mgmt` ≥ 85%

---

## Deliverables（見 checklist 詳細）

| Day | 工作 |
|-----|------|
| 0 | Setup: branch + plan + checklist + GitHub issues #32-37 + Cat 7 baseline reproduce + AI-20 (US-6) dev extras + #27 catalog 對齐 |
| 1 | **US-1 Reducer concrete impl + unit tests** + commit + push 驗 backend-ci 綠 |
| 2 | **US-2 DBCheckpointer + alembic + time-travel + US-3 transient/durable enforcement** + integration tests + push 驗 ci.yml 綠 |
| 3 | **US-4 AgentLoop integration + #27 reactivation 上半（Cat 7 native + ExecutionContext 6+2）** + push 驗 |
| 4 | **#27 reactivation 下半 + US-7 docs + retrospective + Sprint Closeout + PR open（normal merge）** |

Day 0 預計 2026-05-02 啟動；Day 1-4 預計 5 days（含 Day 4 PR review 等待）。

---

## Dependencies & Risks

### 依賴

- main HEAD `404b8147` (Sprint 52.6 merged) ✅
- Branch protection `enforce_admins=true` 已生效（Sprint 52.6 closeout）
- `gh` CLI authenticated ✅
- PostgreSQL 本地可跑（alembic upgrade）— assumed via dev environment
- 8 個 active CI workflow 全綠 baseline（per Sprint 52.6 retrospective）
- Cat 1 (Loop) / Cat 6 (Output Parser) / Cat 2 (Tools) / Cat 3 (Memory) / Cat 4 (Context) / Cat 5 (Prompt) Phase 50-52 落地（為 US-4 整合提供既有 dependencies）

### 風險

| Risk | Mitigation |
|------|------------|
| **#27 14 xfail 中部分非 Cat 7 直相關，53.1 修不完** | Day 3-4 hard cutoff：≥ 12 reactivate 即可；剩餘開新 issue + Audit Debt + retrospective Q3 砍 scope 透明列出 |
| **DBCheckpointer JSONB serialization 邊界 case**（datetime / UUID / Optional / 嵌套 dataclass）| Day 2 寫 `_serialize.py` 集中；test 含 round-trip with edge values；fallback 用 `pydantic` BaseModel for safety |
| **Reducer asyncio.Lock 引入死鎖**（如 LLM call inside merge） | Reducer.merge 嚴格只做 dataclass 重建；不呼叫外部 IO；test 含並行 merge 模擬 |
| **AgentLoop integration 退步 51.x baseline** | Day 3 push 後立即跑既有 integration test suite；如有退步，rollback + 重設計 dep injection |
| **alembic migration 衝突**（既有 head）| Day 2 確認 `alembic heads` 只 1 個；新 migration parent_revision 對齊；測試 `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` round-trip |
| **CARRY-035 (test_builtin_tools) 無解** | 53.1 不強塞；開新 issue + Audit Debt + 留 xfail；retrospective 列原因 |
| **Branch protection 阻擋本 sprint 緊急 fix** | 不 admin override；如真緊急 → 開新 PR fast-track review；不重複 52.6 temp-relax bootstrap |
| **State snapshot DB 增長過快** | Day 2 加 retention policy TODO（Audit Debt 53.x）：每 session 保留 last 50 snapshots；本 sprint 不實作（YAGNI）|
| **Sprint 過寬** | 砍 scope hierarchy：CARRY-035 → US-7 docs → 部分 #27 → US-3 enforcement docs；core US-1/2/4 不可砍 |

---

## Audit Carryover Section（per W3 process fix #1）

本 sprint 處理：
- **#27 umbrella reactivation**（14 xfail tests；52.6 標記 + bundling at 53.1 priority per AI-16）
- **AI-20 dev extras**（52.6 retrospective）
- **AI-21 cross-platform mypy docs**（52.6 retrospective）

**不在 53.1 scope（明確排除）**：
- AI-22 dummy red PR test enforce_admins → 53.1 完成後單獨 chaos test PR（不 bundle，避免 PR scope 太大）
- #29 V2 frontend E2E setup → 53.x+ frontend track
- #30 sandbox image CI build → 53.x+ infra track
- #31 V2 backend Dockerfile + Deploy workflow → 53.x+ infra track
- AI-19 CI workflow consolidation → 53.x+
- W3-2 SLO carryover (child span / metric emit count) → 53.x+
- 5×3 matrix real PG fixture → 53.x+
- CARRY-033 (Redis-backed PromptCacheManager) → Phase 53.x per 52.2 §AI-12
- CARRY-034 (Sub-agent delegation) → Phase 54.2

### 後續 audit 預期

W4 audit（Sprint 53.1 完成後）：驗證
- DBCheckpointer 在主流量真用（而非 lazy-init never called）
- Reducer 是 sole mutator（grep `state.transient.messages.append` 在 `orchestrator_loop/` 應 = 0）
- #27 reactivate 真完成（pytest output 顯示 14 xfail → 0 xfail）
- Cat 7 coverage ≥ 85% 真達

---

## §10 Process 修補落地檢核

per 52.5 §10 + 52.6 §10：

- [x] Plan template 加 Audit Carryover 段落（本 plan §Audit Carryover Section）
- [ ] Retrospective 加 Audit Debt 段落（Day 4 retrospective.md）
- [ ] GitHub issue per US（#32-37 Day 0 建立；#27 既有）
- [ ] **per W3 process fix #6**：Sprint Retrospective「主流量整合驗收」必答題（Day 4）
- [ ] **52.6 §AI-20 落地**：US-6 (dev extras) Day 0 完成
- [ ] **52.6 §AI-21 落地**：US-7 (cross-platform docs) Day 4 完成
- [ ] **52.5 §AD-2 + 52.6 closeout**：Sprint 53.1 PR 走 normal merge（branch protection 已 enforce_admins=true，技術上不可 bypass；行為紀律配合）

---

## Retrospective 必答（per W3-2 + 52.6 教訓）

Sprint 結束時，retrospective 必須回答：

1. **每個 US 真清了嗎？** 列每 US 對應 commit + verification 結果（含 8 active CI workflow 在 main HEAD 的 run id + status）
2. **跨切面紀律守住了嗎？** admin-merge count（本 sprint 應 = 0；branch protection enforce）/ Cat 7 coverage 數字 / Reducer-as-sole-mutator grep 證據
3. **有任何砍 scope 嗎？** 若有（例 CARRY-035 / 部分 #27），明確列出 + 理由 + 後續排程
4. **GitHub issues #32-37 + #27 全處理了嗎？** 列每個 issue url + close commit hash + #27 14/14 or partial
5. **Audit Debt 累積了嗎？** 本 sprint 期間發現的新 audit-worthy 問題列出（例如 state retention policy / serialization edge case）
6. **主流量整合驗收**：Reducer 在 AgentLoop 真用？Checkpointer 在 AgentLoop 真用？State snapshots DB 真寫入？Time-travel 真 round-trip 過？Cat 7 coverage 真 ≥ 85%？

---

## Sprint Closeout

- [ ] Day 4 retrospective.md 寫好（含必答 6 條）
- [ ] All 6 GitHub issues #32-37 closed；#27 close (14/14) or partial close with reduced reactivate ticket
- [ ] PR 開到 main，title: `feat(state-mgmt, sprint-53-1): Cat 7 State Management — Reducer + DBCheckpointer + AgentLoop integration + #27 14 xfail reactivation`
- [ ] PR body 含每 US verification 證據 + workflow run id + Cat 7 coverage 數字 + Reducer-as-sole-mutator grep 證據
- [ ] **PR 用正常 merge**（NOT admin override）— branch protection enforce_admins=true 自動強制
- [ ] V2 milestone 更新：13/22 sprints (59%)
- [ ] Memory update：phase 53 啟動 + Cat 7 Level 3 達成 + #27 closure status

---

**權威排序**：`agent-harness-planning/` 19 docs > 本 plan > V1 文件 / 既有代碼。本 plan 對齊 `01-eleven-categories-spec.md` §範疇 7 + `17-cross-category-interfaces.md` §1.1 / §2.1 + Sprint 49.1 stub + Sprint 52.6 retrospective AI-16 / AI-20 / AI-21。
