# MAF RC4 升級掃描與修復計劃

> **文件版本**: 1.0
> **建立日期**: 2026-03-18
> **目的**: 針對 V8.1 升級遺漏的 8 項破壞性變更，提供可在 Claude Code 中直接執行的掃描命令與修復指引
> **前置文件**: `MAF-Version-Gap-Analysis.md`、`MAF-Features-Architecture-Mapping-V8.md`
> **掃描範圍**: `backend/src/integrations/agent_framework/`、`backend/src/integrations/hybrid/`、`backend/src/integrations/orchestration/`、`backend/src/integrations/ag_ui/`、`backend/src/domain/sessions/`、`backend/src/core/`

---

## 執行摘要

V8.1 升級記錄確認處理了 4 項變更（命名空間遷移 BC-07、constructor kwargs、4 組類別別名、Claude SDK 更新），但 gap 分析中的 18 項破壞性變更仍有 **8 項未在 V8.1 中被提及或確認處理**。本計劃按優先順序為每項提供：掃描命令、預期命中、修復模式、驗證方法。

**執行順序建議**：SCAN-1 到 SCAN-8 按風險從高到低排列。建議先全部掃描一遍確認實際影響範圍，再按結果決定修復順序。

---

## Phase 0: 環境準備

```bash
# 確認目前代碼庫的 MAF 版本鎖定
grep -rn "agent.framework" requirements*.txt pyproject.toml setup.cfg 2>/dev/null

# 確認 V8.1 升級後的實際安裝版本
pip show agent-framework-core 2>/dev/null || pip show agent-framework 2>/dev/null

# 建立掃描結果目錄
mkdir -p scan-results/
```

---

## SCAN-1: Workflow 事件 isinstance 檢查 (BC-14)

**風險等級**: CRITICAL — 靜默失敗，不會報錯但事件被跳過
**GAP 分析編號**: BC-14
**V8.1 狀態**: 僅建立了 `WorkflowStatusEvent` 別名，未遷移 isinstance 用法

### 為什麼危險

RC4 將所有事件子類別（`WorkflowOutputEvent`、`WorkflowRequestEvent` 等）替換為泛型 `WorkflowEvent[DataT]`。舊的 `isinstance()` 檢查不會拋出錯誤，只是永遠返回 `False`，導致事件處理邏輯被靜默跳過。在 happy path 測試中完全正常 — 只有當需要處理特定事件時才會發現問題。

### 掃描命令

```bash
echo "=== SCAN-1: Workflow event isinstance checks ===" | tee scan-results/scan-1.txt

# 1a. 搜尋所有 isinstance + Event 的組合
grep -rn "isinstance.*Event" \
  backend/src/integrations/agent_framework/ \
  backend/src/integrations/hybrid/ \
  backend/src/integrations/orchestration/ \
  backend/src/core/ \
  2>/dev/null | tee -a scan-results/scan-1.txt

# 1b. 搜尋舊的事件類別引入
grep -rn "from agent_framework.*import.*\(WorkflowOutputEvent\|WorkflowRequestEvent\|WorkflowStatusEvent\|SuperStepCompletedEvent\|WorkflowStartedEvent\|WorkflowFailedEvent\)" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-1.txt

# 1c. 搜尋 source_executor_id (BC-04 同時檢查)
grep -rn "source_executor_id" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-1.txt

echo "=== SCAN-1 END ===" | tee -a scan-results/scan-1.txt
```

### 預期命中檔案

| 檔案 | 預期問題 |
|------|----------|
| `builders/workflow_executor.py` | isinstance 檢查 workflow output/request events |
| `builders/nested_workflow.py` | isinstance 檢查巢狀 workflow 事件 |
| `core/events.py` | 事件類型定義和分發 |
| `core/approval_workflow.py` | isinstance 檢查 approval 相關事件 |

### 修復模式

```python
# BEFORE (b260114)
from agent_framework import WorkflowOutputEvent, WorkflowRequestEvent

async for event in workflow.run(input, stream=True):
    if isinstance(event, WorkflowOutputEvent):
        messages = event.data
    elif isinstance(event, WorkflowRequestEvent):
        handle_request(event)

# AFTER (RC4)
from typing import Any, cast
from agent_framework import WorkflowEvent, Message

async for event in workflow.run(input, stream=True):
    if event.type == "output":
        messages = cast(list[Message], event.data)
    elif event.type == "request":
        handle_request(event)
```

**RC4 保留事件類型字串**: `"started"`、`"status"`、`"failed"`、`"output"`、`"request"`、`"super_step_completed"`

### 驗證方法

```bash
# 確認沒有殘留的 isinstance Event 檢查
grep -rn "isinstance.*Event" backend/src/integrations/agent_framework/ backend/src/core/ | grep -v "test" | grep -v "#"
# 期望: 0 結果

# 確認新的 event.type 用法存在
grep -rn "event\.type ==" backend/src/integrations/agent_framework/ backend/src/core/
# 期望: 至少有對應的 type 字串檢查
```

---

## SCAN-2: 異常處理類別 (BC-09)

**風險等級**: CRITICAL — 錯誤路徑靜默失敗，happy path 正常
**GAP 分析編號**: BC-09
**V8.1 狀態**: 完全未提及

### 為什麼危險

`ServiceException` 系列在 RC4 中被完全移除並替換為 `AgentFrameworkException` 體系。舊的 `except ServiceException` 不會報編譯錯誤（因為 import 會失敗，但如果有 try/except 包裹 import 則更隱蔽），只是在真正發生錯誤時不再捕獲任何東西。

### 掃描命令

```bash
echo "=== SCAN-2: Exception class references ===" | tee scan-results/scan-2.txt

# 2a. 搜尋所有舊異常類別
grep -rn "\(ServiceException\|ServiceInitializationError\|ServiceResponseException\|ServiceContentFilterException\|ServiceInvalidAuthError\|ServiceInvalidExecutionSettingsError\|ServiceInvalidRequestError\|AgentExecutionException\|AgentInvocationError\|AgentInitializationError\)" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-2.txt

# 2b. 搜尋 except 語句中的異常捕獲
grep -rn "except.*\(Service\|AgentExecution\|AgentInvocation\|AgentInitialization\)" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-2.txt

# 2c. 搜尋從 agent_framework 引入的異常
grep -rn "from agent_framework.*import.*\(Exception\|Error\)" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-2.txt

echo "=== SCAN-2 END ===" | tee -a scan-results/scan-2.txt
```

### 預期命中檔案

| 檔案 | 預期問題 |
|------|----------|
| `core/approval.py` | except ServiceException 或 AgentExecutionException |
| `builders/agent_executor.py` | 錯誤處理邏輯 |
| `hybrid/switching/mode_switcher.py` | 框架切換時的異常捕獲 |
| `hybrid/execution/` | 執行層異常處理 |
| `orchestration/` | 編排層異常處理 |

### 修復模式

```python
# BEFORE (b260114)
from agent_framework import ServiceException, ServiceResponseException

try:
    result = await agent.run(input)
except ServiceResponseException as e:
    handle_response_error(e)
except ServiceException as e:
    handle_general_error(e)

# AFTER (RC4) — 新的異常體系
from agent_framework import (
    AgentFrameworkException,
    AgentException,
    AgentInvalidResponseException,
    AgentContentFilterException,
    WorkflowException,
    ToolExecutionException,
)

try:
    result = await agent.run(input)
except AgentInvalidResponseException as e:
    handle_response_error(e)
except AgentContentFilterException as e:
    handle_content_filter(e)
except AgentException as e:
    handle_general_agent_error(e)
except AgentFrameworkException as e:
    handle_framework_error(e)
```

**RC4 完整異常樹**:
```
AgentFrameworkException
├── AgentException
│   ├── AgentInvalidAuthException
│   ├── AgentInvalidRequestException
│   ├── AgentInvalidResponseException
│   └── AgentContentFilterException
├── ChatClientException (同上子結構)
├── IntegrationException (同上子結構)
├── ContentError
├── WorkflowException
│   ├── WorkflowRunnerException
│   ├── WorkflowValidationError
│   └── WorkflowActionError
├── ToolExecutionException
├── MiddlewareTermination
└── SettingNotFoundError
```

### 驗證方法

```bash
# 確認沒有殘留的舊異常類別
grep -rn "ServiceException\|ServiceInitializationError\|ServiceResponseException" backend/src/ | grep -v "test" | grep -v "#" | grep -v ".pyc"
# 期望: 0 結果
```

---

## SCAN-3: Checkpoint 存儲介面 (BC-15)

**風險等級**: HIGH — 可能導致 checkpoint 讀寫失敗
**GAP 分析編號**: BC-15
**V8.1 狀態**: 記錄了 constructor 遷移但未提及存儲介面變更

### 為什麼危險

V8.1 處理了 `with_checkpointing()` → constructor kwarg 的遷移，但 checkpoint 的 encode/decode 格式、`CheckpointStorage` 介面、以及 checkpoint 在 superstep 中的建立時機都有變更。你的 `hybrid/checkpoint/` 有 4 個自定義 backend（Memory、Redis、PostgreSQL、Filesystem），如果介面不匹配，checkpoint 的儲存和恢復會失敗。

### 掃描命令

```bash
echo "=== SCAN-3: Checkpoint interface ===" | tee scan-results/scan-3.txt

# 3a. 搜尋 with_checkpointing 殘留
grep -rn "with_checkpointing" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-3.txt

# 3b. 搜尋 checkpoint 相關的 import 和類別
grep -rn "from agent_framework.*import.*\(Checkpoint\|CheckpointStorage\|CheckpointInfo\|SuperStepCompleted\)" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-3.txt

# 3c. 搜尋自定義 checkpoint storage 實現
grep -rn "class.*Checkpoint.*Storage\|class.*CheckpointBackend\|def save\|def load\|def delete" \
  backend/src/integrations/hybrid/checkpoint/ \
  backend/src/integrations/agent_framework/checkpoint* \
  backend/src/domain/checkpoints/ \
  backend/src/infrastructure/checkpoint/ \
  2>/dev/null | tee -a scan-results/scan-3.txt

# 3d. 搜尋 set_start_executor 和 with_output_from (同時被移除)
grep -rn "set_start_executor\|with_output_from" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-3.txt

# 3e. 搜尋 checkpoint encode/decode 或 serialize/deserialize
grep -rn "encode\|decode\|serialize\|deserialize" \
  backend/src/integrations/hybrid/checkpoint/ \
  backend/src/infrastructure/checkpoint/ \
  2>/dev/null | tee -a scan-results/scan-3.txt

echo "=== SCAN-3 END ===" | tee -a scan-results/scan-3.txt
```

### 預期命中檔案

| 檔案 | 預期問題 |
|------|----------|
| `hybrid/checkpoint/` (4 backends) | 自定義 storage 介面可能與新 CheckpointStorage 不匹配 |
| `integrations/agent_framework/checkpoint.py` | MAF 官方 checkpoint 包裝 |
| `domain/checkpoints/` | domain 層 checkpoint 邏輯 |
| `infrastructure/checkpoint/` | 基礎設施層 checkpoint backend |
| builders 中殘留的 fluent method | `set_start_executor()`, `with_output_from()` |

### 修復模式

```python
# BEFORE (b260114) — fluent method
workflow = (
    WorkflowBuilder()
    .set_start_executor(start)
    .with_checkpointing(my_storage)
    .with_output_from(end)
    .add_edge(start, end)
    .build()
)

# AFTER (RC4) — constructor kwargs
workflow = (
    WorkflowBuilder(
        start_executor=start,
        checkpoint_storage=my_storage,
        output_executor=end,    # 注意：需確認 RC4 實際參數名
    )
    .add_edge(start, end)
    .build()
)

# Checkpoint 存取方式也改變了
# BEFORE: 通過 workflow API
# AFTER: 通過 SuperStepCompletedEvent 的 CheckpointInfo
async for event in workflow.run(input, stream=True):
    if event.type == "super_step_completed":
        checkpoint = event.data  # CheckpointInfo
```

### 驗證方法

```bash
# 確認 fluent method 已全部移除
grep -rn "with_checkpointing\|set_start_executor\|with_output_from" backend/src/ | grep -v "test" | grep -v "#"
# 期望: 0 結果
```

---

## SCAN-4: Context Provider 複數→單數 (BC-03)

**風險等級**: HIGH — 可能導致 agent 初始化失敗
**GAP 分析編號**: BC-03
**V8.1 狀態**: 建立了 ContextProvider 別名，但未處理複數→單數遷移

### 掃描命令

```bash
echo "=== SCAN-4: Context provider changes ===" | tee scan-results/scan-4.txt

# 4a. 搜尋 context_providers (複數，舊用法)
grep -rn "context_providers" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-4.txt

# 4b. 搜尋 display_name (已移除的參數)
grep -rn "display_name" \
  backend/src/integrations/agent_framework/ \
  backend/src/integrations/hybrid/ \
  2>/dev/null | tee -a scan-results/scan-4.txt

# 4c. 搜尋 AggregateContextProvider (已移除)
grep -rn "AggregateContextProvider" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-4.txt

# 4d. 搜尋 AgentThread (已移除)
grep -rn "AgentThread" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-4.txt

# 4e. 搜尋 middleware 賦值方式 (必須為 list)
grep -rn "middleware\s*=" \
  backend/src/integrations/agent_framework/ \
  2>/dev/null | tee -a scan-results/scan-4.txt

echo "=== SCAN-4 END ===" | tee -a scan-results/scan-4.txt
```

### 修復模式

```python
# BEFORE (b260114)
agent = client.create_agent(
    display_name="MyAgent",           # REMOVED
    context_providers=[prov1, prov2],  # 複數 → 單數
    middleware=single_middleware,       # 必須為 list
)

# AFTER (RC4)
agent = client.as_agent(
    name="MyAgent",                    # display_name → name
    context_provider=combined_prov,    # 單數，僅 1 個
    middleware=[single_middleware],     # 必須為 list
)
# 如果需要多個 context provider，需要自行組合成一個
```

---

## SCAN-5: HITL 恢復方式 (send_responses 移除)

**風險等級**: HIGH — 直接影響審批系統的 workflow 恢復
**GAP 分析編號**: 未單獨列出（屬於 RC1 Workflow API 變更）
**V8.1 狀態**: 完全未提及

### 掃描命令

```bash
echo "=== SCAN-5: HITL resume pattern ===" | tee scan-results/scan-5.txt

# 5a. 搜尋被移除的 send_responses 方法
grep -rn "send_responses\|send_responses_streaming" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-5.txt

# 5b. 搜尋 checkpoint_id 在 workflow 恢復中的用法
grep -rn "checkpoint_id" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-5.txt

# 5c. 搜尋 approval/resume/respond 相關模式
grep -rn "resume_workflow\|respond_to\|approval_response\|workflow.*resume" \
  backend/src/integrations/ \
  backend/src/domain/ \
  2>/dev/null | tee -a scan-results/scan-5.txt

echo "=== SCAN-5 END ===" | tee -a scan-results/scan-5.txt
```

### 修復模式

```python
# BEFORE (b260114)
async for event in workflow.send_responses_streaming(
    checkpoint_id=checkpoint_id,
    responses=[approved_response],
):
    handle(event)

# AFTER (RC4) — responses 直接傳入 run()
async for event in workflow.run(
    checkpoint_id=checkpoint_id,
    responses=[approved_response],
    stream=True,
):
    handle(event)
```

---

## SCAN-6: AgentRunResponse 類型重命名 (BC-02)

**風險等級**: MEDIUM — 編譯時 ImportError 或運行時 AttributeError
**GAP 分析編號**: BC-02
**V8.1 狀態**: 未提及

### 掃描命令

```bash
echo "=== SCAN-6: Response type renames ===" | tee scan-results/scan-6.txt

# 6a. 搜尋舊的回應類型名稱
grep -rn "AgentRunResponse\|AgentRunResponseUpdate" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-6.txt

# 6b. 搜尋 create_agent (BC-01 同時檢查)
grep -rn "create_agent\b" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-6.txt

echo "=== SCAN-6 END ===" | tee -a scan-results/scan-6.txt
```

### 修復模式

```python
# BEFORE
from agent_framework import AgentRunResponse, AgentRunResponseUpdate
# AFTER
from agent_framework import AgentResponse, AgentResponseUpdate
```

---

## SCAN-7: Session/Context 類型移除

**風險等級**: MEDIUM-HIGH — 可能影響 session domain
**GAP 分析編號**: BC-11 (provider state scoping) + 新增
**V8.1 狀態**: 未提及

### 掃描命令

```bash
echo "=== SCAN-7: Session/context types ===" | tee scan-results/scan-7.txt

# 7a. 搜尋被移除的 AgentThread
grep -rn "AgentThread" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-7.txt

# 7b. 搜尋舊的 source_id state 存取模式
grep -rn "state\[self\.source_id\]" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-7.txt

# 7c. 搜尋 InMemoryHistoryProvider 的舊 source_id
grep -rn "InMemoryHistoryProvider" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-7.txt

# 7d. 搜尋 SessionContext / BaseContextProvider 用法
grep -rn "SessionContext\|BaseContextProvider\|ContextProvider" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-7.txt

echo "=== SCAN-7 END ===" | tee -a scan-results/scan-7.txt
```

---

## SCAN-8: Core 類型額外重命名

**風險等級**: MEDIUM — V8.1 別名可能在 GA 後失效
**GAP 分析編號**: BC-12 延伸
**V8.1 狀態**: 僅處理了 4 組，但 RC4 有更多

### 掃描命令

```bash
echo "=== SCAN-8: Core type renames beyond V8.1 aliases ===" | tee scan-results/scan-8.txt

# 8a. 搜尋 V8.1 已建別名但應遷移到新名的用法
grep -rn "ChatAgent\|ChatMessage\|WorkflowStatusEvent\|ContextProvider" \
  backend/src/ \
  2>/dev/null | grep -v "as ChatAgent\|as ChatMessage\|as WorkflowStatusEvent\|as ContextProvider" \
  | tee -a scan-results/scan-8.txt

# 8b. 搜尋 V8.1 未覆蓋的額外重命名
grep -rn "RawChatAgent\|ChatClientProtocol\|HostedCodeInterpreterTool\|HostedWebSearchTool" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-8.txt

# 8c. 搜尋 FunctionTool[Any] (BC-13)
grep -rn "FunctionTool\[" \
  backend/src/ \
  2>/dev/null | tee -a scan-results/scan-8.txt

echo "=== SCAN-8 END ===" | tee -a scan-results/scan-8.txt
```

---

## Phase 2: 一鍵全掃描腳本

將以上所有掃描合併為一個可直接執行的腳本：

```bash
#!/bin/bash
# MAF RC4 Upgrade Gap Scanner
# 執行: bash scan-maf-rc4-gaps.sh <project_backend_src_path>
# 例如: bash scan-maf-rc4-gaps.sh backend/src

SRC="${1:-backend/src}"
OUT="scan-results"
mkdir -p "$OUT"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$OUT/full-scan-$TIMESTAMP.txt"

echo "================================================" | tee "$REPORT"
echo "MAF RC4 Upgrade Gap Scanner" | tee -a "$REPORT"
echo "Scan path: $SRC" | tee -a "$REPORT"
echo "Timestamp: $TIMESTAMP" | tee -a "$REPORT"
echo "================================================" | tee -a "$REPORT"

# --- SCAN-1: Workflow event isinstance ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-1: Workflow event isinstance (CRITICAL) ---" | tee -a "$REPORT"
echo "[1a] isinstance + Event:" | tee -a "$REPORT"
grep -rn "isinstance.*Event" "$SRC" 2>/dev/null | grep -v "__pycache__" | grep -v ".pyc" | tee -a "$REPORT"
echo "[1b] Old event class imports:" | tee -a "$REPORT"
grep -rn "WorkflowOutputEvent\|WorkflowRequestEvent\|SuperStepCompletedEvent\|WorkflowStartedEvent\|WorkflowFailedEvent" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[1c] source_executor_id (BC-04):" | tee -a "$REPORT"
grep -rn "source_executor_id" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-2: Exception classes ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-2: Exception classes (CRITICAL) ---" | tee -a "$REPORT"
echo "[2a] Old exception classes:" | tee -a "$REPORT"
grep -rn "ServiceException\|ServiceInitializationError\|ServiceResponseException\|ServiceContentFilterException\|ServiceInvalidAuthError\|AgentExecutionException\|AgentInvocationError\|AgentInitializationError" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[2b] except statements with old classes:" | tee -a "$REPORT"
grep -rn "except.*\(Service\|AgentExecution\|AgentInvocation\|AgentInitialization\)" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-3: Checkpoint interface ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-3: Checkpoint interface (HIGH) ---" | tee -a "$REPORT"
echo "[3a] with_checkpointing residual:" | tee -a "$REPORT"
grep -rn "with_checkpointing\|set_start_executor\|with_output_from" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[3b] Checkpoint imports:" | tee -a "$REPORT"
grep -rn "from agent_framework.*import.*Checkpoint" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-4: Context provider plural/singular ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-4: Context provider changes (HIGH) ---" | tee -a "$REPORT"
echo "[4a] context_providers (plural):" | tee -a "$REPORT"
grep -rn "context_providers" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[4b] display_name:" | tee -a "$REPORT"
grep -rn "display_name" "$SRC/integrations/agent_framework/" "$SRC/integrations/hybrid/" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[4c] AggregateContextProvider:" | tee -a "$REPORT"
grep -rn "AggregateContextProvider" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[4d] AgentThread:" | tee -a "$REPORT"
grep -rn "AgentThread" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-5: HITL resume pattern ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-5: HITL resume pattern (HIGH) ---" | tee -a "$REPORT"
echo "[5a] send_responses:" | tee -a "$REPORT"
grep -rn "send_responses\|send_responses_streaming" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[5b] checkpoint_id usage:" | tee -a "$REPORT"
grep -rn "checkpoint_id" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-6: Response type renames ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-6: Response type renames (MEDIUM) ---" | tee -a "$REPORT"
echo "[6a] AgentRunResponse:" | tee -a "$REPORT"
grep -rn "AgentRunResponse\|AgentRunResponseUpdate" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[6b] create_agent:" | tee -a "$REPORT"
grep -rn "\.create_agent\b" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-7: Session/context types ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-7: Session/context types (MEDIUM-HIGH) ---" | tee -a "$REPORT"
echo "[7a] Old state access pattern:" | tee -a "$REPORT"
grep -rn 'state\[self\.source_id\]' "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[7b] InMemoryHistoryProvider:" | tee -a "$REPORT"
grep -rn "InMemoryHistoryProvider" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SCAN-8: Core type renames ---
echo "" | tee -a "$REPORT"
echo "--- SCAN-8: Core type renames beyond aliases (MEDIUM) ---" | tee -a "$REPORT"
echo "[8a] RawChatAgent / ChatClientProtocol / HostedTools:" | tee -a "$REPORT"
grep -rn "RawChatAgent\|ChatClientProtocol\|HostedCodeInterpreterTool\|HostedWebSearchTool" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"
echo "[8b] FunctionTool generic:" | tee -a "$REPORT"
grep -rn "FunctionTool\[" "$SRC" 2>/dev/null | grep -v "__pycache__" | tee -a "$REPORT"

# --- SUMMARY ---
echo "" | tee -a "$REPORT"
echo "================================================" | tee -a "$REPORT"
echo "SUMMARY" | tee -a "$REPORT"
echo "================================================" | tee -a "$REPORT"
for i in 1 2 3 4 5 6 7 8; do
  COUNT=$(grep -c "^\[${i}" "$REPORT" 2>/dev/null || echo 0)
  HITS=$(grep "^$SRC" "$REPORT" | wc -l)
  echo "SCAN-$i: see above for details" | tee -a "$REPORT"
done

TOTAL_HITS=$(grep "^$SRC" "$REPORT" | wc -l)
echo "" | tee -a "$REPORT"
echo "Total potential hits: $TOTAL_HITS" | tee -a "$REPORT"
echo "Full report: $REPORT" | tee -a "$REPORT"
```

---

## Phase 3: 修復優先順序

掃描完成後，根據命中數量決定修復順序：

| 優先級 | 修復項 | 預估工作量 | 理由 |
|--------|--------|-----------|------|
| **P0** | SCAN-1 (event isinstance) | 3-5 SP | 靜默失敗，最難發現 |
| **P0** | SCAN-2 (exception classes) | 2-3 SP | 錯誤路徑全部失效 |
| **P1** | SCAN-5 (HITL resume) | 3-5 SP | 審批系統恢復功能斷裂 |
| **P1** | SCAN-3 (checkpoint) | 3-5 SP | 依賴掃描結果 — 如果 4 個 backend 都需要改則工作量大 |
| **P2** | SCAN-4 (context provider) | 2-3 SP | 取決於 AggregateContextProvider 使用程度 |
| **P2** | SCAN-6 (response rename) | 1 SP | 機械性替換 |
| **P3** | SCAN-7 (session types) | 2-3 SP | 取決於是否直接使用了 MAF session 類型 |
| **P3** | SCAN-8 (core renames) | 1-2 SP | 向後相容別名暫時可用，GA 前需完成 |

**總估算**: 17-27 SP (2-3 Sprints)，加上 V8.1 已完成的 4 項，合計約 34 SP 與 gap 分析的估算一致。

---

## Phase 4: 驗證清單

所有修復完成後執行：

```bash
# 1. 確認零殘留
bash scan-maf-rc4-gaps.sh backend/src
# 期望: Total potential hits = 0 (或僅剩測試檔案中的 mock)

# 2. 執行 adapter 測試套件
pytest backend/tests/integrations/agent_framework/ -v

# 3. 執行 hybrid 層測試
pytest backend/tests/integrations/hybrid/ -v

# 4. 執行 orchestration 層測試
pytest backend/tests/integrations/orchestration/ -v

# 5. 執行端到端流程測試
pytest backend/tests/e2e/ -v

# 6. 特別驗證 error path (不只 happy path)
pytest backend/tests/ -k "error or exception or fail or timeout" -v

# 7. 特別驗證 checkpoint 恢復
pytest backend/tests/ -k "checkpoint or resume or recovery" -v

# 8. 特別驗證 HITL 審批流程
pytest backend/tests/ -k "hitl or approval or human" -v
```

---

## 附錄: 參考文件

| 文件 | 用途 |
|------|------|
| [Python 2026 Significant Changes Guide](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes) | 官方遷移權威指南 |
| [GitHub Releases](https://github.com/microsoft/agent-framework/releases) | 每個版本的 changelog |
| [PyPI agent-framework](https://pypi.org/project/agent-framework/) | 版本歷史 |
| `MAF-Version-Gap-Analysis.md` | IPA 項目的版本差距分析 |
| `MAF-Features-Architecture-Mapping-V8.md` | IPA 項目功能架構映射 |
| `MAF-Claude-Hybrid-Architecture-V8.md` | IPA 項目混合架構實現 |