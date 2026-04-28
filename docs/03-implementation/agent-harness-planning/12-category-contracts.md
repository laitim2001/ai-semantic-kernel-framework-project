# 11 範疇間整合契約（Contracts）

**建立日期**：2026-04-23
**版本**：V2.0
**重要性**：⭐ 範疇間如何協作的權威定義

---

## 與 17.md 跨範疇接口附錄的關係

> **2026-04-28 review 更新**：所有跨範疇的 dataclass / ABC / tool / event 介面已收攏到 [`17-cross-category-interfaces.md`](./17-cross-category-interfaces.md)（single-source registry）。**本文件不重複定義介面**，只規範**互動順序、資料流、失敗模式**。

當你在本文件看到 `ToolSpec` / `ChatClient` / `LoopState` / `MemoryHint` / `TraceContext` / `ApprovalRequest` 等型別時，**完整定義在 17.md §1.1 + §2.1**。本文件只描述「誰呼叫誰」「傳什麼」「失敗怎辦」。

---

## 為什麼需要本文件

01 文件定義了**每個範疇是什麼**，17 文件定義了**介面在哪**，但**範疇間如何協作**仍需單獨規範。

例：
- Loop（範疇 1）如何呼叫 PromptBuilder（範疇 5）？傳什麼？順序？失敗如何傳播？
- Tool execution（範疇 2）如何觸發 Guardrail（範疇 9）？同步還是異步？
- State Mgmt（範疇 7）的 **Reducer** 何時被觸發？由誰觸發？
- Range 12（Observability）如何 cross-cutting 滲透所有範疇？

本文件**權威定義**所有跨範疇互動 + 資料流 + 失敗模式。

---

## 範疇間呼叫關係總覽（含範疇 12）

```
                        ┌──────────────────┐
                        │ Range 1: Loop    │ ← 中樞，呼叫所有
                        └──┬───┬───┬───┬───┘
            ┌──────────────┘   │   │   │
            ↓                  ↓   ↓   ↓
   ┌─────────────────┐  ┌────────────────┐
   │ R5: PromptBuilder│  │ R4: Context Mgmt│
   └──────┬──────────┘  └────────┬───────┘
          │                       │
          └─→ R3: Memory ←────────┘
                  ↓
          R2: Tool Layer
              ↓
          R6: Output Parser ←─ R1 用
              ↓
          R11: Subagent
              ↓
          R10: Verification ←─ R1 結束時
              ↓
          R7: State Mgmt（持續被用，含 Reducer）
              
   橫切：R8 (Error) / R9 (Guardrails) ← 全範疇用
   ⭐ 橫切：R12 (Observability) ← 滲透所有範疇 ABC（trace_context propagation）
   ⭐ 中央化：§HITL（範疇 2/9 為 caller、範疇 7 為 storage、範疇 8 不直接 own）
```

---

## Cross-Cutting Rule：trace_context 強制簽名（**2026-04-28 第二輪 review 新增**）

> **Review 發現**：Contract 13 規範「所有範疇 ABC 接受 trace_context」，但 Contract 1-10 簽名都沒有此參數，**規範與簽名脫鉤，CI 無法 enforce**。本節統一補強。

### 強制規則

**所有跨範疇 ABC 必須在 keyword-only 參數中接受 `trace_context: TraceContext`。** 例外：純 dataclass / Reducer.merge() 等無 IO 操作的純函式可省略。

```python
# ✅ 正確：所有對外 ABC method 接 trace_context (keyword-only)
async def some_method(
    self,
    *,                                     # ← keyword-only 強制
    arg1: ...,
    trace_context: TraceContext,           # ← 必填，由父 caller 傳遞
) -> ...

# ❌ 錯誤：trace_context 缺失或 positional
async def some_method(self, arg1, trace_context=None): ...
```

### Lint 規則（Phase 49.4 強制）

`backend-ci.yml` 加 `trace_context_enforcement_check`：

```python
# scripts/lint/check_trace_context.py
# 對 agent_harness/**/_abc.py 中所有 @abstractmethod async method
# 必須在 signature 中含 trace_context: TraceContext 參數
# 違反者 CI fail。
```

### 受影響 Contract

Contract 1, 2, 3, 4, 5, 7, 8, 9, 10 全部加 `trace_context: TraceContext` 參數（在下方各 Contract 的 API 簽名展示中已對應修訂）。Contract 12（Reducer）/ 13（Observability）/ 14（HITL）已含。

---

## Contract 1：Loop ↔ PromptBuilder（範疇 1 → 5）

### 觸發時機
- 每輪 loop 開始前

### API（**2026-04-28 修訂**：去 staticmethod + 加 trace_context）

> **Review 發現**：原 `@staticmethod` 無法 DI 注入 cache / template registry / observability，未來擴充必破 API。改為 instance method。

```python
# agent_harness/prompt_builder/builder.py
class PromptBuilder(ABC):
    """Instance-based。由 DI container 注入 cache_manager / template_registry / token_counter。"""

    @abstractmethod
    async def build(
        self,
        *,
        system_role: str,
        tools: list[ToolSpec],
        memory_layers: MemoryLayers,
        conversation: list[Message],
        user_message: str | None = None,
        position_strategy: PositionStrategy = PositionStrategy.LOST_IN_MIDDLE_AWARE,
        cache_breakpoints: list[CacheBreakpoint] | None = None,    # 範疇 4 caching
        trace_context: TraceContext,                                # ⭐ 強制
    ) -> AssembledPrompt: ...

@dataclass
class AssembledPrompt:
    messages: list[Message]      # 給 ChatClient 用
    estimated_tokens: int        # 給 Context Mgmt 用
    components: dict[str, int]   # 哪部分占多少 token（debug 用）
    cache_breakpoints: list[CacheBreakpoint]  # 給 ChatClient 透傳到 provider
```

### 資料流
```
Loop:
  prompt = await PromptBuilder.build(
      system_role=loop_state.system_role,
      tools=registered_tools,
      memory_layers=memory_snapshot,
      conversation=loop_state.messages,
      user_message=None,  # 已在 conversation 中
  )
  response = await chat_client.chat_with_tools(prompt.messages, tools)
```

### 失敗模式
- PromptBuilder 內部失敗 → raise PromptBuildError
- Token 超預算 → 觸發 Context Mgmt compaction（見 Contract 4）

---

## Contract 2：Loop ↔ ChatClient（範疇 1 → adapter）

### 觸發時機
- PromptBuilder 完成後

### API
```python
# adapters/_base/chat_client.py（完整 ABC 見 10.md 原則 2）
class ChatClient(ABC):
    @abstractmethod
    async def chat(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: int | None = None,
        temperature: float = 1.0,
        thinking: bool = False,        # extended thinking（Anthropic）/ reasoning（GPT-5）
        cache_breakpoints: list[CacheBreakpoint] | None = None,
        trace_context: TraceContext,                                # ⭐ 強制
        extra: dict | None = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolSpec],
        trace_context: TraceContext,                                # ⭐ 強制
        **kwargs,
    ) -> AsyncIterator[ChatChunk]:
        """Streaming-first。Phase 50.1 起主流量必用此 method（見 Contract 15）。"""
        ...

@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall] | None
    thinking: str | None              # 中性 thinking 欄位
    stop_reason: StopReason
    usage: Usage                      # tokens, cost
    metadata: dict
```

### 失敗模式
- Provider 錯誤 → 由 Adapter 翻譯為 ChatClientError
- 超時 → ChatClientTimeoutError
- Rate limit → ChatClientRateLimitError（觸發 retry）

---

## Contract 3：Loop ↔ Tool Executor（範疇 1 → 2）

### 觸發時機
- ChatResponse 含 tool_calls 時

### API
```python
# agent_harness/tools/executor.py
class ToolExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        *,
        tool_call: ToolCall,
        context: ExecutionContext,
        trace_context: TraceContext,                  # ⭐ 強制
    ) -> ToolResult: ...

    @abstractmethod
    async def execute_parallel(
        self,
        *,
        tool_calls: list[ToolCall],
        context: ExecutionContext,
        trace_context: TraceContext,                  # ⭐ 強制
        partial_failure_policy: Literal["all_or_nothing", "best_effort"] = "best_effort",
    ) -> list[ToolResult]:
        """並行政策依 ToolSpec.concurrency_policy 與 Loop-level parallel_tool_policy 取嚴格交集。
        判斷依據：**顯式來自 ToolSpec.annotations.read_only + concurrency_policy（不靠 is_mutating 推測）**。
        partial_failure_policy: best_effort 允許部分成功並回傳混合結果（含 error）；all_or_nothing 任一失敗整批 rollback。"""

@dataclass
class ExecutionContext:
    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    role: str
    loop_state: LoopState  # 唯讀引用
```

### 內部觸發
ToolExecutor 內部會呼叫：
1. Guardrail check（Contract 5）
2. Permission check
3. Sandbox setup（如需要）
4. Tool handler 執行
5. Audit log（Contract 6）

### 失敗模式
- Permission denied → ToolPermissionError
- HITL required → 拋 HITLRequired exception，loop 暫停
- Tool 執行錯誤 → ToolExecutionError（回注 LLM 而非 raise，見範疇 8）

---

## Contract 4：Loop ↔ Context Compactor（範疇 1 → 4）

### 觸發時機
- 每輪 loop 開頭
- Token usage > 75% window 時

### API
```python
# agent_harness/context_mgmt/compactor.py
class ContextCompactor(ABC):
    @abstractmethod
    async def should_compact(
        self,
        *,
        state: LoopState,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> bool: ...

    @abstractmethod
    async def compact(
        self,
        *,
        state: LoopState,
        strategy: CompactionStrategy = CompactionStrategy.PRESERVE_DECISIONS,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> LoopState:
        """
        策略：
        - PRESERVE_DECISIONS: 保留架構決策、未解 bug，丟冗餘
        - PRESERVE_RECENT_N: 保留最近 N 輪
        - AGGRESSIVE: 只保留 system prompt + 摘要
        """
```

### 資料流
```
Loop:
  if await compactor.should_compact(state):
      state = await compactor.compact(state)
      state.messages = state.messages  # 已被替換
      audit.log("compaction", tokens_before, tokens_after)
```

---

## Contract 5：Tool Executor ↔ Guardrail Engine（範疇 2 → 9）

### 觸發時機
- 每個 tool 執行**前**（同步）

### API
```python
# agent_harness/guardrails/engine.py
class GuardrailEngine(ABC):
    @abstractmethod
    async def check_input(
        self,
        *,
        user_input: str,
        context: ExecutionContext,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> GuardrailResult: ...

    @abstractmethod
    async def check_tool_call(
        self,
        *,
        tool_call: ToolCall,
        context: ExecutionContext,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> ToolGuardrailResult: ...

    @abstractmethod
    async def check_output(
        self,
        *,
        final_output: str,
        context: ExecutionContext,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> GuardrailResult: ...

@dataclass
class ToolGuardrailResult:
    passed: bool
    requires_hitl: bool
    risk_level: RiskLevel
    triggered_rules: list[str]
    tripwire_fired: bool
    reasoning: str
```

### 資料流
```
Tool Executor:
  guardrail_result = await guardrail.check_tool_call(tc, ctx)
  
  if guardrail_result.tripwire_fired:
      raise TripwireException(reason=guardrail_result.reasoning)
  
  if guardrail_result.requires_hitl:
      raise HITLRequired(approval_payload=...)
  
  if not guardrail_result.passed:
      return ToolResult.error(guardrail_result.reasoning)
  
  # 通過 → 執行
  result = await tool.handler(tc.arguments)
```

### 失敗模式
- Tripwire 觸發 → loop 立即終止
- HITL required → loop 暫停，state 持久化

---

## Contract 6：所有範疇 → Audit Logger（範疇 9 cross-cutting）

### 觸發時機
- 任何重要操作後

### API
```python
# governance/audit/logger.py
class AuditLogger(ABC):
    @abstractmethod
    async def log(
        self,
        *,
        operation: str,
        resource_type: str,
        resource_id: str | None,
        operation_data: dict,
        result: AuditResult,
        context: ExecutionContext | None = None,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> AuditLogEntry: ...
```

### 觸發範例
```python
# 範疇 1 Loop
await audit.log("loop_started", "session", session_id, {...}, AuditResult.SUCCESS)
await audit.log("loop_ended", "session", session_id, {...}, AuditResult.SUCCESS)

# 範疇 2 Tool
await audit.log("tool_executed", "tool", tool_name, {args, result}, AuditResult.SUCCESS)

# 範疇 9 HITL
await audit.log("approval_granted", "approval", approval_id, {...}, AuditResult.SUCCESS)

# 範疇 10 Verification
await audit.log("verification_passed", "session", session_id, {...}, AuditResult.SUCCESS)
```

### 強制原則
- ⭐ 所有 mutating 操作必須有 audit log
- ⭐ Audit 失敗不應阻塞主流程（fire-and-forget + outbox 補償）

---

## Contract 7：Loop ↔ State Checkpointer（範疇 1 → 7）

### 觸發時機
- 每輪 loop 完成後（自動 checkpoint）
- HITL pause 時（手動 checkpoint）
- 用戶請求 time-travel 時

### API
```python
# agent_harness/state_mgmt/checkpointer.py
class StateCheckpointer(ABC):
    @abstractmethod
    async def snapshot(
        self,
        *,
        state: LoopState,
        reason: Literal["turn_end","hitl_pause","verification_fail","manual","schedule"] = "turn_end",
        trace_context: TraceContext,         # ⭐ 強制
    ) -> CheckpointId: ...

    @abstractmethod
    async def restore(
        self,
        *,
        checkpoint_id: UUID,
        trace_context: TraceContext,
    ) -> LoopState: ...

    @abstractmethod
    async def list_checkpoints(
        self,
        *,
        session_id: UUID,
        trace_context: TraceContext,
    ) -> list[CheckpointSummary]: ...

    @abstractmethod
    async def time_travel(
        self,
        *,
        session_id: UUID,
        version: StateVersion,
        trace_context: TraceContext,
    ) -> LoopState: ...
```

### Checkpoint 頻率政策（**2026-04-28 修訂**）

> **Review 發現**：原規範「每輪 loop 完成自動 checkpoint」會放大 DB 寫入。修訂為**事件驅動**：

| 觸發 | 寫入位置 | 頻率 |
|------|--------|------|
| Turn 結束 | **In-memory shadow state**（不落 DB） | 每 turn |
| HITL pause | DB checkpoint | per pause |
| Verification fail | DB checkpoint | per fail |
| 每 N turn（預設 5） | DB checkpoint | 週期性 |
| Manual / time-travel request | DB checkpoint | on-demand |
| Schedule（含 backup window） | DB checkpoint | 5 min |

`reason` 參數記錄寫入動機，方便 audit。

### 失敗模式

| 失敗 | 處置 | 重試政策 |
|------|------|---------|
| DB 寫入超時 | 寫 outbox（持久 queue），主 loop 不阻塞 | exponential backoff，max 5 |
| Optimistic lock 衝突（StateVersion content_hash mismatch） | reload + reapply reducer，重 hash | max 3 retry |
| Outbox 補償失敗 | emit AlertEvent + 進入 dead-letter | 由 SRE 介入 |

---

## Contract 8：Tool Layer ↔ Memory（範疇 2 → 3）

### 觸發時機
- Memory tools 被呼叫時：
  - `memory_search`
  - `memory_write`
  - `memory_list`

### API
```python
# agent_harness/memory/retrieval.py
class MemoryRetrieval(ABC):
    @abstractmethod
    async def search(
        self,
        *,
        query: str,
        context: ExecutionContext,
        layers: list[MemoryLayer] = None,
        time_scales: list[TimeScale] = None,
        top_k: int = 5,
        trace_context: TraceContext,
    ) -> list[MemoryEntry]: ...

    @abstractmethod
    async def write(
        self,
        *,
        content: str,
        layer: MemoryLayer,
        time_scale: TimeScale,
        category: str,
        context: ExecutionContext,
        trace_context: TraceContext,
    ) -> MemoryEntry: ...

    @abstractmethod
    async def get_layer_summary(
        self,
        *,
        layer: MemoryLayer,
        context: ExecutionContext,
        max_tokens: int = 500,
        trace_context: TraceContext,
    ) -> str:
        """給 PromptBuilder 用，每層的摘要"""
```

### Subagent / Memory 隔離契約（**2026-04-28 新增**）

> **Review 發現**：Contract 10 只規範 token budget 隔離，未規範 subagent 是否能寫 user-layer memory。是 V1 安全洞。

| Subagent Mode | 可讀層 | 可寫層 | 強制 |
|--------------|------|------|------|
| FORK | L1+L2+L3+L4+L5（snapshot） | **僅 L5_session**（FORK 結束即丟） | sandbox enforced |
| TEAMMATE | L1+L2+L3 | **無寫權**（除非父 agent 顯式授權） | mailbox 限定 channel |
| HANDOFF | 父 agent 所有層 | 父 agent 所有層 | 完全交棒 |
| AS_TOOL | L1+L2 | **無寫權** | 純函式呼叫 |

**規則**：subagent 寫 user-layer memory 必須由父 agent 顯式 `grant_memory_write(layer="L4_user")`，否則 raise `MemoryPermissionError`。

### 強制
- ⭐ Tenant 隔離：必須透過 RLS（Contract 中無例外）
- ⭐ Audit log：每個 memory_write 必須記錄
- ⭐ Subagent 預設無 user-layer 寫權（最小權限）

---

## Contract 9：Loop ↔ Verifier（範疇 1 → 10）

### 觸發時機
- Loop 結束前（end_turn）
- 重要中間產出（生成報告 / 文件等）

### API
```python
# agent_harness/verification/verifier_base.py
class Verifier(ABC):
    @abstractmethod
    async def verify(
        self,
        *,
        target: VerificationTarget,
        context: ExecutionContext,
        trace_context: TraceContext,         # ⭐ 強制
    ) -> VerificationResult: ...

@dataclass
class VerificationResult:
    passed: bool
    confidence: float
    reasoning: str
    suggested_corrections: list[str] | None

# 配置（每範疇可在 ExecutionContext 覆寫）
DEFAULT_MAX_CORRECTIONS = 2
DEFAULT_VERIFIER_FAILURE_MODE = "fail_closed"  # verifier 自身錯誤視為驗證失敗
```

### Self-correction Flow（**2026-04-28 修訂**：補無限循環防護 + fail-closed）

```python
# Loop 內
async def run_with_verification(*, max_corrections: int = DEFAULT_MAX_CORRECTIONS, ...):
    """
    Self-correction loop 上限：max_corrections（預設 2，硬上限 5）
    若 verifier 自身錯誤 → fail_closed（視為驗證失敗）+ emit warning
    """
    for attempt in range(max_corrections + 1):
        result = await self.run_internal(...)
        try:
            verification = await self.verifier.verify(target=result, context=ctx, trace_context=trace_ctx)
        except Exception as e:
            # fail_closed：verifier 自身錯誤視為失敗
            tracer.record_metric(MetricEvent("verifier.error", "counter", 1.0, {...}))
            verification = VerificationResult(passed=False, confidence=0.0,
                                              reasoning=f"Verifier error: {e}",
                                              suggested_corrections=None)

        if verification.passed:
            return result

        # 失敗 → 回注訊息再來一輪
        state.messages.append(Message(
            role="user",
            content=f"Verification failed: {verification.reasoning}\n"
                    f"Suggestions: {verification.suggested_corrections}"
        ))
        state.correction_count += 1

    # 達到 max_corrections 仍失敗
    tracer.record_metric(MetricEvent("verification.exhausted", "counter", 1.0, {...}))
    return result.with_warning("verification_failed_after_retries")
```

---

## Contract 10：Loop ↔ Subagent Dispatcher（範疇 1 → 11）

### 觸發時機
- 工具呼叫 `task_spawn` / `handoff_to`

### API
```python
# agent_harness/subagent/dispatcher.py
class SubagentDispatcher(ABC):
    @abstractmethod
    async def fork(
        self,
        *,
        parent_state: LoopState,
        task: str,
        role: str,
        budget: SubagentBudget,                  # 見 17.md §1.1（含 summary_token_cap caller-defined）
        trace_context: TraceContext,             # ⭐ 強制（child span 用）
    ) -> SubagentResult: ...

    @abstractmethod
    async def spawn_teammate(
        self,
        *,
        role: str,
        mailbox: Mailbox,
        budget: SubagentBudget,
        trace_context: TraceContext,
    ) -> SubagentHandle: ...

    @abstractmethod
    async def handoff_to(
        self,
        *,
        target_agent: AgentSpec,
        full_context: LoopState,
        trace_context: TraceContext,
    ) -> HandoffResult: ...

@dataclass
class SubagentResult:
    summary: str  # 由 caller-defined SubagentBudget.summary_token_cap 控制
    artifacts: list[str]
    cost_usd: float
    succeeded: bool
```

### 強制
- ⭐ Subagent 摘要必須 ≤ 2K token（範疇 4 強制）
- ⭐ Subagent 失敗不會 crash 父 agent
- ⭐ 每個 subagent 有獨立 token budget

---

## Contract 11：Error Handler 跨範疇（範疇 8 cross-cutting）

### 4 類錯誤路由

```python
# agent_harness/error_handling/router.py
class ErrorRouter:
    async def handle(self, exc: Exception, ctx: ExecutionContext) -> ErrorAction: ...

class ErrorAction:
    RETRY_TRANSIENT = "retry_transient"      # 自動 retry + backoff
    RETURN_TO_LLM = "return_to_llm"          # 回注 ToolResult.error
    INTERRUPT_FOR_HITL = "interrupt_hitl"    # 觸發 HITL
    BUBBLE_UP = "bubble_up"                   # 終止 + alert
```

### 觸發時機
- 任何範疇拋例外時
- 統一路由到對應處理

---

## Contract 12：Reducer Pattern（範疇 7 內部 + 跨範疇 merge）

> **2026-04-28 review 新增**：原 spec 缺 Reducer。HITL pause/resume / subagent return / context compaction 都需要把更新 merge 回 LoopState，沒有 Reducer 等於沒有可預期的 state mutation 模型。

### 觸發時機

| 觸發者 | Reducer 類型 | 對象 |
|------|------------|------|
| 範疇 1 Loop 每 turn 結束 | `AppendReducer` | `messages` / `tool_results` 追加 |
| §HITL 中央化 ApprovalDecision 回流 | `HITLDecisionReducer` | DurableState：把 decision 轉 user message + 清 pending |
| 範疇 11 SubagentResult 回流 | `SubagentResultReducer` | DurableState：把 summary 注入 messages |
| 範疇 4 Compactor 完成 | `LastWriteWinsReducer` | TransientState：替換 messages |
| 範疇 12 metric 累計 | `CounterReducer` | tokens_used / cost 等 metric 計數 |

### API

```python
# 範疇 7 owner
from agent_harness._contracts.state import LoopState, DurableState, TransientState
from agent_harness.state_mgmt import Reducer  # 由 17.md §2.1 single-source

class StateUpdater:
    """Loop 在 turn 結束 / HITL resume / subagent return 時呼叫。"""

    async def apply(
        self,
        *,
        state: LoopState,
        update: Any,
        reducer: Reducer,
        trace_context: TraceContext,
    ) -> LoopState:
        """應用 reducer，emit StateCheckpointed event；範疇 12 自動 record metric。"""
```

### 跨範疇互動

```
HITL approval received
  ↓
HITLManager.decide(ApprovalDecision)             [§HITL]
  ↓
StateUpdater.apply(state, decision, HITLDecisionReducer)  [範疇 7]
  ↓
DurableState.messages 追加 user message
DurableState.pending_approval_ids 移除已決策 UUID
  ↓
Checkpointer.snapshot()                          [範疇 7]
  ↓
Loop resume from latest checkpoint               [範疇 1]
```

### 失敗模式

| 失敗 | 處置 |
|------|------|
| Reducer 拋例外 | 不修改 state，emit `ReducerFailed` event，視為 LLM_RECOVERABLE error |
| Reducer 改了 immutable 欄位 | 模式比對檢查（dataclass(frozen=True)），ValueError |
| Reducer 違反 schema | mypy strict 在 lint 階段擋下 |

---

## Contract 13：Observability Cross-Cutting（範疇 12 滲透所有範疇）

> **2026-04-28 review 新增**：範疇 12 Observability 是 cross-cutting concern，**不在每個範疇 spec 重複描述**，由本 contract 統一規範滲透方式。

### 滲透規則

```
所有範疇 ABC 接受 trace_context: TraceContext 參數
  ↓
每個 ABC 入口：tracer.start_span(category=SpanCategory.X)
  ↓
ABC 完成：record_metric(MetricEvent)
  ↓
所有 LoopEvent 自動帶 trace_id / span_id
  ↓
SSE / OTel collector 端 reconstruction 完整 trace tree
```

### Span 切點對應表

| 範疇 | Span Category | record_metric 必 emit |
|------|--------------|--------------------|
| 1 (Loop) | LOOP / TURN | duration_ms / turns / tokens.{input,output,cached} |
| 2 (Tools) | TOOL_EXEC | tool.duration_ms / tool.errors |
| 3 (Memory) | MEMORY_OP | memory.read_count / memory.write_count |
| 4 (Context) | COMPACTION | compaction.token_reduction / compaction.duration_ms |
| 5 (Prompt) | PROMPT_BUILD | prompt.cache_hit_rate |
| 6 (Output) | — (in TURN) | parser.duration_ms |
| 7 (State) | CHECKPOINT | checkpoint.duration_ms |
| 8 (Error) | — (attribute on parent) | retry.count / circuit.open |
| 9 (Guardrails) | GUARDRAIL | guardrail.triggered |
| 10 (Verification) | VERIFICATION | verification.pass_rate |
| 11 (Subagent) | SUBAGENT | subagent.spawned / subagent.duration_ms |
| §HITL | HITL_WAIT | hitl.pending / hitl.wait_duration_s |

### 失敗模式

| 失敗 | 處置 |
|------|------|
| Tracer 自身錯誤 | **fail-open**：忽略 tracing 錯誤，不影響 loop（observability 不能拖累業務） |
| Metric overflow | bucketing + sample rate 降到 1% |
| trace_context propagation 斷裂 | lint rule 強制（Phase 49.4） |

---

## Contract 14：§HITL 中央化（範疇 2/9 caller，範疇 7 storage，範疇 1 pause/resume）

> **2026-04-28 review 新增**：HITL 散落在範疇 2 / 7 / 8 / 9 是 V1 教訓的根因之一。本 contract 規範統一互動。

### 觸發時機

| Caller | 觸發條件 |
|--------|---------|
| 範疇 2 (Tools) | `ToolSpec.hitl_policy.mode != "auto"` 或 `is_mutating=True` 且 risk≥MEDIUM |
| 範疇 9 (Guardrails) | guardrail check 結果 `requires_hitl=True` 或 `OutputGuardrailAction=ESCALATE` |
| 業務工具（08b） | `incident_close` / `rootcause_apply_fix` 等 always_ask 工具 |

### API（介面在 17.md §2.1）

```python
# 範疇 2 / 9 caller 路徑
async def execute_with_hitl(tool_call: ToolCall, ctx: LoopContext):
    if requires_hitl(tool_call):
        request_id = await hitl_manager.request_approval(ApprovalRequest(
            requester="tools",
            risk_level="HIGH",
            payload={"tool": tool_call.name, "args": tool_call.args},
            sla_deadline=now() + timedelta(hours=4),
            context_snapshot={...},
            trace_context=ctx.trace_context,
            ...
        ))
        # Loop 範疇 1 接收事件、暫停
        return ToolResult(status="hitl_pending", request_id=request_id)
    return await execute(tool_call)
```

### Resume 流程

```
1. Reviewer 在 governance frontend 提交 ApprovalDecision
2. HITLManager.decide() 寫入 DB
3. 背景 watcher 偵測到 decision → trigger Loop resume worker
4. Worker 從 last checkpoint load DurableState（範疇 7）
5. StateUpdater.apply(state, decision, HITLDecisionReducer)（Contract 12）
6. Loop 範疇 1 從 step 8 繼續執行
```

### 失敗模式

| 失敗 | 處置 |
|------|------|
| Approval timeout | `HITLPolicy.fallback_on_timeout`：reject / escalate / approve_with_audit |
| Reviewer 不存在 | escalate 到 admin pool |
| DB unreachable | fail-closed：直接 reject 工具呼叫，emit alert |
| 跨 session resume race | Optimistic lock on `pending_approval_ids`（StateVersion 雙因子） |

---

## Contract 15：Loop → Frontend Streaming/Event（範疇 1 → AG-UI/SSE）

> **2026-04-28 第二輪 review 新增**：原 12 文件未定義 LoopEvent emission 路徑（誰 emit、誰 subscribe、back-pressure 如何處理）。Phase 28+ AG-UI 主軸卻無對應 contract，**review 7.5/10 最大扣分項**。

### 觸發時機

- Loop 啟動 → emit `LoopStarted`
- LLM token streaming → emit `Thinking` chunk
- Tool call detected → emit `ToolCallRequested`
- Tool execution complete → emit `ToolCallExecuted`
- 任何範疇 ABC 完成 → emit 對應子事件
- HITL pause → emit `ApprovalRequested`
- HITL resume → emit `ApprovalReceived`
- Loop 結束 → emit `LoopCompleted`

完整事件子類見 [`17.md §4.1`](./17-cross-category-interfaces.md)（22 個 LoopEvent 子類）。

### Streaming 模型（**取代 await 一次拿結果**）

V2 主流量採用 **AsyncIterator streaming** 模式（對齊 Claude Agent SDK `query()`）：

```python
# Loop runtime
async def run(self, *, ..., trace_context: TraceContext) -> AsyncIterator[LoopEvent]:
    """主 loop yield events 而非 return 完整結果。
    消費者（API / SSE handler / OTel exporter）決定下游處理。"""

    yield LoopStarted(session_id=..., trace_context=trace_context)

    async for chunk in chat_client.stream(messages=..., trace_context=trace_context):
        if chunk.type == "thinking_token":
            yield Thinking(content=chunk.delta, trace_context=trace_context)
        elif chunk.type == "tool_call_partial":
            # 累積成完整 ToolCall（Streaming-first 設計，見 01.md 範疇 1）
            ...
        elif chunk.type == "tool_call_complete":
            yield ToolCallRequested(tool_call=accumulated, trace_context=...)

    yield LoopCompleted(stop_reason=..., trace_context=trace_context)
```

### Backpressure 與消費者契約

| 角色 | 職責 |
|------|------|
| **Producer**（Loop runtime） | yield events，不主動 buffer；asyncio coroutine 自然 backpressure |
| **API SSE handler** | `async for event in loop.run(...): await sse_emit(event)`；`await asyncio.sleep(0)` 確保 event loop yield（見 V1 教訓 feedback_sse_streaming_fix） |
| **OTel exporter** | 訂閱所有事件，extract trace_id；獨立 span emission；不影響 Loop 速度 |
| **Frontend EventSource** | 訂閱 named events；reconnect 用 `lastEventId` resume（見 16.md SSE handling 章節） |

### 事件序列保證

每個 LoopEvent 帶 `streaming_seq: int`（**單調遞增 per-loop**），用於：
- Frontend 去重（reconnect 時 dedup）
- Audit log 順序重建
- OTel span ordering

```python
@dataclass
class LoopEvent:
    """Owner: 17.md §4.1"""
    event_type: str
    streaming_seq: int                       # ⭐ 新增：per-loop monotonic
    trace_context: TraceContext              # ⭐ 強制
    timestamp: datetime
    payload: dict
```

### Reconnect / Resume 契約

```python
# Frontend reconnect 帶 last_event_id
GET /api/v1/chat/{session_id}/events?last_event_id=42

# Backend SSE handler
async def stream_events(session_id, last_event_id: int = 0):
    async for event in events_replay_from(session_id, after_seq=last_event_id):
        yield f"id: {event.streaming_seq}\nevent: {event.event_type}\ndata: {json.dumps(event.payload)}\n\n"
```

### 失敗模式

| 失敗 | 處置 |
|------|------|
| Producer 拋例外 | yield `LoopFailed` event 後關閉 iterator；不靜默吞錯 |
| Consumer 處理慢（SSE buffer 滿） | TCP backpressure 自然減速 producer；asyncio 不需手動限速 |
| Reconnect 找不到 last_event_id（已超過保留期） | 回傳 SSE event `replay_unavailable` + 建議用 checkpoint resume |
| Token streaming 中斷 | partial chunk 由 OutputParser 累積；達 stop_reason 才視為完整 message |

### 與業界對比

| 框架 | Streaming 模型 | V2 對應 |
|------|--------------|---------|
| Claude Agent SDK | `async for msg in query()` | ✅ 同模型（Contract 15） |
| OpenAI Agents SDK | `Runner.stream()` → `RunStreamEvent` | ✅ LoopEvent 對應 RunStreamEvent |
| LangGraph | `graph.stream()` per channel | ⚠️ V2 無 channel 概念，Reducer 綁事件而非 state slot（後續 retro 評估升級） |

---

## 範疇呼叫順序圖（典型 Loop 一輪，**2026-04-28 第二輪 review 補完**）

> **Review 修訂**：補 HITL Resume 對稱路徑 + max_corrections 視覺化 + Streaming chunk emit 時機 + Checkpointer 頻率細化。

```
Loop.run() — yield AsyncIterator[LoopEvent]：

A. 起始
   ┌─ emit LoopStarted (streaming_seq=0, trace_context propagation)
   └─ Tracer.start_span(category=LOOP)                  [範疇 12]

B. 每輪 turn（while not stop_reason）：

   1. Compactor.should_compact() / compact()            [範疇 4]
      └─ emit ContextCompacted (if applied)
   2. Checkpointer.snapshot(reason=...)                 [範疇 7]
      ┌─ in-memory shadow（每 turn，free）
      └─ DB write 條件：HITL pause / verification fail / 每 N=5 turn / scheduled
   3. PromptBuilder.build()                             [範疇 5]
      ├─→ Memory.get_layer_summary() (5 layers × 3 time scales)  [範疇 3]
      ├─→ ToolRegistry.list_tools_for_role()            [範疇 2]
      └─→ PromptCacheManager.get_cache_breakpoints()    [範疇 4]
      └─ emit PromptBuilt
   4. ChatClient.stream(messages, tools, trace_context) [Adapter]
      └─ async for chunk:
         ├─ chunk.type == "thinking_token" → emit Thinking         ⭐ Streaming chunk emit 時機
         ├─ chunk.type == "tool_call_partial" → 累積（不執行）
         └─ chunk.type == "stop"  → 退出 streaming
   5. OutputParser.classify(response)                   [範疇 6]
      ├─ 若無 tool_calls → step 9
      └─ 若有 tool_calls → step 6
   6. For each tool_call (concurrency_policy 強制):
      ├─→ emit ToolCallRequested
      ├─→ Guardrail.check_tool_call()                   [範疇 9]
      │   ├─ 若 tripwire → emit TripwireTriggered → 終止
      │   └─ 若 requires_hitl →                         ⭐ HITL Pause 路徑
      │      ├─→ HITLManager.request_approval()         [§HITL]
      │      ├─→ Checkpointer.snapshot(reason="hitl_pause")  [範疇 7]
      │      ├─→ emit ApprovalRequested
      │      └─→ Loop runtime exit (return AsyncIterator end)
      │              ↓
      │         （等待 reviewer 在 governance frontend 決策）
      │              ↓
      │         ⭐ HITL Resume 路徑 ⭐
      │         ├─→ HITLManager.decide() 寫 DB
      │         ├─→ Watcher 偵測 → trigger resume worker
      │         ├─→ Checkpointer.restore(checkpoint_id)
      │         ├─→ StateUpdater.apply(state, decision, HITLDecisionReducer)
      │         ├─→ emit ApprovalReceived
      │         └─→ Loop 從 step 7 繼續（已有 tool_result）
      ├─→ ToolExecutor.execute()                        [範疇 2]
      │   ├─→ Memory.search/write (if memory tool)      [範疇 3]
      │   ├─→ Subagent.fork (if subagent tool, 帶 SubagentBudget)  [範疇 11]
      │   └─→ AuditLogger.log()                         [§9 cross-cutting]
      ├─→ emit ToolCallExecuted
      └─→ ErrorRouter.handle (if error)                 [範疇 8]
          └─ ErrorTerminator: budget exceeded / circuit open → 終止
   7. Append tool_results to state.durable.messages (AppendReducer)
   8. Loop back to step 1 (next turn)

C. 當 LLM 回應無 tool_calls：
   9. Verifier.verify()                                 [範疇 10]
      ├─ verifier 自身錯誤 → fail_closed
      └─ verification.passed:
         ├─ false + state.correction_count < max_corrections (default 2, max 5) →
         │  ├─ correction_count += 1
         │  ├─ emit VerificationFailed
         │  └─ append correction message → goto step 1     ⭐ max_corrections 上限
         ├─ false + correction_count == max_corrections →
         │  ├─ emit VerificationFailed (terminal)
         │  └─ continue with warning
         └─ true → emit VerificationPassed → step 10
   10. Guardrail.check_output()                         [範疇 9]
       ├─ tripwire / fail → 同 step 6 處理
       └─ pass → step 11
   11. emit LoopCompleted
       ├─→ Tracer.end_span(LOOP)                        [範疇 12]
       └─→ AuditLogger.log("loop_ended")                [§9]
```

**圖例**：
- `[範疇 X]` 標示 ABC owner
- `⭐` 標示 2026-04-28 review 補完項目
- 所有 `emit X` 是 Contract 15 streaming yield
- 所有 ABC 呼叫都帶 `trace_context`（cross-cutting，圖中省略以保持可讀）

---

## 跨範疇資料流契約

### LoopState（中央資料結構，**2026-04-28 第二輪 review 拆分為 Transient/Durable**）

> **Review 發現**：原 LoopState 是 flat dataclass，與 Contract 12 引入的 Reducer pattern 脫節（哪些欄位走 LastWriteWinsReducer、哪些走 AppendReducer 形同虛設）。本次切分對齊 Reducer 模型 + 補缺漏欄位。

```python
# 完整定義在 17.md §1.1，本處只列示意

@dataclass
class TransientState:
    """In-memory，loop runtime 操作；checkpoint 不寫 DB。Reducer: LastWriteWinsReducer。"""
    # Identity
    request_id: UUID
    session_id: UUID
    user_id: UUID
    tenant_id: UUID

    # Loop tracking
    turn_count: int
    tokens_used: int
    cost_usd_total: float                # ⭐ 新增：成本累計
    correction_count: int                # max_corrections 上限
    streaming_seq: int                   # ⭐ 新增：事件去重
    deadline_at: datetime | None         # ⭐ 新增：loop 硬截止時間

    # In-flight
    pending_tool_calls: list[ToolCall]
    in_flight_subagents: list[SubagentHandle]

    # Trace
    trace_context: TraceContext          # ⭐ 強制
    parent_request_id: UUID | None       # ⭐ 新增：subagent tree 還原

    # System role / available tools
    system_role: str
    available_tools: list[str]


@dataclass
class DurableState:
    """DB-persisted，HITL pause/resume / time-travel 必經。Reducer: AppendReducer + 領域特定。"""
    session_id: UUID
    tenant_id: UUID

    # Conversation（messages 表 reference，避免重複序列化）
    messages: list[Message]              # AppendReducer

    # Tool history
    completed_tool_results: list[ToolResult]   # AppendReducer

    # HITL（cross-session）
    pending_approval_ids: list[UUID]     # ⭐ 改：原 list[Approval] 改 ID reference

    # Memory pointers（不複製內容，僅 reference）
    memory_layer_versions: dict[str, int]

    # Audit reference（不放 entry，避免 state 線性膨脹）
    audit_trail_count: int               # ⭐ 改：完整 audit 在 audit_log 表查；state 只記筆數

    # Versioning
    version: StateVersion                # counter + content_hash 雙因子
    last_checkpoint_at: datetime
    schema_version: int                  # ⭐ 新增：schema migration 用


@dataclass
class LoopState:
    """Facade，runtime 操作此 composite。"""
    transient: TransientState
    durable: DurableState
```

### Reducer 對齊表

| 欄位 | 所屬 | Reducer | 說明 |
|------|------|---------|------|
| `transient.turn_count` | Transient | `LastWriteWinsReducer` | 純覆蓋 |
| `transient.tokens_used` | Transient | `CounterReducer`（範疇 12） | accumulate |
| `transient.cost_usd_total` | Transient | `CounterReducer` | accumulate |
| `transient.streaming_seq` | Transient | `LastWriteWinsReducer` | monotonic |
| `durable.messages` | Durable | `AppendReducer` | 不可改前面 |
| `durable.completed_tool_results` | Durable | `AppendReducer` | 不可改前面 |
| `durable.pending_approval_ids` | Durable | `HITLDecisionReducer` | merge approve/reject |
| `durable.memory_layer_versions` | Durable | `LastWriteWinsReducer` | per layer 覆蓋 |
| `durable.audit_trail_count` | Durable | `CounterReducer` | accumulate |

### 與 ExecutionContext 的關係

> **Review 發現**：Contract 5 / 8 引用 `ExecutionContext`，與 LoopState「唯一跨範疇資料結構」矛盾。釐清：

- `ExecutionContext` 是 **per-call ephemeral context**（含 session_id / tenant_id / user_id / role / **唯讀** loop_state 引用 + trace_context）
- `LoopState` 是 **per-loop durable + transient state**
- `ExecutionContext` **包含** `loop_state` 唯讀 reference；ABC 接 ExecutionContext 而非 LoopState 直接修改

```python
@dataclass(frozen=True)                  # ⭐ frozen 強制 immutable
class ExecutionContext:
    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    role: str
    loop_state: LoopState                # 唯讀引用（dataclass 內部 mutable，但 ctx 結構 frozen）
    trace_context: TraceContext
```

**規則**：
- ⭐ `LoopState` 是**唯一**跨範疇傳遞的中央資料結構
- ⭐ 範疇間通過 LoopState 通訊，避免直接互相 import 內部資料
- ⭐ 修改 LoopState 必須透過 **Reducer**（Contract 12），不直接 mutation
- ⭐ `DurableState` 修改必須透過 Checkpointer 持久化（含 outbox 補償）

---

## 結語

本契約文件定義 11 範疇間如何協作的權威 API。

**Phase 49.3 必須實作完成本文件中所有 ABC 簽名**（即使內部尚無實作）。
**Phase 50+ 各範疇實作必須遵守這些契約**。

任何違反 contract 的 PR：CI 強制 fail。
