# V9 Deep Semantic Verification: mod-integration-batch1.md

> **Date**: 2026-03-31 | **Scope**: agent_framework/, claude_sdk/, ag_ui/ modules
> **Method**: Glob file lists + Grep class/function names + Read source files
> **Target**: `docs/07-analysis/V9/02-modules/mod-integration-batch1.md`

---

## Summary

| Category | Points | ✅ Pass | ❌ Fail | ⚠️ Minor | Score |
|----------|--------|---------|---------|----------|-------|
| agent_framework/ (P1–P20) | 20 | 15 | 2 | 3 | 15/20 |
| claude_sdk/ (P21–P40) | 20 | 15 | 2 | 3 | 15/20 |
| ag_ui/ (P41–P60) | 20 | 16 | 1 | 3 | 16/20 |
| **Total** | **60** | **46** | **5** | **9** | **46/60 (76.7%)** |

---

## agent_framework/ Module (P1–P20)

### P1–P5: builders/ 目錄下的 builder 文件列表

- **P1** ✅ builders/ 下有 23 個 .py 文件（含 `__init__.py`），實際 builder 類文件 22 個
- **P2** ⚠️ 文件聲稱「30+ builders」— 實際 builder 類有 ~19 個 adapter/builder classes（含 migration 層），但不足 30。此數字指的可能是 builder + factory functions 總數，但描述模糊
- **P3** ✅ 15 個 Builder Adapter 列表（表格中列出）全部在源碼中確認存在：
  - `ConcurrentBuilderAdapter` → `concurrent.py` ✅
  - `HandoffBuilderAdapter` → `handoff.py` ✅
  - `GroupChatBuilderAdapter` → `groupchat.py` ✅
  - `MagenticBuilderAdapter` → `magentic.py` ✅
  - `WorkflowExecutorAdapter` → `workflow_executor.py` ✅
  - `GroupChatVotingAdapter` → `groupchat_voting.py` ✅
  - `HandoffPolicyAdapter` → `handoff_policy.py` ✅
  - `CapabilityMatcherAdapter` → `handoff_capability.py` ✅
  - `ContextTransferAdapter` → `handoff_context.py` ✅
  - `HandoffService` → `handoff_service.py` ✅
  - `NestedWorkflowAdapter` → `nested_workflow.py` ✅
  - `PlanningAdapter` → `planning.py` ✅
  - `AgentExecutorAdapter` → `agent_executor.py` ✅
  - `CodeInterpreterAdapter` → `code_interpreter.py` ✅
  - `MultiTurnAdapter` → `multiturn/adapter.py` ✅
- **P4** ✅ 附加文件確認存在：`edge_routing.py`, `groupchat_orchestrator.py`, `handoff_hitl.py`
- **P5** ✅ `__init__.py` 存在，作為 builders 模組入口

### P6–P10: 每個 builder 的 class 名稱和 build() 方法

- **P6** ✅ 所有主要 adapter 類名稱與文件中描述一致（見 P3 列表）
- **P7** ✅ `build()` 方法在 8 個 builder 中確認存在：concurrent, handoff, groupchat, magentic, nested_workflow(x2), workflow_executor, planning
- **P8** ⚠️ 文件聲稱「12 builder adapters + migration layers」— 實際有 15 個 adapter 加上 5 個 migration 文件，表格列出更多。數字不完全精確但範圍正確
- **P9** ✅ Migration 層的 adapter 類確認：`ConcurrentExecutorAdapter`, `GroupChatManagerAdapter`, `HandoffControllerAdapter`, `MagenticManagerAdapter`, `NestedWorkflowManagerAdapter`
- **P10** ✅ Factory functions 如 `create_all_concurrent()`, `create_handoff_adapter()` 等在表格中描述正確

### P11–P13: memory/ 子模組

- **P11** ✅ `memory/` 子目錄存在，包含 4 個文件：`__init__.py`, `base.py`, `redis_storage.py`, `postgres_storage.py`
- **P12** ✅ 文件中提及 memory 子模組存在，功能描述合理
- **P13** ⚠️ 文件未詳細描述 memory/ 的類名和 API，只在 "Additional subsystems" 行簡要提及

### P14–P16: _migration.py 文件

- **P14** ❌ **文件聲稱 P14-P16 涉及 `_migration.py` 單一文件** — 實際不存在 `_migration.py` 這個文件。Migration 文件是 5 個獨立文件在 builders/ 下：`concurrent_migration.py`, `handoff_migration.py`, `groupchat_migration.py`, `magentic_migration.py`, `workflow_executor_migration.py`
- **P15** ✅ Known Issues 部分正確提到「5 legacy migration modules still present」— 與實際 5 個 migration 文件一致
- **P16** ✅ Migration 文件的存在已確認，且文件名命名正確

### P17–P20: agent_framework 與 MAF SDK 整合方式

- **P17** ✅ MAF Compliance Status 描述正確：import official class → `self._builder = OfficialBuilder()` → `self._builder.build()`
- **P18** ✅ 依賴 `agent_framework` (pip package) 的描述正確
- **P19** ✅ `acl/` 子模組存在（`adapter.py`, `interfaces.py`, `version_detector.py`），但文件中未提及此重要子模組
- **P20** ❌ 文件計數聲稱「57 .py files」— 實際計數 57 個 ✅（修正：此項通過，與 `find` 計數一致）

**修正**：P20 重新確認為 ✅，agent_framework 有 57 個 .py 文件，與文件聲稱一致。P14 的 `_migration.py` 是驗證任務描述的問題，不是文件本身的問題。文件本身正確描述了 5 個 migration modules。

---

## claude_sdk/ Module (P21–P40)

### P21–P25: claude_sdk/ 的子目錄結構

- **P21** ✅ 子目錄確認：`autonomous/`, `hooks/`, `hybrid/`, `mcp/`, `tools/` — 全部存在
- **P22** ✅ 額外子目錄 `orchestrator/` 存在且在文件中正確描述
- **P23** ✅ 頂層文件：`client.py`, `session.py`, `config.py`, `exceptions.py`, `types.py`, `query.py`, `session_state.py` — 全部確認
- **P24** ⚠️ 文件聲稱「48 .py files」— 實際計數為 48 個 ✅
- **P25** ✅ 子目錄結構與 CLAUDE.md 中的描述一致

### P26–P30: 每個子模組的主要類/函數名稱

- **P26** ✅ `ClaudeSDKClient` in `client.py` — 確認存在
- **P27** ✅ `Session` in `session.py` — 確認存在
- **P28** ✅ `ClaudeCoordinator` in `orchestrator/coordinator.py` — 確認存在
- **P29** ✅ `QueryResult` in `types.py` — 確認存在
- **P30** ✅ `SessionResponse` in `types.py` — 確認存在（文件中 Session 類的 `query()` 返回 `SessionResponse`）

### P31–P33: Claude SDK 整合的實際 import 和配置

- **P31** ✅ 依賴 `anthropic` (pip) 的描述正確
- **P32** ✅ 配置變量 `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CLAUDE_MAX_TOKENS` 描述合理
- **P33** ⚠️ Known Issues 提到「No official Claude Agent SDK package」— 描述準確但措辭可能令人困惑，因為模組名為 `claude_sdk` 卻不使用獨立 SDK 包

### P34–P36: hooks 機制的實際實現

- **P34** ✅ Hook chain 結構正確：`Hook` (ABC) + `HookChain` in `base.py`
- **P35** ✅ Hook 實現確認：
  - `ApprovalHook` → `approval.py` ✅
  - `AuditHook` → `audit.py` ✅
  - `RateLimitHook` → `rate_limit.py` ✅
  - `SandboxHook` → `sandbox.py` ✅
- **P36** ❌ **文件未提及 `approval_delegate.py`** — 此文件包含 `ClaudeApprovalDelegate` 類，是 hooks 目錄的重要組件但未被列入文件描述。Hook 列表為「Approval → Audit → RateLimit → Sandbox」但實際多了 `approval_delegate`

### P37–P40: tools 註冊和調用的實際流程

- **P37** ✅ `tools/registry.py` 使用函數式註冊（`register_tool()`, `get_tool_instance()`）而非類 — 文件描述為「Tool registration and discovery」基本正確
- **P38** ❌ **文件聲稱 `autonomous/engine.py`** — 實際文件名為 `autonomous/executor.py`，包含 `PlanExecutor` 類。不存在 `engine.py`
- **P39** ✅ autonomous/ 目錄文件列表確認：`types.py`, `analyzer.py`, `planner.py`, `executor.py`, `verifier.py`, `retry.py`, `fallback.py`
- **P40** ⚠️ tools/registry.py 不是類而是模組級函數 (`register_tool`, `get_tool_instance`, `list_tools`)。文件簡述為「Tools Registry」未區分是否為類

---

## ag_ui/ Module (P41–P60)

### P41–P45: ag_ui/ 的文件列表

- **P41** ✅ 文件計數：27 個 .py 文件 — 與文件聲稱「27 .py files」一致
- **P42** ✅ 頂層文件確認：`bridge.py`, `converters.py`, `mediator_bridge.py`, `sse_buffer.py`
- **P43** ✅ 子目錄結構確認：`events/`, `features/`, `thread/`
- **P44** ✅ `features/` 包含：`agentic_chat.py`, `generative_ui.py`, `human_in_loop.py`, `tool_rendering.py`, `approval_delegate.py` + `advanced/` 子目錄
- **P45** ⚠️ `features/` 目錄和 `advanced/` 子目錄在文件中未被詳細描述。文件只列出 events/ 和 thread/，缺少 features/ 的完整文件列表

### P46–P50: SSE event handling 的實際實現

- **P46** ✅ `events/` 目錄包含 6 個文件：`base.py`, `lifecycle.py`, `message.py`, `tool.py`, `state.py`, `progress.py` — 與文件描述的「6 files」一致
- **P47** ✅ Event 類型確認存在：
  - `BaseAGUIEvent`, `AGUIEventType`, `RunFinishReason` → `base.py` ✅
  - `RunStartedEvent`, `RunFinishedEvent` → `lifecycle.py` ✅（非 base.py）
  - `TextMessageStartEvent`, `TextMessageContentEvent`, `TextMessageEndEvent` → `message.py` ✅
  - `ToolCallStartEvent`, `ToolCallEndEvent` → `tool.py` ✅
  - `StateSnapshotEvent`, `CustomEvent` → `state.py` ✅
- **P48** ❌ **文件聲稱 `RunStartedEvent` 和 `RunFinishedEvent` 在 `base.py`，`CustomEvent` 在 `base.py`** — 實際：
  - `RunStartedEvent`, `RunFinishedEvent` 在 `lifecycle.py`（非 base.py）
  - `CustomEvent` 在 `state.py`（非 base.py）
  - `RunFinishReason` 在 `base.py`（非 lifecycle.py）
  - 文件表格中的文件位置分配有多處錯誤
- **P49** ✅ `ToolCallArgsEvent` 存在於 `tool.py` — 文件未列出此事件但它確實存在
- **P50** ⚠️ 文件聲稱「11 event types」— 實際 event classes 更多（含 `ToolCallArgsEvent`, `StateDeltaEvent`, `StateDeltaItem` 等），最少 13+ 個事件相關類

### P51–P53: mediator_bridge 的功能和接口

- **P51** ✅ `mediator_bridge.py` 存在，包含 `MediatorEventBridge` 類
- **P52** ✅ `MediatorEventBridge` 方法確認：`stream_events()`, `convert_event()`, `_format_sse()`
- **P53** ⚠️ 文件圖表中提到 `MediatorEventBridge` 作為 hybrid/ 模組的組件之一，但未在 ag_ui/ 的 Public API 部分詳細描述

### P54–P56: AG-UI protocol compliance 描述

- **P54** ✅ HybridEventBridge 的描述正確：`stream_events()` 返回 `AsyncGenerator[str, None]`
- **P55** ✅ `RunAgentInput` dataclass 字段描述正確：`prompt`, `thread_id`, `run_id`, `session_id`, `force_mode`, `tools`, `file_ids`
- **P56** ✅ `BridgeConfig` dataclass 存在且文件中有描述

### P57–P60: 前後端 AG-UI 組件的對應關係

- **P57** ✅ Dependents 表格正確列出 `api/v1/ag_ui/` 和 `swarm/events/emitter.py`
- **P58** ✅ Dependencies 描述正確：依賴 `converters.py`, `events/*`, 以及 TYPE_CHECKING 中的 `hybrid/orchestrator_v2` 和 `swarm/events`
- **P59** ✅ Thread management 描述正確：`ThreadManager`, Redis-backed storage
- **P60** ✅ Known Issues 描述合理：heartbeat interval 2s 和 large bridge file

---

## Corrections Required

### ❌ Critical Errors (Must Fix)

| # | Location | Issue | Fix |
|---|----------|-------|-----|
| 1 | claude_sdk/ P38 | `autonomous/engine.py` 不存在 | 改為 `autonomous/executor.py`，類名為 `PlanExecutor` |
| 2 | ag_ui/ events P48 | Event class 文件歸屬錯誤 | `RunStartedEvent`/`RunFinishedEvent` → `lifecycle.py`；`CustomEvent` → `state.py`；`RunFinishReason` → `base.py` |
| 3 | claude_sdk/ P36 | 缺少 `approval_delegate.py` | hooks/ 列表應包含 `approval_delegate.py` (`ClaudeApprovalDelegate`) |

### ⚠️ Minor Inaccuracies (Should Fix)

| # | Location | Issue | Fix |
|---|----------|-------|-----|
| 4 | agent_framework P2 | 「30+ builders」數字偏高 | 改為「~19 adapter classes + 5 migration adapters + factory functions」或「23 builder files」 |
| 5 | ag_ui/ events P50 | 「11 event types」偏低 | 改為「13+ event classes across 6 files」（含 ToolCallArgsEvent, StateDeltaEvent 等） |
| 6 | ag_ui/ P45 | 缺少 features/ 子目錄描述 | 新增 features/ 文件列表（agentic_chat, generative_ui, human_in_loop, tool_rendering, approval_delegate, advanced/） |
| 7 | agent_framework P13 | memory/ 子模組描述過於簡略 | 補充 base.py, redis_storage.py, postgres_storage.py 的類名 |
| 8 | claude_sdk/ P40 | tools/registry.py 非類而是函數 | 明確說明是模組級函數：`register_tool()`, `get_tool_instance()`, `list_tools()` |
| 9 | agent_framework P19 | 缺少 acl/ 子模組描述 | acl/ 包含 adapter.py, interfaces.py, version_detector.py — 是 MAF 版本兼容的關鍵子模組 |

### 🔍 Additional Observations

1. **agent_framework** 實際包含更多子模組（`acl/`, `assistant/`, `core/`, `multiturn/`, `tools/`），文件中的描述集中在 builders/ 上但遺漏其他子模組的詳細 API
2. **claude_sdk** 的 `orchestrator/` 子目錄（含 `coordinator.py`, `context_manager.py`, `task_allocator.py`）在文件中有提及但未列出完整類名
3. **ag_ui** 的 `features/advanced/` 子目錄包含 `tool_ui.py`, `shared_state.py`, `predictive.py`，在文件中完全未提及
4. 文件計數全部正確：agent_framework=57, claude_sdk=48, ag_ui=27

---

## Verification Matrix

| Point | Status | Details |
|-------|--------|---------|
| P1 | ✅ | builders/ 有 23 個 .py 文件 |
| P2 | ⚠️ | 「30+ builders」偏高，實際 ~19 adapter classes |
| P3 | ✅ | 15 個 adapter 全部確認存在 |
| P4 | ✅ | 附加文件確認 |
| P5 | ✅ | __init__.py 存在 |
| P6 | ✅ | 類名正確 |
| P7 | ✅ | build() 方法存在 |
| P8 | ⚠️ | 「12 builder adapters」數字不精確 |
| P9 | ✅ | Migration adapter 類確認 |
| P10 | ✅ | Factory functions 確認 |
| P11 | ✅ | memory/ 結構正確 |
| P12 | ✅ | memory 功能描述合理 |
| P13 | ⚠️ | memory/ 描述過於簡略 |
| P14 | ✅ | 5 個 migration 文件存在（驗證任務描述有誤，文件本身正確） |
| P15 | ✅ | Known Issues 正確提到 5 個 migration |
| P16 | ✅ | Migration 文件名正確 |
| P17 | ✅ | MAF Compliance 描述正確 |
| P18 | ✅ | 依賴描述正確 |
| P19 | ❌ | 缺少 acl/ 子模組描述 |
| P20 | ✅ | 文件計數 57 正確 |
| P21 | ✅ | 子目錄結構正確 |
| P22 | ✅ | orchestrator/ 存在 |
| P23 | ✅ | 頂層文件正確 |
| P24 | ✅ | 文件計數 48 正確 |
| P25 | ✅ | 結構一致 |
| P26 | ✅ | ClaudeSDKClient 確認 |
| P27 | ✅ | Session 確認 |
| P28 | ✅ | ClaudeCoordinator 確認 |
| P29 | ✅ | QueryResult 確認 |
| P30 | ✅ | SessionResponse 確認 |
| P31 | ✅ | anthropic 依賴正確 |
| P32 | ✅ | 配置變量正確 |
| P33 | ⚠️ | SDK 命名措辭可能混淆 |
| P34 | ✅ | Hook/HookChain 架構正確 |
| P35 | ✅ | 4 個 Hook 實現確認 |
| P36 | ❌ | 缺少 approval_delegate.py |
| P37 | ✅ | registry 功能正確 |
| P38 | ❌ | engine.py 不存在，應為 executor.py |
| P39 | ✅ | autonomous/ 文件列表正確 |
| P40 | ⚠️ | registry 是函數非類 |
| P41 | ✅ | 文件計數 27 正確 |
| P42 | ✅ | 頂層文件正確 |
| P43 | ✅ | 子目錄結構正確 |
| P44 | ✅ | features/ 內容確認 |
| P45 | ⚠️ | features/ 描述不完整 |
| P46 | ✅ | events/ 6 個文件正確 |
| P47 | ✅ | Event 類存在 |
| P48 | ❌ | Event 文件歸屬有誤 |
| P49 | ✅ | ToolCallArgsEvent 存在 |
| P50 | ⚠️ | 「11 event types」偏低 |
| P51 | ✅ | MediatorEventBridge 存在 |
| P52 | ✅ | 方法簽名確認 |
| P53 | ⚠️ | mediator_bridge 未在 Public API 詳述 |
| P54 | ✅ | HybridEventBridge 描述正確 |
| P55 | ✅ | RunAgentInput 字段正確 |
| P56 | ✅ | BridgeConfig 存在 |
| P57 | ✅ | Dependents 正確 |
| P58 | ✅ | Dependencies 正確 |
| P59 | ✅ | Thread management 正確 |
| P60 | ✅ | Known Issues 合理 |
