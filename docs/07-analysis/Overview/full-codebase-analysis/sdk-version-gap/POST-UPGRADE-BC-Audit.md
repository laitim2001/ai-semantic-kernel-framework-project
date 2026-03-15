# 升級後 Breaking Changes 審計報告

**審計日期**: 2026-03-16
**審計範圍**: `C:\Users\Chris\Downloads\maf-upgrade\backend\src\`
**對照文件**: CHANGE-006-maf-rc4-upgrade-claude-sdk-sync.md（第三部分：18 個 BC）
**對照版本差異**: MAF-Version-Gap-Analysis.md

---

## 逐條驗證

### BC-01: `create_agent` -> `as_agent`

- **CHANGE-006 評估**: NONE — IPA 的 `create_agent` 是自定義方法，非 MAF API 呼叫
- **實際驗證**: 搜索 `create_agent` 在 `agent_executor.py` 找到多處引用（行 262 等），但均為 IPA 自定義方法名稱，並非呼叫 MAF 的 `client.create_agent()`。未發現 `client.create_agent()` 或 `client.as_agent()` 的直接呼叫。
- **結論**: **PASS** — CHANGE-006 評估正確，IPA 不受此 BC 影響。

---

### BC-02: `AgentRunResponse` -> `AgentResponse`

- **CHANGE-006 評估**: NONE — IPA 的 `AgentRunResponse` 是自定義 Pydantic model，與 MAF 同名但不同源
- **實際驗證**: 搜索 `AgentRunResponse`、`AgentResponse`、`AgentResponseUpdate`、`AgentRunResponseUpdate` 在 `integrations/agent_framework/` 中均**無結果**。IPA 的同名類別在 `domain/agents/schemas.py`，與 MAF 無關。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-03: `display_name` 移除 + `context_providers` 單數化 + `middleware` 列表化

- **CHANGE-006 評估**: LOW — 搜索未發現直接使用
- **實際驗證**:
  - `display_name`: 在 `integrations/agent_framework/` 中搜索**無結果**
  - `context_providers`（複數）: 搜索**無結果**
  - `context_provider`（單數，非 `context_providers`）: 搜索**無結果**
- **結論**: **PASS** — CHANGE-006 評估正確。IPA builder adapter 未直接傳遞這些參數給 MAF API。

---

### BC-04: `context_providers` -> `context_provider`（單數）

- **CHANGE-006 評估**: NONE — 搜索未發現 `context_providers` 直接使用
- **實際驗證**: 確認無結果。`memory/base.py:25` 使用的是 `from agent_framework import BaseContextProvider as ContextProvider`，這是 import 類別名稱，非建構參數。
- **結論**: **PASS** — 但需注意 `memory/base.py:25` 的 import 仍使用舊頂層路徑（見 BC-07）。

---

### BC-05: `source_executor_id` -> `source`

- **CHANGE-006 評估**: NONE — IPA 使用自定義屬性名
- **實際驗證**: 搜索 `source_executor_id` 只在 `builders/edge_routing.py` 的**註解**中出現（行 46「源執行器 ID」），但實際屬性名為 `source_id`，是 IPA 自定義的 dataclass 欄位。無直接使用 MAF 的 `source_executor_id`。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-06: Exception 類別重命名

- **CHANGE-006 評估**: NONE — 搜索未發現任何舊例外類別引用
- **實際驗證**: 搜索 `ServiceException`、`ServiceInitializationError`、`ServiceResponseException`、`AgentExecutionException`、`AgentInvocationError`、`AgentInitializationError` 在整個 `integrations/agent_framework/` 中均**無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

> **注意**: Version-Gap-Analysis.md 將此 BC 的 IPA 影響評為 HIGH，但 CHANGE-006 的更精確搜索顯示為 NONE。CHANGE-006 的評估更準確。

---

### BC-07: 命名空間遷移（頂層 -> 子模組）【CRITICAL】

- **CHANGE-006 評估**: CRITICAL — 所有 23 條活躍 import 語句都需遷移
- **實際驗證**:

#### 已完成遷移的 import（6 條 — Builder 層）:

| 檔案 | 行號 | 目前 import | 狀態 |
|------|------|-----------|------|
| `builders/concurrent.py` | 83 | `from agent_framework.orchestrations import ConcurrentBuilder` | 已遷移 |
| `builders/groupchat.py` | 83 | `from agent_framework.orchestrations import (...)` | 已遷移 |
| `builders/handoff.py` | 54 | `from agent_framework.orchestrations import HandoffBuilder, HandoffAgentUserRequest` | 已遷移 |
| `builders/magentic.py` | 39 | `from agent_framework.orchestrations import (...)` | 已遷移 |
| `builders/planning.py` | 31 | `from agent_framework.orchestrations import MagenticBuilder` | 已遷移 |
| `core/execution.py` | 35 | `from agent_framework.orchestrations import SequentialBuilder` | 已遷移 |

#### 仍使用舊頂層 import 的（15 條 — 未遷移）:

| # | 檔案 | 行號 | 舊 import（仍存在） | 應改為 |
|---|------|------|-------------------|--------|
| 1 | `builders/agent_executor.py` | 155 | `from agent_framework import Agent as ChatAgent, Message as ChatMessage, Role` | `from agent_framework.agents import Agent as ChatAgent, Message as ChatMessage, Role` |
| 2 | `builders/nested_workflow.py` | 71 | `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor` | `from agent_framework.workflows import WorkflowBuilder, Workflow, WorkflowExecutor` |
| 3 | `builders/planning.py` | 32 | `from agent_framework import Workflow` | `from agent_framework.workflows import Workflow` |
| 4 | `builders/workflow_executor.py` | 52 | `from agent_framework import (...)` | `from agent_framework.workflows import (...)` |
| 5 | `checkpoint.py` | 102 | `from agent_framework import WorkflowCheckpoint` | `from agent_framework.workflows import WorkflowCheckpoint` |
| 6 | `core/approval.py` | 39 | `from agent_framework import Executor, handler, WorkflowContext` | `from agent_framework.workflows import Executor, handler, WorkflowContext` |
| 7 | `core/approval_workflow.py` | 36 | `from agent_framework import Workflow, Edge` | `from agent_framework.workflows import Workflow, Edge` |
| 8 | `core/edge.py` | 29 | `from agent_framework import Edge` | `from agent_framework.workflows import Edge` |
| 9 | `core/events.py` | 34 | `from agent_framework import WorkflowEvent as WorkflowStatusEvent` | `from agent_framework.workflows import WorkflowEvent as WorkflowStatusEvent` |
| 10 | `core/execution.py` | 34 | `from agent_framework import Agent as ChatAgent, Workflow` | `from agent_framework.agents import Agent as ChatAgent` + `from agent_framework.workflows import Workflow` |
| 11 | `core/executor.py` | 38 | `from agent_framework import Executor, WorkflowContext, handler` | `from agent_framework.workflows import Executor, WorkflowContext, handler` |
| 12 | `core/workflow.py` | 37 | `from agent_framework import Workflow, WorkflowBuilder, Edge, Executor` | `from agent_framework.workflows import Workflow, WorkflowBuilder, Edge, Executor` |
| 13 | `memory/base.py` | 25 | `from agent_framework import BaseContextProvider as ContextProvider` | `from agent_framework.agents import BaseContextProvider as ContextProvider` |
| 14 | `memory/base.py` | 169 | `from agent_framework import MemoryStorage` | `from agent_framework.agents import MemoryStorage` |
| 15 | `multiturn/adapter.py` | 27 | `from agent_framework import (...)` | `from agent_framework.workflows import (...)` |

#### 部分遷移的（2 條 — 混合狀態）:

| 檔案 | 狀態 |
|------|------|
| `multiturn/checkpoint_storage.py:31` | `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage` — **未遷移** |
| `workflow.py:425` | `from agent_framework import WorkflowBuilder`（lazy import）— **未遷移** |

#### ACL 動態引用（4 處 — 未更新）:

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `acl/adapter.py` | 141 | `getattr(agent_framework, maf_class_name, None)` | **未更新** — rc4 後頂層不再 export，此行會返回 None |
| `acl/version_detector.py` | 87 | `getattr(agent_framework, "__version__", "0.0.0")` | **可能 OK** — `__version__` 通常保留在頂層 |
| `acl/version_detector.py` | 136 | `hasattr(agent_framework, api_name)` | **未更新** — 同上問題 |
| `acl/version_detector.py` | 167 | `hasattr(agent_framework, api_name)` | **未更新** — 同上問題 |

#### Infrastructure 層（1 條 — 部分遷移）:

| 檔案 | 行號 | 程式碼 | 狀態 |
|------|------|--------|------|
| `infrastructure/storage/storage_factories.py` | 308 | `from agent_framework.workflows import InMemoryCheckpointStorage as AFInMemoryCheckpointStorage  # TODO: verify submodule path` | **已嘗試遷移** — 但帶有 `TODO: verify submodule path` 注解，表示對路徑不確定 |

#### 關鍵發現 — Import 路徑不一致:

**CHANGE-006 規劃的路徑**: `agent_framework.workflows.orchestrations`
**實際程式碼使用的路徑**: `agent_framework.orchestrations`

已遷移的 6 條 Builder import 使用的是 `from agent_framework.orchestrations import ...`，而 CHANGE-006 文件指定的是 `from agent_framework.workflows.orchestrations import ...`。這兩者**不同**。

需要驗證 rc4 中哪個路徑才是正確的：
- `agent_framework.orchestrations`（worktree 目前使用）
- `agent_framework.workflows.orchestrations`（CHANGE-006 規劃使用）

若 rc4 實際支援的是 `agent_framework.orchestrations`，則已遷移部分正確；若只支援 `agent_framework.workflows.orchestrations`，則 6 條已遷移的 import 也需要再次修正。

#### 額外發現 — 類別名稱別名:

程式碼中使用了 MAF 的新類別名稱（或舊名稱的別名），與 CHANGE-006 文件的預期不同：

| 程式碼使用 | CHANGE-006 預期 | 說明 |
|-----------|---------------|------|
| `Agent as ChatAgent` | `ChatAgent` | MAF 可能已將 `ChatAgent` 改名為 `Agent` |
| `Message as ChatMessage` | `ChatMessage` | MAF 可能已將 `ChatMessage` 改名為 `Message` |
| `WorkflowEvent as WorkflowStatusEvent` | `WorkflowStatusEvent` | MAF 可能已將事件類別改名 |
| `BaseContextProvider as ContextProvider` | `ContextProvider` | MAF 可能已改名 |

這表示升級過程中已經識別到 rc4 的新類別名稱並使用了別名映射，但這些映射**只在部分檔案**完成。

- **結論**: **FAIL** — 23 條 import 中僅 6 條已遷移至子模組路徑（且路徑可能不正確），15 條仍使用舊頂層 import，2 條 checkpoint 相關未遷移，4 條 ACL 動態引用未更新，1 條 infrastructure 帶 TODO 標記。遷移完成度約 **26%**（6/23）。

---

### BC-08: `AFBaseSettings` 移除

- **CHANGE-006 評估**: NONE — IPA 不使用 MAF 設定系統
- **實際驗證**: 搜索 `AFBaseSettings` 在 `integrations/agent_framework/` 中**無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-09: `AggregateContextProvider` 移除

- **CHANGE-006 評估**: NONE — 搜索未發現使用
- **實際驗證**: 搜索 `AggregateContextProvider` **無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-10: `FunctionTool` 泛型移除

- **CHANGE-006 評估**: NONE — 搜索未發現 `FunctionTool[` 使用
- **實際驗證**: 搜索 `FunctionTool[` **無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-11: Provider 狀態依 `source_id` 範圍化

- **CHANGE-006 評估**: MEDIUM — `checkpoint.py` 和 `multiturn/` 使用 `InMemoryCheckpointStorage`
- **實際驗證**:
  - `multiturn/checkpoint_storage.py:31` — `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage`（仍用舊 import）
  - `multiturn/adapter.py:27` — `from agent_framework import (...)`（仍用舊 import，包含 checkpoint 相關類別）
  - `builders/edge_routing.py` 使用 `source_id` 但是 IPA 自定義欄位，非 MAF 的 provider source_id
  - 未發現任何 `source_id` 預設值從 `"memory"` 到 `"in_memory"` 的更新
- **結論**: **需注意** — CHANGE-006 評估等級正確（MEDIUM），但程式碼中未見任何針對 `source_id` 行為變更的處理。需在 import 遷移完成後進行功能測試驗證。

---

### BC-12: Entra auth token 變更

- **CHANGE-006 評估**: NONE — 搜索未發現 `ad_token_provider` 使用
- **實際驗證**: 搜索 `ad_token_provider`、`ad_token`、`get_entra_auth_token` **無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-13: `InMemoryHistoryProvider` 移除

- **CHANGE-006 評估**: NONE — 搜索未發現使用
- **實際驗證**: 搜索 `InMemoryHistoryProvider` **無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-14: `WorkflowOutputEvent` 移除

- **CHANGE-006 評估**: NONE — 搜索未發現使用
- **實際驗證**: 搜索 `WorkflowOutputEvent` **無結果**。搜索 `isinstance.*Event` 也**無結果**。
- **額外發現**: `core/events.py:34` 使用 `from agent_framework import WorkflowEvent as WorkflowStatusEvent`，這是 `WorkflowEvent` 類別（非 `WorkflowOutputEvent`）。但此 import 仍使用舊頂層路徑。
- **結論**: **PASS** — 但需注意 Version-Gap-Analysis.md 將此評為 HIGH 影響（建議使用 `event.type` 代替 `isinstance()`）。CHANGE-006 的 NONE 評估更準確，因為 IPA 確實未使用 `WorkflowOutputEvent`。

> **注意**: Version-Gap-Analysis.md (BC-14) 描述的是「工作流程事件重構為通用 `WorkflowEvent[DataT]`」，影響 `isinstance()` 檢查。但 CHANGE-006 (BC-14) 描述的是「`WorkflowOutputEvent` 移除」。兩份文件對 BC-14 的定義不同，需要釐清。

---

### BC-15: Checkpoint 模型和存儲行為重構

- **CHANGE-006 評估**: MEDIUM — `checkpoint.py` 和 `multiturn/adapter.py` 使用 `WorkflowCheckpoint`
- **實際驗證**:
  - `checkpoint.py:102` — `from agent_framework import WorkflowCheckpoint`（lazy import，**仍用舊頂層路徑**）
  - `checkpoint.py` 定義了 `save_checkpoint(checkpoint: WorkflowCheckpoint)` 等方法的 Protocol
  - `multiturn/adapter.py:27` — 使用舊 import 引入 checkpoint 相關類別
  - `multiturn/checkpoint_storage.py:31` — `from agent_framework import CheckpointStorage, InMemoryCheckpointStorage`（**仍用舊頂層路徑**）
  - 未發現針對 Checkpoint API 變更（如新欄位、新方法簽名）的任何修改
- **結論**: **需注意** — CHANGE-006 評估等級正確（MEDIUM），但除了 import 路徑問題外（BC-07），尚未執行任何 Checkpoint API 適配工作。需在 rc4 環境下實際測試 Checkpoint 功能。

---

### BC-16: 標準化編排輸出為 `list[ChatMessage]`

- **CHANGE-006 評估**: LOW-MEDIUM — 需驗證 GroupChat 輸出處理
- **實際驗證**: 搜索 `ChatMessage` 在 `integrations/agent_framework/` 中發現多處使用，主要在 `builders/agent_executor.py`（`from agent_framework import ... Message as ChatMessage`）。GroupChat builder 中的輸出處理是通過 adapter 抽象層處理的。
- **結論**: **需注意** — 未發現針對輸出格式變更的明確處理。需功能測試驗證 GroupChat 輸出是否為 `list[ChatMessage]` 格式。

---

### BC-17: Azure Functions 套件的 Schema 變更

- **CHANGE-006 評估**: NONE — IPA 不使用 Azure Functions
- **實際驗證**: 搜索 `azure.functions`、`azure_functions` **無結果**。
- **結論**: **PASS** — CHANGE-006 評估正確。

---

### BC-18: HITL 工具呼叫審批行為變更

- **CHANGE-006 評估**: LOW — 新增功能，非必要遷移。Phase B 可選採用。
- **實際驗證**: 搜索 `tool_call_approval`、`tool_approval`、`plan_pause` 在 `integrations/agent_framework/` 中發現 `builders/magentic.py` 有多處 `tool_call` 相關引用，但均為 IPA 自建的工具呼叫處理邏輯，非 MAF 的 HITL 審批 API。
- **結論**: **PASS** — CHANGE-006 評估正確。這是可選的新功能增強，非破壞性變更。

---

## CHANGE-006 未記錄的發現

### 發現 1: Import 路徑不一致（CRITICAL）

CHANGE-006 第四部分指定所有 orchestration builder 應遷移至 `agent_framework.workflows.orchestrations`，但 worktree 中已遷移的 6 條 import 實際使用的是 `agent_framework.orchestrations`（少了 `.workflows` 中間層）。

**受影響檔案**:
- `builders/concurrent.py:83`
- `builders/groupchat.py:83`
- `builders/handoff.py:54`
- `builders/magentic.py:39`
- `builders/planning.py:31`
- `core/execution.py:35`

**風險**: 如果 rc4 不支援 `agent_framework.orchestrations` 路徑，這 6 條已遷移的 import 也會失敗。必須在 rc4 環境中驗證正確的 import 路徑。

### 發現 2: MAF 類別名稱已變更（HIGH）

worktree 中發現 MAF 的某些類別已在 rc4 中改名，目前使用別名映射：

| 舊名稱（CHANGE-006 使用） | 新名稱（worktree 實際 import） |
|--------------------------|------------------------------|
| `ChatAgent` | `Agent`（別名 `as ChatAgent`） |
| `ChatMessage` | `Message`（別名 `as ChatMessage`） |
| `WorkflowStatusEvent` | `WorkflowEvent`（別名 `as WorkflowStatusEvent`） |
| `ContextProvider` | `BaseContextProvider`（別名 `as ContextProvider`） |

CHANGE-006 的遷移映射表（第 188-217 行）仍使用舊類別名稱，需要更新。

### 發現 3: `storage_factories.py` 帶 TODO 標記

`infrastructure/storage/storage_factories.py:308` 已嘗試遷移至 `from agent_framework.workflows import InMemoryCheckpointStorage`，但附帶 `# TODO: verify submodule path` 注解，表示執行者對路徑正確性不確定。

### 發現 4: `requirements.txt` 已更新

`requirements.txt` 行 20 已更新為 `agent-framework>=1.0.0rc4,<2.0.0`，此項已完成。

### 發現 5: `handoff.py` 路徑差異

`builders/handoff.py:54` 使用 `from agent_framework.orchestrations import HandoffBuilder, HandoffAgentUserRequest`，但 CHANGE-006 規劃的是將 `HandoffAgentUserRequest` 從 `agent_framework.workflows` import（而非 `orchestrations`）。需驗證 `HandoffAgentUserRequest` 在 rc4 中的實際模組歸屬。

---

## 統計

### 總覽

| 分類 | 數量 |
|------|------|
| **PASS** | **12** |
| **FAIL** | **1**（BC-07） |
| **需注意** | **3**（BC-11, BC-15, BC-16） |
| **CHANGE-006 未記錄問題** | **5** |

### BC-07 遷移進度

| 狀態 | 數量 | 百分比 |
|------|------|--------|
| 已遷移至子模組 | 6 | 26% |
| 仍用舊頂層 import | 15 | 65% |
| ACL 動態引用未更新 | 4 | — |
| Infrastructure 帶 TODO | 1 | — |
| **需要完成的工作** | **20 條 import + 4 條動態引用** | — |

### CHANGE-006 影響評估準確性

| BC 項目 | CHANGE-006 評估 | Version-Gap 評估 | 實際驗證結果 | 準確性 |
|---------|---------------|----------------|------------|--------|
| BC-01 | NONE | LOW | NONE | CHANGE-006 更準確 |
| BC-02 | NONE | MEDIUM | NONE | CHANGE-006 更準確 |
| BC-03 | LOW | HIGH | NONE/LOW | CHANGE-006 更準確 |
| BC-04 | NONE | — | NONE | 正確 |
| BC-05 | NONE | — | NONE | 正確 |
| BC-06 | NONE | HIGH | NONE | CHANGE-006 更準確 |
| BC-07 | CRITICAL | CRITICAL | CRITICAL | 兩者一致，但遷移未完成 |
| BC-08 | NONE | LOW-MEDIUM | NONE | CHANGE-006 更準確 |
| BC-09 | NONE | — | NONE | 正確 |
| BC-10 | NONE | LOW | NONE | 正確 |
| BC-11 | MEDIUM | MEDIUM | MEDIUM | 一致，待測試 |
| BC-12 | NONE | MEDIUM | NONE | CHANGE-006 更準確 |
| BC-13 | NONE | — | NONE | 正確 |
| BC-14 | NONE | HIGH | NONE | CHANGE-006 更準確 |
| BC-15 | MEDIUM | MEDIUM | MEDIUM | 一致，待測試 |
| BC-16 | LOW-MEDIUM | MEDIUM | LOW-MEDIUM | 一致，待測試 |
| BC-17 | NONE | LOW | NONE | CHANGE-006 更準確 |
| BC-18 | LOW | HIGH | LOW | CHANGE-006 更準確 |

**結論**: CHANGE-006 的影響評估整體比 Version-Gap-Analysis.md 更精確（基於實際 IPA 程式碼搜索），18 項中有 10 項評估更準確或一致。

---

## 風險評估

### CRITICAL 風險

1. **BC-07 遷移僅完成 26%**: 15 條活躍 import 仍使用舊頂層路徑。若安裝 rc4 並執行，這些檔案將 import 失敗，導致整個 `integrations/agent_framework/` 模組無法載入。

2. **Import 路徑不一致**: 已遷移的 6 條 import 使用 `agent_framework.orchestrations`，但 CHANGE-006 規劃使用 `agent_framework.workflows.orchestrations`。需在 rc4 環境中驗證哪個路徑正確。若 `agent_framework.orchestrations` 不存在，則已遷移的部分也會失敗。

3. **MAF 類別名稱已變更但 CHANGE-006 未記錄**: `ChatAgent` -> `Agent`、`ChatMessage` -> `Message` 等改名，表示 rc4 的 API surface 與 CHANGE-006 預期不同。遷移映射表需要更新。

### HIGH 風險

4. **ACL 動態引用未更新**: `acl/adapter.py:141` 的 `getattr(agent_framework, maf_class_name)` 在 rc4 中會因頂層不再 export 類別而返回 `None`，導致 ACL 版本偵測和動態載入完全失效。

### MEDIUM 風險

5. **Checkpoint/Provider 行為變更未驗證**: BC-11 和 BC-15 的行為變更需要功能測試驗證，目前無法僅從程式碼靜態分析判斷是否相容。

### 建議優先處理順序

1. **驗證 rc4 的正確 import 路徑**（`orchestrations` vs `workflows.orchestrations`）
2. **完成剩餘 15 條頂層 import 遷移**
3. **更新 ACL 動態引用邏輯**（adapter.py + version_detector.py）
4. **更新 CHANGE-006 的類別名稱映射表**（反映 rc4 實際改名）
5. **在 rc4 環境中進行 Checkpoint 功能測試**
6. **移除 `storage_factories.py:308` 的 TODO 注解**（確認路徑後）

---

**審計結論**: 升級工作已啟動但遠未完成。`requirements.txt` 已更新至 rc4，Builder 層的 orchestration import 已部分遷移（6/23），但 Core、Multiturn、Memory、Checkpoint、ACL、Infrastructure 層的 import 均未遷移。若此時實際安裝 rc4 執行，預計 **15+ 個模組將 import 失敗**。建議在合併前完成所有 BC-07 遷移並在 rc4 環境中執行完整測試套件。
