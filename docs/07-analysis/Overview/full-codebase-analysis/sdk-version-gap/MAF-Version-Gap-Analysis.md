# Microsoft Agent Framework — 版本差異分析報告

**分析日期**: 2026-03-15
**目前版本（IPA Platform）**: `agent-framework>=1.0.0b260114,<2.0.0`（版本鎖定於 2026-01-16）
**Reference Repo**: 最後 commit 2025-12-05 (51721bd9)，pyproject.toml 版本 `1.0.0b251204`
**最新可用版本**: `1.0.0rc4`（2026-03-11 發佈於 PyPI）
**來源**: [PyPI](https://pypi.org/project/agent-framework/)、[GitHub Releases](https://github.com/microsoft/agent-framework/releases)、[Microsoft Learn](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes)

---

## 執行摘要

IPA Platform 目前運行 `1.0.0b260114`，而最新版本為 `1.0.0rc4` — 差距橫跨 **9 個版本，約 2 個月**。此差距包含 **15+ 項破壞性變更**，涵蓋 API 重新命名、例外處理層級、設定系統、工作流程事件、憑證處理和編排命名空間重組。IPA Platform 的 Adapter Pattern 層（`backend/src/integrations/agent_framework/builders/`）提供部分隔離，但多項破壞性變更仍需修改 **6+ 個 adapter 檔案** 和 **5+ 個核心整合檔案**。

**嚴重度：HIGH** — 該框架正積極邁向 GA（1.0.0 穩定版）。延遲升級將使遷移成本呈指數增長。建議在 1-2 個 Sprint 內升級至 `1.0.0rc4`。

---

## 1. 版本時間線（2025-12 至 2026-03）

| 版本 | 日期 | 狀態 | 關鍵主題 |
|------|------|------|----------|
| `1.0.0b251204` | 2025-12-05 | Beta | Reference repo 快照 |
| `1.0.0b260106` | 2026-01-06 | Beta | 假期後更新 |
| `1.0.0b260114` | 2026-01-14 | Beta | **IPA Platform 目前版本** |
| `1.0.0b260116` | 2026-01-16 | Beta | `create_agent` → `as_agent`，`AgentRunResponse` → `AgentResponse` |
| `1.0.0b260123` | 2026-01-23 | Beta | Anthropic 結構化輸出，`response_format` 驗證錯誤 |
| `1.0.0b260127` | 2026-01-27 | Beta | GitHub Copilot SDK BaseAgent |
| `1.0.0b260128` | 2026-01-28 | Beta | 補丁版本 |
| `1.0.0b260130` | 2026-01-30 | Beta | 通用 `ChatOptions`/`ChatResponse`，Claude SDK BaseAgent |
| `1.0.0b260210` | 2026-02-10 | Beta | 編排命名空間遷移，背景回應 |
| `1.0.0rc1` / `1.0.0b260219` | 2026-02-19 | **RC** | 統一憑證、例外處理重設計、設定系統重寫 |
| `1.0.0rc2` | 2026-02-25 | RC | Agent Skills，嵌入抽象 |
| `1.0.0rc3` | 2026-03-04 | RC | Shell 工具，程式碼解譯器增強 |
| `1.0.0rc4` | 2026-03-11 | RC | **PyPI 上的最新版本** |

**差距**: IPA 落後 9 個版本，錯過了 2 個月的演進，包括 RC 里程碑。

---

## 2. 破壞性變更（需要修改程式碼）

### 2.1 立即生效的破壞性變更（自 `1.0.0b260116`）

#### BC-01: `create_agent` 重新命名為 `as_agent`
- **PR**: [#3249](https://github.com/microsoft/agent-framework/pull/3249)
- **影響**: 所有呼叫 `client.create_agent()` 的程式碼必須改為 `client.as_agent()`
- **IPA 影響**: LOW — IPA adapter 已包裝此呼叫；需檢查 `agent_executor.py`

#### BC-02: `AgentRunResponse` 重新命名為 `AgentResponse`
- **PR**: [#3207](https://github.com/microsoft/agent-framework/pull/3207)
- **變更前**: `from agent_framework import AgentRunResponse, AgentRunResponseUpdate`
- **變更後**: `from agent_framework import AgentResponse, AgentResponseUpdate`
- **IPA 影響**: MEDIUM — 用於工作流程建構器和回應處理

#### BC-03: `display_name` 移除；`context_provider` 改為單數；`middleware` 必須為清單
- **PR**: [#3139](https://github.com/microsoft/agent-framework/pull/3139)
- 變更內容：
  1. `display_name` 參數從 agent 中移除
  2. `context_providers`（複數）→ `context_provider`（單數，僅允許 1 個）
  3. `middleware` 現在要求必須為清單（不接受單一實例）
  4. `AggregateContextProvider` 已移除
- **IPA 影響**: HIGH — 多個 adapter 可能使用了 `display_name` 和 `context_providers`

#### BC-04: `WorkflowOutputEvent.source_executor_id` 重新命名為 `executor_id`
- **PR**: [#3166](https://github.com/microsoft/agent-framework/pull/3166)
- **IPA 影響**: MEDIUM — `workflow_executor.py` 中的工作流程事件處理

### 2.2 來自 `1.0.0b260123` 的破壞性變更

#### BC-05: `response_format` 驗證錯誤現在會拋出（不再靜默返回 `None`）
- **PR**: [#3274](https://github.com/microsoft/agent-framework/pull/3274)
- `ChatResponse.value` / `AgentResponse.value` 現在在 schema 驗證失敗時拋出 `ValidationError`
- 新增 `try_parse_value()` 方法用於安全解析
- **IPA 影響**: MEDIUM — 編排層可能需要更新錯誤處理

#### BC-06: AG-UI 執行邏輯簡化
- **PR**: [#3322](https://github.com/microsoft/agent-framework/pull/3322)
- `run_config` dict 參數移除；參數現在直接傳遞
- **IPA 影響**: MEDIUM — `backend/src/integrations/ag_ui/` 中的 AG-UI 整合

### 2.3 來自 `1.0.0b260210` 的破壞性變更

#### BC-07: 編排建構器遷移至專用命名空間
- **變更前**: `from agent_framework import SequentialBuilder, GroupChatBuilder`
- **變更後**: `from agent_framework.orchestrations import SequentialBuilder, GroupChatBuilder`
- **IPA 影響**: **CRITICAL** — 直接影響所有建構器 adapter：
  - `concurrent.py` — `from agent_framework import ConcurrentBuilder`
  - `groupchat.py` — `from agent_framework import GroupChatBuilder, ...`
  - `handoff.py` — `from agent_framework import ...`
  - `magentic.py` — `from agent_framework import MagenticBuilder, ...`
  - `nested_workflow.py` — `from agent_framework import WorkflowBuilder, Workflow, WorkflowExecutor`
  - `planning.py` — `from agent_framework import MagenticBuilder, Workflow`
  - `workflow_executor.py` — `from agent_framework import ...`

### 2.4 來自 `1.0.0rc1` 的破壞性變更（2026 年 2 月 19 日）

#### BC-08: 統一 Azure 憑證處理
- **PR**: [#4088](https://github.com/microsoft/agent-framework/pull/4088)
- `ad_token`、`ad_token_provider`、`get_entra_auth_token` 替換為統一的 `credential` 參數
- 影響：`AzureOpenAIChatClient`、`AzureOpenAIResponsesClient`、`AzureAIClient` 等
- **IPA 影響**: MEDIUM — `agent_executor.py` 引入了 `AzureOpenAIResponsesClient`

#### BC-09: 例外處理層級重新設計
- **PR**: [#4082](https://github.com/microsoft/agent-framework/pull/4082)
- `ServiceException` 系列替換為 `AgentFrameworkException` 體系
- 已移除：`ServiceException`、`ServiceInitializationError`、`ServiceResponseException`、`AgentExecutionException`、`AgentInvocationError`、`AgentInitializationError` 等
- **IPA 影響**: HIGH — 任何引用舊例外類別的例外處理

#### BC-10: 設定系統重寫（移除 pydantic-settings）
- **PR**: [#3843](https://github.com/microsoft/agent-framework/pull/3843)、[#4032](https://github.com/microsoft/agent-framework/pull/4032)
- `AFBaseSettings`（pydantic）替換為 `TypedDict` + `load_settings()`
- `pydantic-settings` 依賴從 agent-framework 中移除
- 設定透過 dict 語法存取，不再使用屬性存取
- **IPA 影響**: LOW-MEDIUM — IPA 使用自己的設定系統，但任何直接使用 AF 設定的地方會受影響

#### BC-11: Provider 狀態依 `source_id` 範圍化
- **PR**: [#3995](https://github.com/microsoft/agent-framework/pull/3995)
- Provider hooks 接收範圍化的 state dict，而非完整的 session state
- `InMemoryHistoryProvider` 預設 `source_id` 從 `"memory"` 改為 `"in_memory"`
- **IPA 影響**: MEDIUM — 自定義 provider 和 checkpoint 邏輯

#### BC-12: Chat/agent 訊息類型對齊
- **PR**: [#3920](https://github.com/microsoft/agent-framework/pull/3920)
- `get_response` 現在一致接收 `Sequence[Message]`
- **IPA 影響**: LOW — Adapter 層處理正規化

#### BC-13: `FunctionTool[Any]` 泛型移除
- **PR**: [#3907](https://github.com/microsoft/agent-framework/pull/3907)
- 直接使用 `FunctionTool` 而非 `FunctionTool[Any]`
- **IPA 影響**: LOW — 僅在使用泛型工具模式時受影響

#### BC-14: 工作流程事件重構為通用 `WorkflowEvent[DataT]`
- 個別事件子類別替換為 `WorkflowEvent[DataT]`
- 使用 `event.type` 字串代替 `isinstance()` 檢查
- **IPA 影響**: HIGH — `workflow_executor.py`、`nested_workflow.py` 中的工作流程事件處理

#### BC-15: Checkpoint 模型和存儲行為重構
- **PR**: [#3744](https://github.com/microsoft/agent-framework/pull/3744)
- **IPA 影響**: MEDIUM — agent_framework 整合中的 `checkpoint.py`

### 2.5 來自 Reference Repo Commits 的破壞性變更（260114 之前）

#### BC-16: 標準化編排輸出為 `list[ChatMessage]`
- **PR**: [#2291](https://github.com/microsoft/agent-framework/pull/2291) — 標記 [BREAKING]
- **IPA 影響**: MEDIUM — GroupChat 和編排輸出處理

#### BC-17: Azure Functions 套件的 Schema 變更
- **PR**: [#2151](https://github.com/microsoft/agent-framework/pull/2151) — 標記 [BREAKING]
- **IPA 影響**: LOW — IPA 不使用 Azure Functions 託管

#### BC-18: 磁性代理工具呼叫審批的 HITL 行為
- **PR**: [#2569](https://github.com/microsoft/agent-framework/pull/2569) — 標記 [BREAKING]
- 支援工具呼叫審批和計劃暫停
- **IPA 影響**: HIGH — `magentic.py` adapter 和 HITL 工作流程整合

---

## 3. 新增功能（升級後可用）

| 功能 | 版本 | PR | 描述 |
|------|------|-----|------|
| 宣告式 YAML 工作流程 | b260114 | #2815 | 基於圖形的 YAML 定義多代理編排執行時 |
| AG-UI 會話持續性 | b260116 | #3136 | 服務管理的對話身份保持 |
| Anthropic 結構化輸出 | b260123 | #3301 | Anthropic 客戶端支援 `response_format` |
| Claude SDK BaseAgent | b260130 | #3509 | MAF 中的原生 Claude Agent SDK adapter |
| GitHub Copilot SDK BaseAgent | b260127 | #3404 | GitHub Copilot SDK 整合 |
| 通用 `ChatOptions`/`ChatResponse` | b260130 | #3305 | 結構化輸出的更好類型推斷 |
| 背景回應 | b260210 | #3808 | 長時間運行的代理任務，帶有 continuation token |
| Session/context providers | b260210 | #3763 | 新的 `SessionContext` 和 `BaseContextProvider` |
| 程式碼解譯器串流 | b260210 | #3775 | 增量程式碼差異更新，用於 UI 渲染 |
| `@tool` 明確 schema | b260210 | #3734 | 工具定義的自定義 schema 處理 |
| 持久化工作流程（Azure Functions） | rc1 | #3630 | Azure Functions 持久化工作流程支援 |
| OpenTelemetry MCP 追蹤 | rc1 | #3780 | 自動追蹤上下文傳播至 MCP 請求 |
| Bedrock provider | rc1 | #3953 | `core[all]` extras 中的 Amazon Bedrock |
| Agent Skills | rc2 | — | Agent 技能和嵌入抽象 |
| Shell 工具 | rc3 | — | Shell 工具和程式碼解譯器增強 |
| Pydantic BaseModel 作為函數結果 | rc4(?) | #2606 | BaseModel 可從函數呼叫返回 |
| 自主切換流程 | rc4(?) | #2497 | 支援自主切換模式 |
| WorkflowBuilder 註冊表 | rc4(?) | #2486 | 工作流程建構器的註冊表模式 |

### 對 IPA Platform 特別有價值的功能：
1. **Claude SDK BaseAgent** — IPA Claude SDK 層的直接整合路徑
2. **宣告式 YAML 工作流程** — 可簡化 IPA 的工作流程定義
3. **背景回應** — 啟用長時間運行的代理任務
4. **OpenTelemetry MCP 追蹤** — 端到端分散式追蹤
5. **HITL 工具呼叫審批** — 磁性代理的原生 HITL 支援
6. **自主切換流程** — 改進切換編排模式

---

## 4. Bug 修復（與 IPA 相關）

| 修復內容 | 版本 | PR | 描述 |
|---------|------|-----|------|
| AgentRunResponse.created_at UTC | rc4(?) | #2590 | 本地時間被錯誤標記為 UTC |
| 空文字內容 pydantic 驗證 | rc4(?) | #2539 | 空內容的 Pydantic 驗證失敗 |
| 重複 MCP 工具/提示 | b251114 | #1876 | 防止重複工具註冊 |
| 工具執行狀態洩漏 | b251204 | #2314 | 修復 aiohttp/Bot Framework 場景 |
| MagenticAgentExecutor repr 工具呼叫 | rc4(?) | #2566 | 修復工具呼叫內容的 repr 字串 |
| 推理模型工作流程切換 | rc1 | #4083 | 修復 gpt-5-mini/gpt-5.2 在多代理工作流程中的問題 |
| service_session_id 切換時洩漏 | rc1 | #4083 | 跨代理狀態洩漏防護 |

---

## 5. API 變更摘要

| 類別 | 舊 API | 新 API | 版本 | 影響 |
|------|--------|--------|------|------|
| Agent 建立 | `client.create_agent()` | `client.as_agent()` | b260116 | LOW |
| 回應類型 | `AgentRunResponse` | `AgentResponse` | b260116 | MEDIUM |
| 回應類型 | `AgentRunResponseUpdate` | `AgentResponseUpdate` | b260116 | MEDIUM |
| Agent 參數 | `display_name="..."` | （已移除） | b260114 | MEDIUM |
| Agent 參數 | `context_providers=[...]` | `context_provider=single` | b260114 | HIGH |
| Agent 參數 | `middleware=single` | `middleware=[list]` | b260114 | MEDIUM |
| 工作流程事件 | `WorkflowOutputEvent.source_executor_id` | `.executor_id` | b260116 | MEDIUM |
| 建構器引入 | `from agent_framework import GroupChatBuilder` | `from agent_framework.orchestrations import GroupChatBuilder` | b260210 | **CRITICAL** |
| Azure 認證 | `azure_ad_token_provider=...` | `credential=...` | rc1 | MEDIUM |
| 例外處理 | `ServiceException` | `AgentFrameworkException` | rc1 | HIGH |
| 設定系統 | `AFBaseSettings`（pydantic） | `TypedDict` + `load_settings()` | rc1 | LOW-MEDIUM |
| Provider 狀態 | `state[self.source_id]["key"]` | `state["key"]`（範圍化） | rc1 | MEDIUM |
| 訊息類型 | `str \| Message \| list[Message]` | `Sequence[Message]` | rc1 | LOW |
| 工具泛型 | `FunctionTool[Any]` | `FunctionTool` | rc1 | LOW |
| 工作流程事件 | `isinstance(event, SubClass)` | `event.type == "output"` | rc1 | HIGH |
| 歷史 Provider | `InMemoryHistoryProvider("memory")` | `InMemoryHistoryProvider("in_memory")` | rc1 | MEDIUM |

---

## 6. 對 IPA Platform 的影響

### 6.1 受影響模組（依嚴重度排序）

#### CRITICAL 影響
| 檔案 | 問題 | 必要變更 |
|------|------|----------|
| `builders/concurrent.py` | BC-07：引入命名空間變更 | 更新 `from agent_framework import ConcurrentBuilder` 為 `from agent_framework.orchestrations import ConcurrentBuilder` |
| `builders/groupchat.py` | BC-07：引入命名空間變更 | 更新所有編排引入 |
| `builders/handoff.py` | BC-07：引入命名空間變更 | 更新切換建構器引入 |
| `builders/magentic.py` | BC-07、BC-18：命名空間 + HITL | 更新引入 + 新增工具呼叫審批支援 |
| `builders/nested_workflow.py` | BC-07：引入命名空間變更 | 更新 `WorkflowBuilder`、`Workflow`、`WorkflowExecutor` 引入 |
| `builders/planning.py` | BC-07：引入命名空間變更 | 更新 `MagenticBuilder`、`Workflow` 引入 |
| `builders/workflow_executor.py` | BC-07、BC-14：命名空間 + 事件 | 更新引入 + 重構事件處理 |

#### HIGH 影響
| 檔案 | 問題 | 必要變更 |
|------|------|----------|
| `builders/groupchat.py` | BC-03：`context_providers` 單數化 | 重構多 provider 模式 |
| `builders/magentic.py` | BC-02、BC-03 | 回應類型重新命名 + agent 參數 |
| `core/approval.py` | BC-09：例外處理層級 | 更新例外處理 |
| `core/approval_workflow.py` | BC-14：工作流程事件 | 更新事件類型檢查 |
| `core/events.py` | BC-14：工作流程事件 | 重構 `isinstance()` 為 `event.type` 檢查 |

#### MEDIUM 影響
| 檔案 | 問題 | 必要變更 |
|------|------|----------|
| `builders/agent_executor.py` | BC-01、BC-08 | `create_agent`→`as_agent`，憑證處理 |
| `checkpoint.py` | BC-15：Checkpoint 重構 | 更新 checkpoint 模型用法 |
| AG-UI 整合層 | BC-06：執行邏輯變更 | 更新 `AGUIEndpoint.run()` 呼叫 |

### 6.2 所需程式碼變更（估算）

| 變更類型 | 檔案數 | 行數（估算） | 複雜度 |
|---------|--------|-------------|--------|
| 引入路徑更新（BC-07） | 7 檔 | ~30 行 | 低 |
| 回應類型重新命名（BC-02） | 4-6 檔 | ~20 行 | 低 |
| Agent 參數變更（BC-03） | 5-8 檔 | ~40 行 | 中 |
| 例外處理層級（BC-09） | 3-5 檔 | ~30 行 | 中 |
| 工作流程事件重構（BC-14） | 2-3 檔 | ~50 行 | 中高 |
| 憑證處理（BC-08） | 1-2 檔 | ~10 行 | 低 |
| Checkpoint 重構（BC-15） | 1 檔 | ~30 行 | 中 |
| 設定遷移（BC-10） | 1-2 檔 | ~15 行 | 低 |
| **合計** | **~15-20 檔** | **~225 行** | **中** |

### 6.3 可選升級功能

| 功能 | 對 IPA 的好處 | 工作量 | 優先級 |
|------|-------------|--------|--------|
| Claude SDK BaseAgent | 原生 Claude 整合 | 低 | HIGH |
| 宣告式 YAML 工作流程 | 簡化工作流程定義 | 中 | MEDIUM |
| 背景回應 | 長時間運行任務 | 中 | HIGH |
| OpenTelemetry MCP 追蹤 | 更好的可觀測性 | 低（自動） | HIGH |
| Agent Skills（rc2） | 可重用的代理能力 | 中 | MEDIUM |
| 自主切換 | 更好的編排 | 低 | HIGH |

---

## 7. 遷移工作量估算

### 階段 A：關鍵路徑（1 Sprint，~13 SP）
| 任務 | 故事點數 | 描述 |
|------|---------|------|
| 引入命名空間遷移 | 3 SP | 更新所有建構器的 `from agent_framework import` 為 `from agent_framework.orchestrations import` |
| 回應類型重新命名 | 2 SP | 全程式碼庫 `AgentRunResponse` → `AgentResponse` |
| Agent 參數變更 | 3 SP | 移除 `display_name`，單數化 `context_provider`，列表化 `middleware` |
| 例外處理層級遷移 | 3 SP | 將 `ServiceException` 系列替換為新層級 |
| 版本鎖定更新 | 2 SP | 更新 `requirements.txt`，測試相容性 |

### 階段 B：工作流程與事件（1 Sprint，~13 SP）
| 任務 | 故事點數 | 描述 |
|------|---------|------|
| 工作流程事件重構 | 5 SP | `isinstance()` → `event.type` 字串檢查 |
| Checkpoint 模型更新 | 3 SP | 適配新的 checkpoint 行為 |
| Provider 狀態範圍化 | 3 SP | 更新自定義 provider hooks |
| 回歸測試 | 2 SP | 完整整合測試執行 |

### 階段 C：增強功能採用（1 Sprint，~8 SP）
| 任務 | 故事點數 | 描述 |
|------|---------|------|
| Claude SDK BaseAgent 整合 | 3 SP | 利用原生 Claude adapter |
| 背景回應 | 3 SP | 啟用長時間運行的代理任務 |
| OpenTelemetry MCP 追蹤 | 2 SP | 配置分散式追蹤 |

### 總估算：**2-3 個 Sprint（~34 SP）**

---

## 8. 遷移建議

### 建議：**在 2 個 Sprint 內升級至 `1.0.0rc4`**

#### 理由：
1. **RC 穩定性** — 框架於 2026-02-19 達到 RC 狀態，表示 API 已趨穩定。RC2-RC4 主要是 bug 修復和增強，非破壞性變更。
2. **GA 即將到來** — 框架正朝 1.0.0 穩定版邁進。現在升級意味著之後更少的遷移工作。
3. **差距擴大中** — 每個新版本增加差異量。IPA Platform 的 Adapter Pattern 提供部分隔離，但無法覆蓋命名空間變更或例外處理層級重寫。
4. **新功能** — Claude SDK BaseAgent、背景回應和 OpenTelemetry 追蹤直接有益於 IPA Platform 的架構。

#### 升級策略：
1. **步驟 1**：直接升級到 `1.0.0rc4`（跳過中間 beta 版本）。重大變更指南涵蓋所有累積變更。
2. **步驟 2**：從引入命名空間變更（BC-07）開始 — 影響最大、風險最低、容易驗證。
3. **步驟 3**：處理回應類型重新命名和 agent 參數變更 — 機械性變更，有明確的前後對比模式。
4. **步驟 4**：重構例外處理和工作流程事件 — 需要更謹慎的測試。
5. **步驟 5**：更新 `requirements.txt` 中的版本鎖定為 `agent-framework>=1.0.0rc4,<2.0.0`

#### 風險緩解：
- 建立功能分支 `feature/maf-rc4-upgrade` 進行隔離測試
- 每個階段後執行完整測試套件
- Adapter Pattern 意味著大多數變更限制在 `backend/src/integrations/agent_framework/`
- 以 [Python 2026 重大變更指南](https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes) 作為權威遷移參考

#### 版本鎖定建議：
```
# requirements.txt
agent-framework>=1.0.0rc4,<2.0.0
```

---

## 附錄 A：Reference Repo 與 PyPI 的差距

本地 reference repo（`reference/agent-framework/`）的最後 commit 為 `51721bd9`（2025-12-05），pyproject.toml 版本為 `1.0.0b251204`。這比最新版本落後 **約 3.5 個月**。

Reference repo 在 2025-10-01 之後的關鍵 commit 包括：
- AG-UI 協議支援 (#1826)
- ChatKit 整合 (#1273)
- 切換編排模式 (#1469)
- Python 3.14 支援 (#1904)
- 工作流程的 MCP 工具支援 (#2029)
- 自主切換流程 (#2497)
- WorkflowBuilder 註冊表 (#2486)
- HITL 工具呼叫審批 (#2569)

**建議**：將 reference repo 更新至最新的 `python-1.0.0rc4` 標籤，以保持本地文件的時效性。

## 附錄 B：IPA Adapter 檔案清單

| 檔案 | 類別 | MAF 引入 |
|------|------|----------|
| `concurrent.py` | `ConcurrentBuilderAdapter` | `ConcurrentBuilder` |
| `groupchat.py` | `GroupChatBuilderAdapter` | `GroupChatBuilder`、`GroupChatManager` 等 |
| `groupchat_voting.py` | `GroupChatVotingAdapter` | 繼承自 GroupChatBuilderAdapter |
| `handoff.py` | `HandoffBuilderAdapter` | Handoff 相關建構器 |
| `magentic.py` | `MagenticBuilderAdapter` | `MagenticBuilder` |
| `nested_workflow.py` | `NestedWorkflowAdapter` | `WorkflowBuilder`、`Workflow`、`WorkflowExecutor` |
| `planning.py` | — | `MagenticBuilder`、`Workflow` |
| `workflow_executor.py` | — | 工作流程執行類別 |
| `agent_executor.py` | — | `ChatAgent`、`ChatMessage`、`AzureOpenAIResponsesClient` |
| `core/approval.py` | — | `Executor`、`handler`、`WorkflowContext` |
| `core/approval_workflow.py` | — | `Workflow`、`Edge` |
| `core/edge.py` | — | `Edge` |
| `checkpoint.py` | — | `WorkflowCheckpoint` |
