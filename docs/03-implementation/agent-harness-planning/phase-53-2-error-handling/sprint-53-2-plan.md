# Sprint 53.2 — Error Handling (Cat 8)

**Phase**: phase-53-2-error-handling
**Sprint**: 53.2
**Duration**: 5 days (Day 0-4 standard layout)
**Status**: TODO → IN PROGRESS → DONE
**Created**: 2026-05-03
**Owner**: User-spawned session 2026-05-03+ (rename: v2-rebuild-main-session-20260503)
**Branch**: feature/sprint-53-2-error-handling (off main `aaa3dd75`)

---

## Sprint Goal

實作 V2 範疇 8 (Error Handling)：把 `01-eleven-categories-spec.md` §範疇 8 規格落地為**生產級實作** — 4-class `ErrorCategory` 分類器 + per-tool/per-error-type `RetryPolicy` 矩陣（取代寫死 max=2）+ per-provider `CircuitBreaker` + per-tenant `ErrorBudget` + `ErrorTerminator`（明確區別於範疇 9 Tripwire）+ AgentLoop LLM-recoverable error 回注機制。同時 bundle 53.x 早期 carryover：AD-Cat7-2 #38 flaky test_router fixture leak、AD-CI-1 CI Pipeline push-to-main pre-existing failure、Sprint 53.1 closeout bookkeeping 2 commits（branch `docs/sprint-53-1-closeout-bookkeeping`）。**這是 V2 第 14 sprint（59% → 64%）**，phase 53 第 2 sprint。

---

## Background

### Cat 8 history

- **Sprint 49.1 (Phase 49 Foundation)** 落地 ABC stub：
  - `backend/src/agent_harness/_contracts/errors.py`：`ErrorCategory` enum stub (TRANSIENT / LLM_RECOVERABLE / USER_FIXABLE / UNEXPECTED)、`RetryPolicy` stub、`CircuitBreaker` stub、`ErrorBudget` stub、`ErrorTerminator` stub
  - `backend/src/agent_harness/error_handling/_abc.py`：`ErrorClassifier` (classify) + `RetryStrategy` (should_retry / get_delay) + `CircuitBreaker` (record / is_open / half_open) ABCs
  - `backend/src/agent_harness/error_handling/README.md`：明確標 "Implementation Phase: 53.2"
- **17 個檔案 reference error_handling**（loop / tools / verification / adapters 等已預期 Cat 8 整合點），但**沒有**concrete impl

### 53.2 為何啟動 phase 53.2

per `06-phase-roadmap.md` §Phase 53：
- 53.1 — State Mgmt (Cat 7) ✅ COMPLETE 2026-05-02 (PR #39 → main aaa3dd75)
- 53.2 — Error Handling (Cat 8) ← **本 sprint**
- 53.3 — Guardrails 核心 (Cat 9)
- 53.4 — Governance Frontend + V1 HITL/Risk 遷移

Error Handling 是 Cat 9 / Cat 11 的前置：
- Guardrails (Cat 9) Tripwire 與 ErrorTerminator 邊界明確（per 17.md §6）— 必須先有 ErrorTerminator
- Subagent Orchestration (Cat 11) 需要 Cat 8 RetryPolicy / CircuitBreaker 在 subagent 失敗時做正確決策
- Verification (Cat 10) self-correction loop 失敗時透過 Cat 8 LLM-recoverable 回注
- Cat 7 Reducer/Checkpointer 已就緒（53.1 落地）— Cat 8 可以利用 checkpointed state 做 retry-with-state-restore

### Sprint 53.1 carryover bundling (53.x 早期)

per Sprint 53.1 retrospective (`docs/03-implementation/agent-harness-execution/phase-53-1/sprint-53-1-state-mgmt/retrospective.md` §Audit Debt)：

- **AD-Cat7-2** test_router multi-tenant flaky in full suite (#38) — 53.x early per retrospective Q5
  - Passes in isolation；fails in full suite (suspected fixture/registry leak)
  - 1 個 xfail strict=False；本 sprint 53.2 Day 0 reproduce + Day 4 fix
- **AD-CI-1** CI Pipeline workflow push-to-main pre-existing failure (since 0ec64c77)
  - 已 8/8 active CI workflow 在 PR-level 全綠；但 push-to-main level 之 CI Pipeline workflow run history 顯示 fail；retrospective 列為 53.x cleanup
- **53.1 closeout bookkeeping branch**：`docs/sprint-53-1-closeout-bookkeeping` HEAD `41aec40f` 含 2 commits
  - 處置選項 (b) 推薦：**bundle 進 53.2 first PR**（避免 3rd temp-relax 稀釋 branch protection 紀律）

### Branch protection 已生效（since Sprint 52.6）

- `enforce_admins=true` block admin bypass；8 status checks + 1 review required
- 53.2 PR 走**正常** review flow（user approve → 我 merge）；**不**走 temp-relax bootstrap
- 53.1 走 2nd temp-relax（PR #39）— 53.2 必須 zero temp-relax
- 詳見 `13-deployment-and-devops.md` §Branch Protection

詳見：
- `01-eleven-categories-spec.md` §範疇 8 Error Handling
- `17-cross-category-interfaces.md` §1.1 ErrorPolicy / CircuitBreaker single-source + §6 Tripwire 邊界（範疇 8 vs 9）
- `agent_harness/error_handling/README.md`（Sprint 49.1 stub readme）
- Sprint 53.1 retrospective AD-Cat7-2 / AD-CI-1
- `06-phase-roadmap.md` §Sprint 53.2 Deliverables

---

## User Stories

### US-1：作為 V2 開發者，我希望 `ErrorClassifier` 把任意 Exception 對映到 4 類 `ErrorCategory`，以便上層 RetryPolicy / CircuitBreaker / ErrorTerminator 能據此做正確決策

- **驗收**：
  - `DefaultErrorClassifier.classify(error: Exception, context: ErrorContext) -> ErrorCategory` 對映：
    - `TRANSIENT`：網路（aiohttp.ClientConnectionError / asyncio.TimeoutError / ConnectionError）/ 5xx
    - `LLM_RECOVERABLE`：tool 執行失敗（ToolExecutionError）/ schema validation fail（ValidationError）
    - `USER_FIXABLE`：認證失敗（AuthenticationError）/ 缺資料（MissingDataError）— 觸發 HITL
    - `UNEXPECTED`：bug / unrecognized exception / panic
  - Unit tests ≥ 90% coverage（per `code-quality.md` Cat 8 target ≥ 80%）
  - Per-error-type registry pattern（`register(exc_class, category)`）— 各範疇可註冊自己的 exception
  - `ErrorContext` 含 source_category / tool_name / provider / attempt_num / state_version
- **影響檔案**：`backend/src/agent_harness/error_handling/classifier.py` (new)；test files
- **GitHub Issue**：#40（Day 0 建立）

### US-2：作為 Tool / Adapter caller，我希望 `RetryPolicy` 是 per-tool / per-error-type 矩陣（不再寫死 max_attempts=2），以便不同失敗類型有不同重試策略

- **驗收**：
  - `RetryPolicyMatrix.get_policy(tool_name: str | None, error_category: ErrorCategory) -> RetryConfig` 返回 `(max_attempts, backoff_base, backoff_max, jitter)`
  - 預設矩陣（per spec）：
    - TRANSIENT × any tool: max=3, base=1.0, max_delay=30.0, jitter=True
    - LLM_RECOVERABLE × any tool: max=2 (回注 LLM 為主, retry 次要)
    - USER_FIXABLE × any tool: max=0 (不 retry, 直接 HITL)
    - UNEXPECTED × any tool: max=0 (不 retry, bubble up)
  - YAML config 載入支援（`backend/config/retry_policies.yaml`）— per-tool override
  - Exponential backoff with jitter：`delay = min(backoff_max, backoff_base * 2^attempt) * (1 + random(-jitter, +jitter))`
  - Unit tests cover 4 categories × 2-3 tools × edge cases
  - **`ErrorRetried` event** emit per `17.md §3 Loop events`
- **影響檔案**：
  - `backend/src/agent_harness/error_handling/retry.py` (new)
  - `backend/config/retry_policies.yaml` (new — default matrix)
  - test files
- **GitHub Issue**：#41

### US-3：作為平台維護者，我希望 `CircuitBreaker` per-provider 在 LLM/外部服務連續失敗達 threshold 時自動 OPEN（半開後試探），以便保護下游 + 配合原則 2 multi-provider routing

- **驗收**：
  - `ProviderCircuitBreaker(provider: str, threshold: int = 5, recovery_timeout: float = 60.0, half_open_max_calls: int = 1)` 三態 (CLOSED / OPEN / HALF_OPEN)
  - `record_success() / record_failure()` 更新狀態
  - `is_open() -> bool`：CLOSED → 連續 N 次失敗 → OPEN（拒絕 call）；timeout 後 → HALF_OPEN（允許 1 次試探）；成功 → CLOSED；失敗 → OPEN
  - Per-provider state 隔離（`azure_openai` 與 `anthropic` 各自一個 instance）
  - Adapter 層接入：`adapters/_base/chat_client.py` 在 `chat()` 前 check `is_open()`；若 OPEN → 拋 `CircuitOpenError`（被 ErrorClassifier 分類為 TRANSIENT 或 ErrorTerminator 終止）
  - Detection time < 5s SLO（per spec）
  - Unit tests cover 三態轉換 + 並行 record + adapter 整合
- **影響檔案**：
  - `backend/src/agent_harness/error_handling/circuit_breaker.py` (new)
  - `backend/src/adapters/_base/chat_client.py`（pre-call check hook）
  - `backend/src/adapters/azure_openai/adapter.py`（注入 circuit breaker dep）
  - test files
- **GitHub Issue**：#42

### US-4：作為多租戶平台 owner，我希望 `ErrorBudget` per-tenant per-day/month，以便超支租戶被拒絕新請求（防 runaway loop 燒費 + 公平資源分配）

- **驗收**：
  - `TenantErrorBudget(tenant_id, max_errors_per_day, max_errors_per_month)` 持久化於 Redis（counter + TTL）or DB（fallback）
  - `record(tenant_id, error_category)` 增量；`is_exceeded(tenant_id) -> bool` 檢查
  - YAML config per-tenant override（`backend/config/error_budgets.yaml`）
  - Default: per_day=1000, per_month=20000（保守估）
  - 超支 → ErrorTerminator 觸發 + ChatResponse content 含 retry-after hint
  - Calculation p95 < 50ms SLO
  - Multi-tenant 隔離測試：tenant_a 超支 → tenant_b 不受影響
- **影響檔案**：
  - `backend/src/agent_harness/error_handling/budget.py` (new)
  - `backend/config/error_budgets.yaml` (new)
  - test files
- **GitHub Issue**：#43

### US-5：作為 Loop owner，我希望 `ErrorTerminator`（明確區別於 Cat 9 Tripwire）在 `ErrorBudget 超支 / CircuitBreaker open / fatal exception` 時立即終止 loop，以便系統不會持續燒費 + 用戶得到明確錯誤訊息

- **驗收**：
  - `ErrorTerminator.should_terminate(error_category, context, state) -> TerminationDecision` 返回 `(terminate: bool, reason: TerminationReason)`
  - 4 種終止原因：`BUDGET_EXCEEDED` / `CIRCUIT_OPEN` / `FATAL_EXCEPTION` / `MAX_RETRIES_EXHAUSTED`
  - `TerminationReason` enum（**non-Tripwire**；per 17.md §6 邊界裁定）
  - Loop 接 `ErrorTerminator` decision → emit `LoopTerminated(reason=...)` event → 結束
  - Cat 7 Checkpointer 在 termination 前自動 save state（為 debug / replay）
  - Unit tests cover 4 終止原因 + ErrorTerminator vs Tripwire 邊界（不衝突）
- **影響檔案**：
  - `backend/src/agent_harness/error_handling/terminator.py` (new)
  - test files
- **GitHub Issue**：#44

### US-6：作為 AgentLoop owner，我希望 LLM-recoverable error 自動回注為 `ToolMessage` 給 LLM（不 raise），且其他類別錯誤透過 ErrorClassifier → RetryPolicy → CircuitBreaker → ErrorTerminator 鏈路處理，以便 Loop 真實使用 Cat 8 整套機制

- **驗收**：
  - `AgentLoop.run()` tool execution exception path：
    1. `error_classifier.classify(exc, ctx)` → category
    2. 若 LLM_RECOVERABLE：構造 `ToolResult(is_error=True, content=f"Error: {exc}. Please adjust.")` → `state = reducer.merge(...)` → 繼續 loop
    3. 若 TRANSIENT：`retry_policy.get_policy(...)` → backoff → 重試 N 次；用盡 → 升級 USER_FIXABLE 或 UNEXPECTED
    4. 若 USER_FIXABLE：觸發 HITL（透過 §HITL 中央化 stub；53.4 完整）
    5. 若 UNEXPECTED：log + alert + bubble up
  - 每次 retry → emit `ErrorRetried` event
  - 終止條件: ErrorTerminator → emit `LoopTerminated` event → 結束
  - 整合 test：3 個 scenario（LLM_recoverable 回注 / TRANSIENT 重試成功 / FATAL terminator）
  - **不退步** Cat 1/7 既有 tests（51.x + 53.1 baseline）
- **影響檔案**：
  - `backend/src/agent_harness/orchestrator_loop/loop.py`
  - `backend/src/agent_harness/_contracts/events.py`（`ErrorRetried` + `LoopTerminated` events）
  - 可能 `backend/src/api/v1/chat/router.py`（DI: classifier + retry + circuit + budget + terminator）
  - test files
- **GitHub Issue**：#45

### US-7：作為 53.1 carryover owner，我希望 #38 flaky test_router multi-tenant 在 full suite 通過（不再 xfail），以便 V2 lint baseline 真綠（AD-Cat7-2）

- **驗收**：
  - reproduce flaky behavior：full suite vs isolation 對比 → 確認 fixture / registry leak 點
  - fix root cause（推測：session-level fixture 跨 test 殘留 state；或 router DI registry 未 reset）
  - 移除 `@pytest.mark.xfail` decorator + reason
  - `pytest tests/unit/api/v1/chat/test_router.py::TestMultiTenantIsolation -v` 通過 in isolation
  - `pytest --random-order tests/` × 3 run 全綠（驗證非 order-dependent）
  - 關閉 GitHub issue #38
- **影響檔案**：
  - `backend/tests/unit/api/v1/chat/test_router.py`
  - 可能 `backend/tests/conftest.py`（fixture isolation fix）
  - 可能 `backend/src/api/v1/chat/router.py`（DI registry reset hook）
- **GitHub Issue**：#38（既有；本 sprint close）

### US-8：作為 CI 維護者，我希望 AD-CI-1 CI Pipeline workflow push-to-main 失敗修復（pre-existing since 0ec64c77），以便 main HEAD 真綠 + push 後不再有紅 X

- **驗收**：
  - 診斷 CI Pipeline workflow（`.github/workflows/ci.yml`）push-to-main 失敗根因
  - 推測：alembic upgrade head 失敗 / pytest fixture 缺 / env 變數未設 / 等等
  - 實施 fix（可能改 workflow YAML / 可能改 setup script）
  - Push to feature branch 確認 ci.yml 在 push event 觸發後綠
  - Merge 53.2 後 main HEAD push event 也綠
- **影響檔案**：
  - 可能 `.github/workflows/ci.yml`
  - 可能 `backend/scripts/ci_setup.sh` or alembic config
- **GitHub Issue**：#46（Day 0 建立 — AD-CI-1 ticket）

### US-9：作為 53.1 closeout bookkeeping owner，我希望 `docs/sprint-53-1-closeout-bookkeeping` branch 2 commits bundle 進 53.2 first PR，以便不需開獨立 PR + 不需 3rd temp-relax bootstrap

- **驗收**：
  - cherry-pick 或 merge `docs/sprint-53-1-closeout-bookkeeping` 2 commits 到 53.2 feature branch
  - Verify content：post-merge bookkeeping (memory entry update) + AD-CI-1 entry add
  - Push to feature branch；CI 綠
  - 53.2 PR body 註明 includes 53.1 closeout bookkeeping bundle
  - PR merge 後 delete remote branch `docs/sprint-53-1-closeout-bookkeeping`
- **影響檔案**：
  - 視 closeout branch 內容（推測：`memory/MEMORY.md` + `claudedocs/...` audit doc）
- **GitHub Issue**：#47（Day 0 建立 — bundle ticket）

---

## Technical Specifications

### US-1 — ErrorClassifier concrete impl

**設計**：

```python
# backend/src/agent_harness/error_handling/classifier.py
from dataclasses import dataclass, field
from typing import Type
from agent_harness._contracts import ErrorCategory, TraceContext
from agent_harness.error_handling._abc import ErrorClassifier


@dataclass(frozen=True)
class ErrorContext:
    source_category: str  # "tools" / "adapters" / "verification" / etc
    tool_name: str | None = None
    provider: str | None = None
    attempt_num: int = 1
    state_version: int | None = None


class DefaultErrorClassifier(ErrorClassifier):
    """Maps exceptions to ErrorCategory via registry pattern."""

    def __init__(self) -> None:
        self._registry: dict[Type[BaseException], ErrorCategory] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        # TRANSIENT
        from aiohttp import ClientConnectionError
        import asyncio
        self._registry[ClientConnectionError] = ErrorCategory.TRANSIENT
        self._registry[asyncio.TimeoutError] = ErrorCategory.TRANSIENT
        self._registry[ConnectionError] = ErrorCategory.TRANSIENT
        # LLM_RECOVERABLE
        from agent_harness.tools._abc import ToolExecutionError
        self._registry[ToolExecutionError] = ErrorCategory.LLM_RECOVERABLE
        # USER_FIXABLE
        from agent_harness._contracts.errors import AuthenticationError, MissingDataError
        self._registry[AuthenticationError] = ErrorCategory.USER_FIXABLE
        self._registry[MissingDataError] = ErrorCategory.USER_FIXABLE
        # UNEXPECTED — fallback for unregistered

    def classify(
        self,
        error: BaseException,
        context: ErrorContext,
        *,
        trace_context: TraceContext | None = None,
    ) -> ErrorCategory:
        for exc_type in type(error).__mro__:
            if exc_type in self._registry:
                return self._registry[exc_type]
        return ErrorCategory.UNEXPECTED

    def register(self, exc_class: Type[BaseException], category: ErrorCategory) -> None:
        self._registry[exc_class] = category
```

**驗證**：
- Unit tests：4 categories 各至少 2 種 exception
- Edge cases：unregistered exception → UNEXPECTED
- Inheritance MRO walk：subclass of registered → parent's category
- Coverage ≥ 90%

**Effort**: 0.75 day（Day 1 上半）

### US-2 — RetryPolicy matrix + ErrorRetried event

**設計**：

```python
# backend/src/agent_harness/error_handling/retry.py
import asyncio
import random
from dataclasses import dataclass
from agent_harness._contracts import ErrorCategory


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int
    backoff_base: float
    backoff_max: float
    jitter: bool


class RetryPolicyMatrix:
    """Per-(tool, category) RetryConfig lookup."""

    def __init__(self, matrix: dict[tuple[str | None, ErrorCategory], RetryConfig]) -> None:
        self._matrix = matrix
        self._defaults = self._build_defaults()

    def _build_defaults(self) -> dict[ErrorCategory, RetryConfig]:
        return {
            ErrorCategory.TRANSIENT: RetryConfig(max_attempts=3, backoff_base=1.0, backoff_max=30.0, jitter=True),
            ErrorCategory.LLM_RECOVERABLE: RetryConfig(max_attempts=2, backoff_base=0.5, backoff_max=5.0, jitter=False),
            ErrorCategory.USER_FIXABLE: RetryConfig(max_attempts=0, backoff_base=0, backoff_max=0, jitter=False),
            ErrorCategory.UNEXPECTED: RetryConfig(max_attempts=0, backoff_base=0, backoff_max=0, jitter=False),
        }

    def get_policy(
        self,
        tool_name: str | None,
        error_category: ErrorCategory,
    ) -> RetryConfig:
        # Specific (tool, cat) override → cat default
        return self._matrix.get((tool_name, error_category), self._defaults[error_category])

    @classmethod
    def from_yaml(cls, path: str) -> "RetryPolicyMatrix": ...


def compute_backoff(config: RetryConfig, attempt: int) -> float:
    base = min(config.backoff_max, config.backoff_base * (2 ** attempt))
    if config.jitter:
        jitter_factor = random.uniform(-0.1, 0.1)
        return base * (1 + jitter_factor)
    return base
```

**YAML config**：

```yaml
# backend/config/retry_policies.yaml
defaults:
  TRANSIENT:
    max_attempts: 3
    backoff_base: 1.0
    backoff_max: 30.0
    jitter: true
  LLM_RECOVERABLE:
    max_attempts: 2
    backoff_base: 0.5
    backoff_max: 5.0
    jitter: false
  USER_FIXABLE:
    max_attempts: 0
  UNEXPECTED:
    max_attempts: 0

per_tool:
  salesforce_query:
    TRANSIENT:
      max_attempts: 5  # Salesforce 較易 transient fail，多 retry
      backoff_max: 60.0
```

**ErrorRetried event** (per 17.md §3)：

```python
# backend/src/agent_harness/_contracts/events.py
@dataclass(frozen=True)
class ErrorRetried:
    """範疇 8 emit；Cat 1 Loop 接收。"""
    error_category: ErrorCategory
    tool_name: str | None
    attempt_num: int
    delay_seconds: float
    original_exception: str  # repr
```

**驗證**：
- Unit tests：4 categories × 2 tools × backoff calculation
- Concurrency：parallel retry 不 starve；SLO retry overhead < 100ms per attempt

**Effort**: 0.75 day（Day 1 下半）

### US-3 — CircuitBreaker per-provider

**設計**：

```python
# backend/src/agent_harness/error_handling/circuit_breaker.py
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStats:
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_at: datetime | None = None
    half_open_call_count: int = 0


class ProviderCircuitBreaker:
    def __init__(
        self,
        provider: str,
        *,
        threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.provider = provider
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    async def is_open(self) -> bool:
        async with self._lock:
            now = datetime.now(timezone.utc)
            if self._stats.state == CircuitState.OPEN:
                if (now - self._stats.last_failure_at).total_seconds() >= self.recovery_timeout:
                    self._stats.state = CircuitState.HALF_OPEN
                    self._stats.half_open_call_count = 0
                    return False  # 允許 half-open call
                return True
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._stats.consecutive_failures = 0
            self._stats.state = CircuitState.CLOSED

    async def record_failure(self) -> None:
        async with self._lock:
            self._stats.consecutive_failures += 1
            self._stats.last_failure_at = datetime.now(timezone.utc)
            if self._stats.consecutive_failures >= self.threshold:
                self._stats.state = CircuitState.OPEN


class CircuitOpenError(Exception):
    """Raised when call attempted while circuit OPEN."""
```

**Adapter 層整合**：

```python
# backend/src/adapters/_base/chat_client.py
class ChatClient:
    def __init__(self, ..., circuit_breaker: ProviderCircuitBreaker | None = None):
        self._circuit_breaker = circuit_breaker

    async def chat(self, ...) -> ChatResponse:
        if self._circuit_breaker and await self._circuit_breaker.is_open():
            raise CircuitOpenError(f"Circuit OPEN for {self._circuit_breaker.provider}")
        try:
            response = await self._do_chat(...)
            if self._circuit_breaker:
                await self._circuit_breaker.record_success()
            return response
        except Exception:
            if self._circuit_breaker:
                await self._circuit_breaker.record_failure()
            raise
```

**驗證**：
- 三態轉換 unit tests（CLOSED → OPEN → HALF_OPEN → CLOSED）
- Concurrent record（asyncio.gather × 10）— state 一致
- Adapter 整合 test：模擬 N 次失敗 → adapter 拋 `CircuitOpenError`
- SLO detection time < 5s（CLOSED→OPEN within threshold failures）

**Effort**: 1 day（Day 2 上半）

### US-4 — ErrorBudget per-tenant

**設計**：

```python
# backend/src/agent_harness/error_handling/budget.py
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID


class BudgetStore(Protocol):
    """Backed by Redis (production) or DB (fallback)."""
    async def increment(self, key: str, ttl_seconds: int) -> int: ...
    async def get(self, key: str) -> int: ...


class TenantErrorBudget:
    def __init__(
        self,
        store: BudgetStore,
        *,
        max_per_day: int = 1000,
        max_per_month: int = 20000,
    ) -> None:
        self._store = store
        self.max_per_day = max_per_day
        self.max_per_month = max_per_month

    def _day_key(self, tenant_id: UUID) -> str:
        date = datetime.now(timezone.utc).date().isoformat()
        return f"error_budget:{tenant_id}:day:{date}"

    def _month_key(self, tenant_id: UUID) -> str:
        ym = datetime.now(timezone.utc).strftime("%Y-%m")
        return f"error_budget:{tenant_id}:month:{ym}"

    async def record(self, tenant_id: UUID, error_category: ErrorCategory) -> None:
        if error_category == ErrorCategory.UNEXPECTED:
            return  # bug 不計入 budget
        await self._store.increment(self._day_key(tenant_id), ttl_seconds=86400 * 2)
        await self._store.increment(self._month_key(tenant_id), ttl_seconds=86400 * 32)

    async def is_exceeded(self, tenant_id: UUID) -> tuple[bool, str | None]:
        day_count = await self._store.get(self._day_key(tenant_id))
        if day_count > self.max_per_day:
            return True, f"daily_limit ({day_count}/{self.max_per_day})"
        month_count = await self._store.get(self._month_key(tenant_id))
        if month_count > self.max_per_month:
            return True, f"monthly_limit ({month_count}/{self.max_per_month})"
        return False, None
```

**Multi-tenant 隔離**：
- 每個 key 帶 tenant_id；Redis namespace 隔離
- Tenant override：`backend/config/error_budgets.yaml` per-tenant 自訂上限

**驗證**：
- 隔離 test：tenant_a 超支 → tenant_b 未受影響
- TTL test：跨 day/month 邊界自動 reset
- SLO p95 < 50ms

**Effort**: 0.75 day（Day 2 下半）

### US-5 — ErrorTerminator

**設計**：

```python
# backend/src/agent_harness/error_handling/terminator.py
from dataclasses import dataclass
from enum import Enum


class TerminationReason(Enum):
    BUDGET_EXCEEDED = "budget_exceeded"
    CIRCUIT_OPEN = "circuit_open"
    FATAL_EXCEPTION = "fatal_exception"
    MAX_RETRIES_EXHAUSTED = "max_retries_exhausted"
    # 注意：NOT 包含 Tripwire reasons（per 17.md §6 Tripwire 屬範疇 9）


@dataclass(frozen=True)
class TerminationDecision:
    terminate: bool
    reason: TerminationReason | None
    detail: str | None


class ErrorTerminator:
    def __init__(
        self,
        *,
        circuit_breakers: dict[str, ProviderCircuitBreaker],
        error_budget: TenantErrorBudget,
    ) -> None:
        self._circuit_breakers = circuit_breakers
        self._error_budget = error_budget

    async def should_terminate(
        self,
        error: BaseException,
        error_category: ErrorCategory,
        context: ErrorContext,
        tenant_id: UUID,
    ) -> TerminationDecision:
        # Budget exceeded
        exceeded, detail = await self._error_budget.is_exceeded(tenant_id)
        if exceeded:
            return TerminationDecision(True, TerminationReason.BUDGET_EXCEEDED, detail)
        # Circuit open
        if context.provider:
            breaker = self._circuit_breakers.get(context.provider)
            if breaker and await breaker.is_open():
                return TerminationDecision(True, TerminationReason.CIRCUIT_OPEN, f"provider={context.provider}")
        # Fatal exception (UNEXPECTED 且非 LLM_RECOVERABLE)
        if error_category == ErrorCategory.UNEXPECTED:
            return TerminationDecision(True, TerminationReason.FATAL_EXCEPTION, repr(error))
        # Max retries (caller 傳入 attempt_num)
        if context.attempt_num >= 5:  # global hard cap
            return TerminationDecision(True, TerminationReason.MAX_RETRIES_EXHAUSTED, f"attempt={context.attempt_num}")
        return TerminationDecision(False, None, None)
```

**`LoopTerminated` event**：

```python
@dataclass(frozen=True)
class LoopTerminated:
    reason: TerminationReason
    detail: str | None
    last_state_version: int | None  # Cat 7 checkpoint reference
```

**驗證**：
- 4 終止原因各一 unit test
- ErrorTerminator vs Tripwire 邊界（不衝突）：grep `Tripwire` 在 `error_handling/` 目錄 = 0 hits
- Loop 整合 test：模擬 budget 超支 → termination → state checkpointed → SSE 事件含 reason

**Effort**: 0.75 day（Day 3 上半）

### US-6 — AgentLoop integration

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
        reducer: Reducer,
        checkpointer: Checkpointer,
        # Cat 8 deps (opt-in similar to Cat 7 pattern)
        error_classifier: ErrorClassifier | None = None,
        retry_policy: RetryPolicyMatrix | None = None,
        circuit_breakers: dict[str, ProviderCircuitBreaker] | None = None,
        error_budget: TenantErrorBudget | None = None,
        error_terminator: ErrorTerminator | None = None,
        ...
    ): ...

    async def _execute_tool_with_error_handling(
        self,
        tool_call: ToolCall,
        state: LoopState,
        trace_context: TraceContext,
    ) -> tuple[LoopState, ToolResult | None]:
        attempt = 0
        last_exc: BaseException | None = None

        while True:
            attempt += 1
            try:
                result = await self.tool_executor.execute(tool_call, ...)
                return state, result  # success
            except BaseException as exc:
                last_exc = exc
                if not self._error_classifier:
                    raise  # opt-out path

                ctx = ErrorContext(
                    source_category="tools",
                    tool_name=tool_call.tool_name,
                    attempt_num=attempt,
                    state_version=state.version.version,
                )
                category = self._error_classifier.classify(exc, ctx)

                # Record budget
                if self._error_budget:
                    await self._error_budget.record(state.durable.tenant_id, category)

                # Check terminator
                if self._error_terminator:
                    decision = await self._error_terminator.should_terminate(exc, category, ctx, state.durable.tenant_id)
                    if decision.terminate:
                        await self.checkpointer.save(state, trace_context=trace_context)
                        await self._emit_loop_terminated(decision)
                        return state, None  # signal loop end

                # LLM_RECOVERABLE: 回注
                if category == ErrorCategory.LLM_RECOVERABLE:
                    error_result = ToolResult(
                        tool_call_id=tool_call.id,
                        is_error=True,
                        content=f"Error: {exc}. Please adjust your approach.",
                    )
                    return state, error_result  # 回 loop，將被 append to messages

                # TRANSIENT: retry with backoff
                if category == ErrorCategory.TRANSIENT and self._retry_policy:
                    config = self._retry_policy.get_policy(tool_call.tool_name, category)
                    if attempt <= config.max_attempts:
                        delay = compute_backoff(config, attempt)
                        await self._emit_error_retried(category, tool_call.tool_name, attempt, delay, exc)
                        await asyncio.sleep(delay)
                        continue  # retry

                # USER_FIXABLE / UNEXPECTED / retries exhausted: bubble or HITL
                if category == ErrorCategory.USER_FIXABLE:
                    # TODO Phase 53.4: trigger HITL via central HITL Manager
                    raise  # for now, bubble up
                raise  # UNEXPECTED bubbles
```

**驗證**：
- Cat 1/7 既有 tests **不退步**（51.x + 53.1 baseline）
- 整合 test 3 scenario：
  - LLM_RECOVERABLE 回注 → loop 繼續 + messages 含 error result
  - TRANSIENT 重試 2 次成功 → ErrorRetried event × 2 emit
  - FATAL → ErrorTerminator → LoopTerminated event + checkpoint saved
- Opt-in pattern：所有 Cat 8 deps 傳 None → fallback 至 raise（51.x 行為保留）

**Effort**: 1.25 day（Day 3 下半 + Day 4 上半）

### US-7 — #38 flaky test_router fix (AD-Cat7-2)

**設計**：

1. **Day 0 reproduce**：
   - `pytest tests/unit/api/v1/chat/test_router.py::TestMultiTenantIsolation` (isolation) → expect PASS
   - `pytest tests/unit/api/v1/chat/test_router.py` (full file) → check
   - `pytest tests/unit/` (full unit suite) → check
   - `pytest tests/` (full suite) → check
   - 對比結果定位 fixture / registry leak 點
2. **Day 4 fix**：
   - 推測根因 1：session-level fixture 跨 test 殘留 tenant context → fix scope to function
   - 推測根因 2：FastAPI router DI 容器未在 test 之間 reset → 加 conftest fixture autouse reset
   - 推測根因 3：global state in `agent_harness/error_handling/` (新增的 RetryPolicy / CircuitBreaker registry) → 確保 per-test instance
3. **驗證**：
   - 移除 `@pytest.mark.xfail`
   - `pytest --random-order tests/ -x` × 3 run 全綠
   - 關閉 #38

**Effort**: 0.5 day（Day 0 reproduce + Day 4 上半 fix）

### US-8 — AD-CI-1 CI Pipeline push-to-main fix

**設計**：

1. **Day 0 診斷**：
   - `gh run list --workflow ci.yml --branch main --limit 10` 看最近 push event runs
   - `gh run view <id> --log-failed` 找具體失敗點
2. **常見失敗模式**：
   - alembic upgrade head 失敗（推測 Sprint 49.2 之後 schema 衝突；53.1 已部分修但未涵蓋 push event）
   - Pytest fixture 缺（push event 不跑 PR-only 設定）
   - env 變數未設（GitHub secrets 未在 main push 觸發時注入）
3. **修復策略**：
   - Option A: 修 ci.yml workflow YAML（push 與 PR triggers 對齊）
   - Option B: 修 alembic head conflict（如果是 schema 問題）
   - Option C: 加 setup script for push event（補齊 PR-only 缺項）
4. **驗證**：
   - Push to feature branch (53.2) → ci.yml on push event 綠
   - 53.2 PR merge 後 main HEAD push event ci.yml 綠
   - `gh run list --workflow ci.yml --branch main --limit 3` 全綠

**Effort**: 0.5 day（Day 0 診斷 + Day 4 上半 fix）

### US-9 — 53.1 closeout bookkeeping bundle

**設計**：

```bash
# Day 4 closeout 階段
git checkout feature/sprint-53-2-error-handling
git fetch origin docs/sprint-53-1-closeout-bookkeeping
git cherry-pick <commit-1-sha> <commit-2-sha>
# OR (preferred for 2 small commits):
git merge --no-ff origin/docs/sprint-53-1-closeout-bookkeeping
# Verify content
git log --oneline -5
git push origin feature/sprint-53-2-error-handling
```

**Verification**：
- `git diff main..feature/sprint-53-2-error-handling -- memory/MEMORY.md claudedocs/` 顯示預期 closeout content
- 53.2 PR body §Includes 段落明確列出 53.1 closeout bundle
- PR merge 後 `git push origin --delete docs/sprint-53-1-closeout-bookkeeping`

**Effort**: 15 min（Day 4 closeout）

---

## File Change List

### US-1 (ErrorClassifier)
- ➕ `backend/src/agent_harness/error_handling/classifier.py` (new)
- ✏️ `backend/src/agent_harness/_contracts/errors.py`（補 `AuthenticationError` / `MissingDataError` / `ErrorContext`）
- ➕ `backend/tests/unit/agent_harness/error_handling/test_classifier.py` (new)

### US-2 (RetryPolicy + ErrorRetried)
- ➕ `backend/src/agent_harness/error_handling/retry.py` (new)
- ➕ `backend/config/retry_policies.yaml` (new)
- ✏️ `backend/src/agent_harness/_contracts/events.py`（補 `ErrorRetried` event）
- ➕ `backend/tests/unit/agent_harness/error_handling/test_retry.py` (new)

### US-3 (CircuitBreaker)
- ➕ `backend/src/agent_harness/error_handling/circuit_breaker.py` (new)
- ✏️ `backend/src/adapters/_base/chat_client.py`（pre-call check hook）
- ✏️ `backend/src/adapters/azure_openai/adapter.py`（注入 circuit breaker dep）
- ➕ `backend/tests/unit/agent_harness/error_handling/test_circuit_breaker.py` (new)
- ➕ `backend/tests/integration/adapters/test_circuit_breaker_integration.py` (new)

### US-4 (ErrorBudget)
- ➕ `backend/src/agent_harness/error_handling/budget.py` (new)
- ➕ `backend/config/error_budgets.yaml` (new)
- ➕ `backend/src/agent_harness/error_handling/_redis_store.py` (new — BudgetStore Redis impl)
- ➕ `backend/tests/unit/agent_harness/error_handling/test_budget.py` (new)

### US-5 (ErrorTerminator)
- ➕ `backend/src/agent_harness/error_handling/terminator.py` (new)
- ✏️ `backend/src/agent_harness/_contracts/events.py`（補 `LoopTerminated` event）
- ➕ `backend/tests/unit/agent_harness/error_handling/test_terminator.py` (new)

### US-6 (AgentLoop integration)
- ✏️ `backend/src/agent_harness/orchestrator_loop/loop.py`
- 可能 ✏️ `backend/src/agent_harness/orchestrator_loop/_abc.py`（新 deps）
- 可能 ✏️ `backend/src/api/v1/chat/router.py`（DI: classifier + retry + circuit + budget + terminator）
- ✏️ `backend/tests/integration/agent_harness/orchestrator_loop/test_loop_error_handling.py` (new)
- ✏️ `backend/src/agent_harness/error_handling/__init__.py`（re-export concrete classes）

### US-7 (#38 flaky test_router)
- ✏️ `backend/tests/unit/api/v1/chat/test_router.py`（移 xfail × 1）
- 可能 ✏️ `backend/tests/conftest.py`（fixture isolation fix）
- 可能 ✏️ `backend/src/api/v1/chat/router.py`（DI registry reset）

### US-8 (AD-CI-1 CI Pipeline)
- 可能 ✏️ `.github/workflows/ci.yml`
- 可能 ✏️ `backend/scripts/ci_setup.sh` or `backend/alembic.ini`

### US-9 (53.1 closeout bundle)
- 視 closeout branch 內容（推測：`memory/MEMORY.md` + `claudedocs/...`）

---

## Acceptance Criteria

### Sprint-level（必過）

- [ ] 9 user stories 全 ✅（US-1 ~ US-9）
- [ ] `cd backend && python -m pytest --tb=no -q` exit 0：
  - **理想**：≥ 615 PASS / 0 xfail / 4 skipped / 0 failed（596 baseline + ≥ 19 new Cat 8 tests）
  - **可接受**：≥ 610 PASS / ≤ 1 xfail (carryover with new issue) / 4 skipped / 0 failed
- [ ] `cd backend && mypy --strict src` 205+ files clean（Cat 8 新增 ~6 files；不退步）
- [ ] `python scripts/lint/check_llm_sdk_leak.py --root backend/src` LLM SDK leak = 0
- [ ] 6 個 V2 lint scripts 全綠（含 cross-category-import / promptbuilder-usage / 其他）
- [ ] 8 個 active CI workflow 在 53.2 PR 全綠（V2 Lint / Backend CI / CI Pipeline / E2E Tests / Frontend CI + 其他）
- [ ] **AD-CI-1 修復驗證**：CI Pipeline workflow 在 main HEAD push event 綠（53.2 merge 後）
- [ ] 7 GitHub issues #40-46 + #47 全 close；#38 close（US-7 reactivate）
- [ ] Cat 8 coverage ≥ 80%（per code-quality.md target）

### 跨切面紀律

- [ ] **Normal merge**：53.2 PR 走正常 review flow（user approve → 我 merge）；**不**用 admin override；**不**用 temp-relax bootstrap（與 53.1 不同）
- [ ] **No silent xfail**：未解的 test 必須有對應新 GitHub issue + retrospective Audit Debt 記錄
- [ ] **No new Potemkin**：ErrorClassifier / RetryPolicy / CircuitBreaker / ErrorBudget / ErrorTerminator 必須在主流量（AgentLoop）真實使用 — US-6 是反 AP-4 守門
- [ ] **Cat 8 vs Cat 9 邊界守住**：grep `Tripwire` 在 `error_handling/` = 0 hits（per 17.md §6）

### 主流量整合驗收（per W3 process fix #6）

- [ ] **ErrorClassifier 真在 AgentLoop 用嗎？** Grep `error_classifier.classify` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **RetryPolicy 真在 AgentLoop 用嗎？** Grep `retry_policy.get_policy` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **CircuitBreaker 真在 Adapter 用嗎？** Grep `circuit_breaker.is_open\|record_success\|record_failure` 在 `adapters/` ≥ 3 處
- [ ] **ErrorBudget 真在主流量用嗎？** Grep `error_budget.record\|is_exceeded` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **ErrorTerminator 真在 AgentLoop 用嗎？** Grep `error_terminator.should_terminate` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **LLM-recoverable 回注真用嗎？** Integration test：tool 拋 ToolExecutionError → loop 繼續 + messages append `is_error=True` ToolResult
- [ ] **Cat 8 coverage 真達標嗎？** `pytest --cov=src/agent_harness/error_handling` ≥ 80%

---

## Deliverables（見 checklist 詳細）

| Day | 工作 |
|-----|------|
| 0 | Setup: branch + plan + checklist + GitHub issues #40-47 + Cat 8 baseline reproduce + #38 reproduce + AD-CI-1 診斷 + 53.1 closeout bookkeeping branch verify |
| 1 | **US-1 ErrorClassifier + US-2 RetryPolicy matrix + ErrorRetried event** + commit + push 驗 backend-ci 綠 |
| 2 | **US-3 CircuitBreaker per-provider + US-4 ErrorBudget per-tenant** + adapter 整合 + integration tests + push 驗 ci.yml 綠 |
| 3 | **US-5 ErrorTerminator + US-6 AgentLoop integration（上半）** + push 驗 |
| 4 | **US-6 AgentLoop integration（下半）+ US-7 #38 fix + US-8 AD-CI-1 fix + US-9 53.1 closeout bundle + retrospective + Sprint Closeout + PR open（normal merge）** |

Day 0 預計 2026-05-03 啟動；Day 1-4 預計 5 days（含 Day 4 PR review 等待）。

---

## Dependencies & Risks

### 依賴

- main HEAD `aaa3dd75` (Sprint 53.1 PR #39 merged) ✅
- Branch protection `enforce_admins=true` 已生效（Sprint 52.6 closeout）
- `gh` CLI authenticated ✅
- Redis 本地可跑（US-4 ErrorBudget store）— assumed via dev environment；fallback DB store
- 8 個 active CI workflow 在 PR-level 全綠 baseline（53.1 closeout 確認）；push-to-main level CI Pipeline 紅 → US-8 修
- Cat 1 (Loop) / Cat 2 (Tools) / Cat 6 (Output Parser) / Cat 7 (State) Phase 50-53.1 落地（為 US-6 整合提供既有 dependencies）
- Cat 7 Reducer / Checkpointer 已 production-ready（53.1 落地）— US-6 利用 checkpoint-on-terminate

### 風險

| Risk | Mitigation |
|------|------------|
| **Cat 8 5 個新 module + AgentLoop 整合 1 個 sprint 太緊** | Day-by-day hard checkpoint；US-1/2/3/4 各 0.75-1 day 嚴守；US-6 整合 1.25 day 留 buffer；若 Day 3 末仍未完成 US-6 → 砍 US-7/8 至 53.x |
| **#38 flaky 根因不易定位** | Day 0 reproduce + Day 4 fix；如 Day 4 上半仍未解 → 留 xfail + 開新 issue + Audit Debt + 不強塞 |
| **AD-CI-1 修復需動 CI workflow** | Day 0 診斷 + Day 4 上半 fix；如需動 ci.yml 結構性改動 → 拆 separate PR + 53.x track；本 sprint 不強塞 |
| **CircuitBreaker 引入 race condition** | asyncio.Lock 嚴守；test 含 concurrent record（asyncio.gather × 10）；參考 53.1 Reducer Lock pattern |
| **ErrorBudget Redis 依賴在 CI 環境不可用** | Fallback DB store；CI 用 fakeredis；test 兩種 store 都跑 |
| **AgentLoop integration 退步 51.x + 53.1 baseline** | Day 3-4 push 後立即跑既有 integration test suite；如有退步 → rollback + opt-in pattern（同 53.1 reducer pattern）|
| **Cat 8 vs Cat 9 邊界混淆**（Tripwire vs ErrorTerminator）| 設計階段 grep `Tripwire` 在 `error_handling/` 必須 = 0；CI lint 加守門 |
| **53.1 closeout bookkeeping bundle 衝突** | Day 4 cherry-pick / merge 前先 rebase main；如衝突 → 手動解決後 push |
| **53.2 自我 self-approve block（同 53.1 chicken-egg）** | 走正常 review flow（user approve → 我 merge）；本 sprint 明確**禁止** temp-relax；如真需 → 開新 sprint |
| **Sprint 過寬** | 砍 scope hierarchy：US-9 closeout bundle → US-8 AD-CI-1 → US-7 #38 → core US-1~6 不可砍 |

---

## Audit Carryover Section（per W3 process fix #1）

本 sprint 處理：
- **AD-Cat7-2 #38 flaky test_router fix**（53.1 retrospective）
- **AD-CI-1 CI Pipeline push-to-main fix**（53.1 retrospective）
- **53.1 closeout bookkeeping bundle**（branch `docs/sprint-53-1-closeout-bookkeeping`）

**不在 53.2 scope（明確排除）**：
- AI-22 dummy red PR test enforce_admins → 53.x+ 單獨 chaos test PR
- AD-Cat7-1 Full sole-mutator refactor → Phase 54.x with verifier integration
- AD-Cat7-3 state_snapshots retention policy → Phase 54.x
- AD-Cat7-4 AgentLoopImpl.resume() full impl → Phase 54.x
- #29 V2 frontend E2E setup → 53.x+ frontend track
- #30 sandbox image CI build → 53.x+ infra track
- #31 V2 backend Dockerfile + Deploy workflow → 53.x+ infra track
- AI-19 CI workflow consolidation → 53.x+
- §HITL 中央化完整實作 → Phase 53.4
- 範疇 9 Tripwire → Phase 53.3

### 後續 audit 預期

W4 audit（Sprint 53.2 完成後）：驗證
- ErrorClassifier 在主流量真用（而非 lazy-init never called）
- RetryPolicy matrix 真用（grep `retry_policy.get_policy` 在主流量 ≥ 1 處）
- CircuitBreaker 在 adapter 真接入（grep 在 `adapters/` ≥ 3 處）
- LLM-recoverable 回注真實作（integration test 證據）
- ErrorTerminator vs Tripwire 邊界守住（`error_handling/` 無 Tripwire reference）
- Cat 8 coverage ≥ 80% 真達

---

## §10 Process 修補落地檢核

per 52.5 §10 + 52.6 §10 + 53.1 §10：

- [x] Plan template 加 Audit Carryover 段落（本 plan §Audit Carryover Section）
- [ ] Retrospective 加 Audit Debt 段落（Day 4 retrospective.md）
- [ ] GitHub issue per US（#40-46 Day 0 建立；#47 bundle ticket；#38 既有）
- [ ] **per W3 process fix #6**：Sprint Retrospective「主流量整合驗收」必答題（Day 4）
- [ ] **per 53.1 §AD-Cat7-2**：US-7 (#38 fix) Day 0 reproduce + Day 4 fix
- [ ] **per 53.1 §AD-CI-1**：US-8 (CI Pipeline fix) Day 0 診斷 + Day 4 fix
- [ ] **53.1 closeout bookkeeping bundle**：US-9 Day 4 closeout
- [ ] **52.5 §AD-2 + 52.6 + 53.1 closeout**：Sprint 53.2 PR 走 normal merge（**zero temp-relax**；branch protection enforce_admins=true 自動強制）

---

## Retrospective 必答（per W3-2 + 52.6 + 53.1 教訓）

Sprint 結束時，retrospective 必須回答：

1. **每個 US 真清了嗎？** 列每 US 對應 commit + verification 結果（含 8 active CI workflow 在 main HEAD 的 run id + status）
2. **跨切面紀律守住了嗎？** admin-merge count（本 sprint 應 = 0；temp-relax count = 0；branch protection enforce）/ Cat 8 coverage 數字 / Cat 8 vs Cat 9 邊界 grep evidence（Tripwire 在 `error_handling/` = 0）
3. **有任何砍 scope 嗎？** 若有（例 #38 / AD-CI-1 / closeout bundle 部分），明確列出 + 理由 + 後續排程
4. **GitHub issues #40-47 + #38 全處理了嗎？** 列每個 issue url + close commit hash
5. **Audit Debt 累積了嗎？** 本 sprint 期間發現的新 audit-worthy 問題列出（例如 ErrorBudget tenant override config / CircuitBreaker per-tool 而非 per-provider 重新討論 / Redis dependency 在 K8s 環境的 HA 等）
6. **主流量整合驗收**：ErrorClassifier 在 Loop 真用？RetryPolicy 真用？CircuitBreaker 在 Adapter 真接入？ErrorBudget 真用？ErrorTerminator 真用？LLM-recoverable 回注真實作？Cat 8 vs Cat 9 邊界 grep ＝ 0？Cat 8 coverage 真 ≥ 80%？

---

## Sprint Closeout

- [ ] Day 4 retrospective.md 寫好（含必答 6 條）
- [ ] All 7 GitHub issues #40-46 + #47 closed；#38 close（US-7 reactivate）
- [ ] PR 開到 main，title: `feat(error-handling, sprint-53-2): Cat 8 Error Handling — ErrorClassifier + RetryPolicy + CircuitBreaker + ErrorBudget + ErrorTerminator + AgentLoop integration + #38 fix + AD-CI-1 fix + 53.1 closeout bundle`
- [ ] PR body 含每 US verification 證據 + workflow run id + Cat 8 coverage 數字 + Cat 8 vs Cat 9 邊界 grep 證據 + 53.1 closeout bundle 確認
- [ ] **PR 用正常 merge**（NOT admin override，NOT temp-relax bootstrap）— branch protection enforce_admins=true 自動強制
- [ ] V2 milestone 更新：14/22 sprints (64%)
- [ ] Memory update：phase 53.2 完成 + Cat 8 Level 4 達成 + #38 closure status + AD-CI-1 closure status + 53.1 closeout bundle 完成
- [ ] Delete remote branch `docs/sprint-53-1-closeout-bookkeeping`（US-9 完成後）

---

**權威排序**：`agent-harness-planning/` 19 docs > 本 plan > V1 文件 / 既有代碼。本 plan 對齊 `01-eleven-categories-spec.md` §範疇 8 + `17-cross-category-interfaces.md` §1.1 / §6 (Tripwire 邊界) + `06-phase-roadmap.md` §Sprint 53.2 + Sprint 49.1 stub + Sprint 53.1 retrospective AD-Cat7-2 / AD-CI-1。
