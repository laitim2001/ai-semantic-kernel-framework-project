# MAF 使用完整掃描報告

> **掃描日期**: 2026-03-15
> **掃描範圍**: `backend/src/` 全目錄 + `backend/tests/` + 配置檔案
> **版本鎖定**: `agent-framework>=1.0.0b260114,<2.0.0` (requirements.txt:20)

---

## 1. Import 語句清單

### 1.1 直接 `from agent_framework import` 語句（活躍程式碼）

| # | 檔案路徑 | 行號 | Import 語句 | 引入的類別/函數 |
|---|----------|------|-------------|----------------|
| 1 | `integrations/agent_framework/builders/concurrent.py` | 83 | `from agent_framework import ConcurrentBuilder` | ConcurrentBuilder |
| 2 | `integrations/agent_framework/builders/groupchat.py` | 83-87 | `from agent_framework import (GroupChatBuilder)` | GroupChatBuilder |
| 3 | `integrations/agent_framework/builders/handoff.py` | 54-57 | `from agent_framework import (HandoffBuilder, HandoffAgentUserRequest)` | HandoffBuilder, HandoffAgentUserRequest |
| 4 | `integrations/agent_framework/builders/magentic.py` | 39-43 | `from agent_framework import (MagenticBuilder, MagenticManagerBase, StandardMagenticManager)` | MagenticBuilder, MagenticManagerBase, StandardMagenticManager |
| 5 | `integrations/agent_framework/builders/planning.py` | 31 | `from agent_framework import MagenticBuilder, Workflow` | MagenticBuilder, Workflow |
| 6 | `integrations/agent_framework/builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | WorkflowBuilder, Workflow, WorkflowExecutor |
| 7 | `integrations/agent_framework/builders/workflow_executor.py` | 52-56 | `from agent_framework import (WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage)` | WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage |
| 8 | `integrations/agent_framework/builders/agent_executor.py` | 155 | `from agent_framework import ChatAgent, ChatMessage, Role` | ChatAgent, ChatMessage, Role |
| 9 | `integrations/agent_framework/builders/agent_executor.py` | 156 | `from agent_framework.azure import AzureOpenAIResponsesClient` | AzureOpenAIResponsesClient |
| 10 | `integrations/agent_framework/core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | Workflow, WorkflowBuilder, Edge, Executor |
| 11 | `integrations/agent_framework/core/executor.py` | 38 | `from agent_framework import Executor, WorkflowContext, handler` | Executor, WorkflowContext, handler |
| 12 | `integrations/agent_framework/core/execution.py` | 34 | `from agent_framework import ChatAgent, SequentialBuilder, Workflow` | ChatAgent, SequentialBuilder, Workflow |
| 13 | `integrations/agent_framework/core/edge.py` | 29 | `from agent_framework import Edge` | Edge |
| 14 | `integrations/agent_framework/core/events.py` | 34 | `from agent_framework import WorkflowStatusEvent` | WorkflowStatusEvent |
| 15 | `integrations/agent_framework/core/approval.py` | 39 | `from agent_framework import Executor, handler, WorkflowContext` | Executor, handler, WorkflowContext |
| 16 | `integrations/agent_framework/core/approval_workflow.py` | 36 | `from agent_framework import Workflow, Edge` | Workflow, Edge |
| 17 | `integrations/agent_framework/multiturn/adapter.py` | 27-31 | `from agent_framework import (CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint)` | CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint |
| 18 | `integrations/agent_framework/multiturn/checkpoint_storage.py` | 31 | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` | CheckpointStorage, InMemoryCheckpointStorage |
| 19 | `integrations/agent_framework/memory/base.py` | 25 | `from agent_framework import Context, ContextProvider` | Context, ContextProvider |
| 20 | `integrations/agent_framework/memory/base.py` | 169 | `from agent_framework import MemoryStorage` | MemoryStorage (lazy import) |
| 21 | `integrations/agent_framework/checkpoint.py` | 102 | `from agent_framework import WorkflowCheckpoint` | WorkflowCheckpoint (lazy import) |
| 22 | `integrations/agent_framework/workflow.py` | 425 | `from agent_framework import WorkflowBuilder` | WorkflowBuilder (lazy import) |
| 23 | `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage` | InMemoryCheckpointStorage |

### 1.2 `import agent_framework` 語句（動態引用）

| # | 檔案路徑 | 行號 | 用途 |
|---|----------|------|------|
| 1 | `integrations/agent_framework/acl/version_detector.py` | 85 | `import agent_framework` — 讀取 `__version__` |
| 2 | `integrations/agent_framework/acl/version_detector.py` | 135 | `import agent_framework` — `hasattr(agent_framework, api_name)` 檢查 |
| 3 | `integrations/agent_framework/acl/version_detector.py` | 165 | `import agent_framework` — 批次 API 可用性檢查 |
| 4 | `integrations/agent_framework/acl/adapter.py` | 139 | `import agent_framework` — `getattr(agent_framework, maf_class_name)` 動態取類別 |

### 1.3 測試中的 MAF 使用

> **結果**: `backend/tests/` 中**未發現**任何 `from agent_framework` import 語句。
> 所有測試均透過 IPA 自有適配器層進行，不直接引用 MAF 套件。

### 1.4 配置與版本鎖定

| # | 檔案路徑 | 行號 | 內容 |
|---|----------|------|------|
| 1 | `backend/requirements.txt` | 20 | `agent-framework>=1.0.0b260114,<2.0.0` |

---

## 2. 受 Breaking Change 影響的使用點

### BC-01: AgentRunResponse 移除

**變更**: `AgentRunResponse` 和 `AgentRunResponseUpdate` 從 `agent_framework` 中移除。

| # | 檔案 | 行號 | 目前使用 | 影響分析 |
|---|------|------|---------|---------|
| 1 | `api/v1/agents/routes.py` | 28, 321, 330, 379 | `AgentRunResponse` 作為 response_model 和回傳型別 | **不受影響** — 這是 IPA 自定義 schema (`domain/agents/schemas.py:125`)，非 MAF 類別 |
| 2 | `domain/agents/schemas.py` | 125 | `class AgentRunResponse(BaseModel)` | **不受影響** — IPA 自定義 Pydantic model |
| 3 | `domain/agents/__init__.py` | 18, 28 | re-export | **不受影響** — 引用自身 schema |

**結論**: IPA 的 `AgentRunResponse` 是自定義類別，與 MAF 同名但不同源。**0 個使用點受影響**。

### BC-02: create_agent 更名為 create_run

**變更**: `create_agent()` 方法重命名為 `create_run()`。

| # | 檔案 | 行號 | 目前使用 | 影響分析 |
|---|------|------|---------|---------|
| 1 | `builders/agent_executor.py` | 262 | `def create_agent(self, config)` | **不受影響** — 這是 IPA 自定義方法名，非呼叫 MAF API |

**結論**: IPA 未直接呼叫 MAF 的 `create_agent()`。**0 個使用點受影響**。

### BC-03: display_name 更名為 name

**變更**: Agent 的 `display_name` 屬性更名為 `name`。

**結論**: 在 `integrations/agent_framework/` 中未發現直接使用 `display_name` 設定 MAF Agent 屬性的程式碼。需在升級時驗證 Builder adapter 內部是否透過 dict/kwargs 傳遞此屬性。**潛在影響，需人工驗證**。

### BC-04: context_providers 更名為 context_provider (單數)

**變更**: `context_providers` (複數) 更名為 `context_provider` (單數)。

| # | 檔案 | 行號 | 目前使用 | 影響分析 |
|---|------|------|---------|---------|
| — | — | — | — | 搜索未發現 `context_providers` 的直接使用 |

**結論**: **0 個使用點受影響**。但 `memory/base.py:25` import 了 `ContextProvider`，如果此類別本身 API 有變則需注意。

### BC-05: source_executor_id 更名為 source

**變更**: `source_executor_id` 更名為 `source`。

| # | 檔案 | 行號 | 目前使用 | 影響分析 |
|---|------|------|---------|---------|
| 1 | `builders/edge_routing.py` | 142 | `def source_executor_ids(self) -> List[str]` | **不受影響** — IPA 自定義屬性名，非 MAF 屬性 |

**結論**: **0 個直接使用點受影響**。但 `core/edge.py` 使用 `Edge`，內部可能透過參數傳遞 `source_executor_id`，需人工驗證。

### BC-06: Exception 類別重命名

**變更**: `ServiceException` → `AgentFrameworkException` 等。

**結論**: 搜索未發現任何 `ServiceException`, `ServiceInitializationError`, `ServiceResponseException`, `AgentExecutionException`, `AgentInvocationError`, `AgentInitializationError` 的引用。**0 個使用點受影響**。

### BC-07: 命名空間遷移（頂層 → 子模組）

**變更**: 所有類別從 `agent_framework` 頂層移至子模組 (如 `agent_framework.agents`, `agent_framework.workflows` 等)。

**這是影響最大的 Breaking Change。** 所有 23 條活躍 import 語句都從頂層 `agent_framework` import，全部需要遷移。

| # | 檔案 | 行號 | 目前 import | 需改為（預估） |
|---|------|------|-----------|--------------|
| 1 | `builders/concurrent.py` | 83 | `from agent_framework import ConcurrentBuilder` | `from agent_framework.workflows.orchestrations import ConcurrentBuilder` |
| 2 | `builders/groupchat.py` | 83 | `from agent_framework import GroupChatBuilder` | `from agent_framework.workflows.orchestrations import GroupChatBuilder` |
| 3 | `builders/handoff.py` | 54 | `from agent_framework import HandoffBuilder, HandoffAgentUserRequest` | `from agent_framework.workflows.orchestrations import HandoffBuilder`; `from agent_framework.workflows import HandoffAgentUserRequest` |
| 4 | `builders/magentic.py` | 39 | `from agent_framework import MagenticBuilder, MagenticManagerBase, StandardMagenticManager` | `from agent_framework.workflows.orchestrations import MagenticBuilder, MagenticManagerBase, StandardMagenticManager` |
| 5 | `builders/planning.py` | 31 | `from agent_framework import MagenticBuilder, Workflow` | `from agent_framework.workflows.orchestrations import MagenticBuilder`; `from agent_framework.workflows import Workflow` |
| 6 | `builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | `from agent_framework.workflows import Workflow, WorkflowBuilder, WorkflowExecutor` |
| 7 | `builders/workflow_executor.py` | 52 | `from agent_framework import WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage` | `from agent_framework.workflows import WorkflowExecutor, SubWorkflowRequestMessage, SubWorkflowResponseMessage` |
| 8 | `builders/agent_executor.py` | 155 | `from agent_framework import ChatAgent, ChatMessage, Role` | `from agent_framework.agents import ChatAgent`; `from agent_framework.agents import ChatMessage, Role` |
| 9 | `builders/agent_executor.py` | 156 | `from agent_framework.azure import AzureOpenAIResponsesClient` | 可能不變或 `from agent_framework.clients.azure import AzureOpenAIResponsesClient` |
| 10 | `core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | `from agent_framework.workflows import Workflow, WorkflowBuilder, Edge, Executor` |
| 11 | `core/executor.py` | 38 | `from agent_framework import Executor, WorkflowContext, handler` | `from agent_framework.workflows import Executor, WorkflowContext, handler` |
| 12 | `core/execution.py` | 34 | `from agent_framework import ChatAgent, SequentialBuilder, Workflow` | `from agent_framework.agents import ChatAgent`; `from agent_framework.workflows.orchestrations import SequentialBuilder`; `from agent_framework.workflows import Workflow` |
| 13 | `core/edge.py` | 29 | `from agent_framework import Edge` | `from agent_framework.workflows import Edge` |
| 14 | `core/events.py` | 34 | `from agent_framework import WorkflowStatusEvent` | `from agent_framework.workflows import WorkflowStatusEvent` |
| 15 | `core/approval.py` | 39 | `from agent_framework import Executor, handler, WorkflowContext` | `from agent_framework.workflows import Executor, handler, WorkflowContext` |
| 16 | `core/approval_workflow.py` | 36 | `from agent_framework import Workflow, Edge` | `from agent_framework.workflows import Workflow, Edge` |
| 17 | `multiturn/adapter.py` | 27 | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint` | `from agent_framework.workflows import CheckpointStorage, InMemoryCheckpointStorage, WorkflowCheckpoint` |
| 18 | `multiturn/checkpoint_storage.py` | 31 | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` | `from agent_framework.workflows import CheckpointStorage, InMemoryCheckpointStorage` |
| 19 | `memory/base.py` | 25 | `from agent_framework import Context, ContextProvider` | `from agent_framework.agents import Context, ContextProvider` |
| 20 | `memory/base.py` | 169 | `from agent_framework import MemoryStorage` | `from agent_framework.agents import MemoryStorage` |
| 21 | `checkpoint.py` | 102 | `from agent_framework import WorkflowCheckpoint` | `from agent_framework.workflows import WorkflowCheckpoint` |
| 22 | `workflow.py` | 425 | `from agent_framework import WorkflowBuilder` | `from agent_framework.workflows import WorkflowBuilder` |
| 23 | `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework import InMemoryCheckpointStorage` | `from agent_framework.workflows import InMemoryCheckpointStorage` |

### BC-08: AFBaseSettings 移除

**結論**: 搜索未發現 `AFBaseSettings` 的使用。**0 個使用點受影響**。

### BC-09: AggregateContextProvider 移除

**結論**: 搜索未發現 `AggregateContextProvider` 的使用。**0 個使用點受影響**。

### BC-10: FunctionTool 泛型移除

**變更**: `FunctionTool[Any]` 不再支援泛型參數。

**結論**: 搜索未發現 `FunctionTool[` 的使用。**0 個使用點受影響**。

### BC-11: 事件 isinstance 檢查

**結論**: 搜索未發現在 MAF 相關程式碼中對事件進行 `isinstance` 檢查。**0 個使用點受影響**。

### BC-12: ad_token_provider / get_entra_auth_token

**結論**: 搜索未發現 `ad_token_provider` 或 `get_entra_auth_token` 的使用。**0 個使用點受影響**。

### BC-13: InMemoryHistoryProvider 移除

**結論**: 搜索未發現 `InMemoryHistoryProvider` 的使用。**0 個使用點受影響**。

### BC-14: WorkflowOutputEvent 移除

**結論**: 搜索未發現 `WorkflowOutputEvent` 的使用。**0 個使用點受影響**。

---

## 3. AG-UI 相關使用

在 `backend/src/integrations/ag_ui/` 目錄中搜索 `agent_framework` 的結果：

> **結果**: `integrations/ag_ui/` 中**未發現**任何直接引用 `agent_framework` 的程式碼。

AG-UI 整合層透過 IPA 自身的適配器層（`integrations/agent_framework/`）間接使用 MAF，不直接 import MAF 套件。

---

## 4. 測試中的使用

在 `backend/tests/` 目錄中搜索的結果：

> **結果**: `backend/tests/` 中**未發現**任何 `from agent_framework` import 語句。

所有測試均透過 IPA 的 adapter/builder 層進行，不直接依賴 MAF 套件。這意味著：
- 測試不需要直接修改 import
- 但如果 adapter 層 API 因升級而改變，測試中的 mock/assert 可能需要更新

---

## 5. 配置和文件引用

### 5.1 套件版本鎖定

| 檔案 | 行號 | 內容 |
|------|------|------|
| `backend/requirements.txt` | 20 | `agent-framework>=1.0.0b260114,<2.0.0` |

### 5.2 ACL 版本偵測器

| 檔案 | 用途 |
|------|------|
| `integrations/agent_framework/acl/version_detector.py` | 動態偵測 MAF 版本和 API 可用性 |
| `integrations/agent_framework/acl/adapter.py` | 動態載入 MAF 類別 via `getattr(agent_framework, class_name)` |

ACL 層會在以下 API 名稱上做可用性檢查 (version_detector.py:155-161):
- `ChatAgent`
- `CheckpointStorage`
- 其他透過 `has_api()` 動態檢查的名稱

### 5.3 CLAUDE.md 文件引用

`backend/src/integrations/agent_framework/CLAUDE.md` 包含完整的 MAF 使用指南，列出：
- 官方 import 模式 (行 24-44)
- Builder 實現規範 (行 120+)
- 所有 adapter 到 MAF 類別的映射 (行 191+)

---

## 6. 統計摘要

### 6.1 總覽

| 指標 | 數量 |
|------|------|
| **使用 MAF 的 .py 檔案數** | **18** |
| **活躍 `from agent_framework import` 語句** | **23** |
| **動態 `import agent_framework` 語句** | **4** |
| **引入的唯一 MAF 類別/函數** | **28** |
| **測試中的直接 MAF 引用** | **0** |
| **AG-UI 中的直接 MAF 引用** | **0** |

### 6.2 引入的所有唯一 MAF 類別/函數

| # | 類別/函數名 | 引入位置數 | 所屬模組（預估遷移目標） |
|---|-----------|-----------|----------------------|
| 1 | `ConcurrentBuilder` | 1 | `workflows.orchestrations` |
| 2 | `GroupChatBuilder` | 1 | `workflows.orchestrations` |
| 3 | `HandoffBuilder` | 1 | `workflows.orchestrations` |
| 4 | `HandoffAgentUserRequest` | 1 | `workflows` |
| 5 | `MagenticBuilder` | 2 | `workflows.orchestrations` |
| 6 | `MagenticManagerBase` | 1 | `workflows.orchestrations` |
| 7 | `StandardMagenticManager` | 1 | `workflows.orchestrations` |
| 8 | `SequentialBuilder` | 1 | `workflows.orchestrations` |
| 9 | `WorkflowBuilder` | 3 | `workflows` |
| 10 | `Workflow` | 4 | `workflows` |
| 11 | `WorkflowExecutor` | 2 | `workflows` |
| 12 | `SubWorkflowRequestMessage` | 1 | `workflows` |
| 13 | `SubWorkflowResponseMessage` | 1 | `workflows` |
| 14 | `Edge` | 3 | `workflows` |
| 15 | `Executor` | 3 | `workflows` |
| 16 | `WorkflowContext` | 2 | `workflows` |
| 17 | `handler` | 2 | `workflows` |
| 18 | `WorkflowStatusEvent` | 1 | `workflows` |
| 19 | `WorkflowCheckpoint` | 2 | `workflows` |
| 20 | `ChatAgent` | 2 | `agents` |
| 21 | `ChatMessage` | 1 | `agents` |
| 22 | `Role` | 1 | `agents` |
| 23 | `CheckpointStorage` | 2 | `workflows` |
| 24 | `InMemoryCheckpointStorage` | 3 | `workflows` |
| 25 | `Context` | 1 | `agents` |
| 26 | `ContextProvider` | 1 | `agents` |
| 27 | `MemoryStorage` | 1 | `agents` |
| 28 | `AzureOpenAIResponsesClient` | 1 | `clients.azure` (推測) |

### 6.3 每個 BC 影響統計

| Breaking Change | 直接受影響使用點 | 需人工驗證 | 風險等級 |
|----------------|----------------|-----------|---------|
| BC-01: AgentRunResponse 移除 | 0 | 0 | NONE |
| BC-02: create_agent → create_run | 0 | 0 | NONE |
| BC-03: display_name → name | 0 | 需驗證 builders | LOW |
| BC-04: context_providers → context_provider | 0 | 1 (memory/base.py) | LOW |
| BC-05: source_executor_id → source | 0 | 1 (core/edge.py) | LOW |
| BC-06: Exception 類別重命名 | 0 | 0 | NONE |
| **BC-07: 命名空間遷移** | **23** | **4 (ACL 動態引用)** | **CRITICAL** |
| BC-08: AFBaseSettings 移除 | 0 | 0 | NONE |
| BC-09: AggregateContextProvider 移除 | 0 | 0 | NONE |
| BC-10: FunctionTool 泛型移除 | 0 | 0 | NONE |
| BC-11: 事件 isinstance 變更 | 0 | 0 | NONE |
| BC-12: Entra auth token 變更 | 0 | 0 | NONE |
| BC-13: InMemoryHistoryProvider 移除 | 0 | 0 | NONE |
| BC-14: WorkflowOutputEvent 移除 | 0 | 0 | NONE |

### 6.4 檔案影響分佈

| 目錄 | 受影響檔案數 | import 語句數 |
|------|------------|-------------|
| `integrations/agent_framework/builders/` | 8 | 10 |
| `integrations/agent_framework/core/` | 6 | 8 |
| `integrations/agent_framework/multiturn/` | 2 | 2 |
| `integrations/agent_framework/memory/` | 1 | 2 |
| `integrations/agent_framework/` (根) | 2 | 2 |
| `integrations/agent_framework/acl/` | 2 | 4 (動態) |
| `infrastructure/storage/` | 1 | 1 |

### 6.5 關鍵發現

1. **BC-07 是唯一的 CRITICAL 影響**: 所有 23 條 import 都從頂層命名空間引入，全部需要遷移到子模組路徑。

2. **IPA ACL 層提供緩衝**: `acl/version_detector.py` 和 `acl/adapter.py` 提供動態版本偵測和類別載入，可作為遷移的緩衝機制。

3. **測試零直接依賴**: 所有測試透過 IPA 適配器層，不直接引用 MAF，降低了升級對測試的影響。

4. **AG-UI 零直接依賴**: AG-UI 整合透過 IPA 適配器層間接使用 MAF。

5. **影響集中**: 所有需修改的程式碼集中在 `integrations/agent_framework/` 目錄內（17/18 檔案），僅 1 個檔案在 `infrastructure/storage/` 中。

6. **遷移策略建議**: 由於影響集中且有 ACL 層，可以：
   - 先更新 ACL 層以支援新命名空間
   - 逐模組更新 import 路徑
   - 利用版本偵測器做雙版本兼容
