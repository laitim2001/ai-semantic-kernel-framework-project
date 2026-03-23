# PoC 設計：Agent Team + Subagent 多 Agent 協作

> **Date**: 2026-03-23
> **Worktree Branch**: `poc/agent-team`
> **Backend Port**: 8003（避免與主 repo 8000 和 PoC-1 8002 衝突）
> **Frontend Port**: 3007
> **預估時間**: 1 session

---

## 1. PoC 範圍

### 測試 A：Subagent 模式（ConcurrentBuilder）

**目標**：驗證 Orchestrator 能動態建立 Subagent 並行執行

**測試場景**：
```
用戶：「請同時檢查 APAC 區域的 3 個系統：ETL Pipeline、CRM 服務、郵件伺服器」

預期行為：
  Orchestrator 判斷 → 3 個獨立任務 → 用 ConcurrentBuilder
  ├── Subagent-1: 檢查 ETL（並行）
  ├── Subagent-2: 檢查 CRM（並行）
  └── Subagent-3: 檢查郵件（並行）
  Orchestrator 整合 3 個結果 → 返回用戶
```

**驗證項目**：
- [ ] ConcurrentBuilder 建構成功
- [ ] 3 個 Agent 真正並行執行（不是順序）
- [ ] 每個 Agent 獨立回報結果
- [ ] Orchestrator 能整合所有結果
- [ ] 執行時間接近最慢的單個 Agent（而非 3 倍）

---

### 測試 B：Agent Team 模式（GroupChatBuilder + SharedTaskList）

**目標**：驗證 Teammates 能在共享對話中協作、領取任務、互相溝通

**測試場景**：
```
用戶：「排查 APAC ETL Pipeline 故障，需要多個專家協作分析」

預期行為：
  Team Lead 建立 SharedTaskList:
    T1: 分析應用程式日誌（priority 1）
    T2: 檢查 DB schema 變更（priority 1）
    T3: 檢查網路連通性（priority 2）
    T4: 分析 ETL 排程配置（priority 2）

  GroupChat 開始：
    Round 1: LogExpert 看到任務清單 → claim T1 → 開始工作
    Round 2: DBExpert 看到任務清單 → claim T2 → 開始工作
    Round 3: LogExpert 回報 T1 結果 → 發現 "Column not found" 錯誤
             → send_message: 「DB 專家注意，日誌顯示欄位名稱問題」
    Round 4: DBExpert 看到 LogExpert 的訊息 → 結合自己的 T2 分析
             → 回報：「確認 3 天前有 schema migration 改了欄位名」
    Round 5: AppExpert 看到討論 → claim T4 → 檢查 ETL 配置是否用舊欄位名
    ...
```

**驗證項目**：
- [ ] SharedTaskList 正確初始化
- [ ] Agent 呼叫 claim_task() 工具成功
- [ ] Agent 呼叫 report_task_result() 工具成功
- [ ] Agent 呼叫 view_team_status() 能看到其他人的進度
- [ ] Agent A 的發言在 Agent B 的下一輪中可見（GroupChat 溝通）
- [ ] Agent 根據其他 Agent 的發現調整自己的行為（協作效果）
- [ ] SharedTaskList 狀態在多輪中正確同步
- [ ] 最終所有任務都被完成（或被 max_rounds 截止）

---

### 測試 C：混合模式（Orchestrator 動態選擇）

**目標**：驗證 Orchestrator 能根據任務特性選擇 Subagent 或 Team 模式

**測試場景 C1（應選 Subagent）**：
```
用戶：「分別查一下台北、香港、新加坡辦公室的 VPN 連線狀態」
→ 3 個獨立任務，不需要協作 → Subagent 模式
```

**測試場景 C2（應選 Agent Team）**：
```
用戶：「排查 ERP 系統今天早上的效能問題，需要 DBA、應用團隊、網路團隊協作」
→ 需要多專家協作 → Agent Team 模式
```

**驗證項目**：
- [ ] Orchestrator 正確判斷 C1 → Subagent
- [ ] Orchestrator 正確判斷 C2 → Agent Team
- [ ] 兩種模式都能正確執行並返回結果

---

## 2. 技術架構

### 後端新增檔案

```
backend/src/api/v1/poc/
├── agent_team_poc.py          # PoC API 端點（~200 LOC）
│   ├── POST /test-subagent    # 測試 A
│   ├── POST /test-team        # 測試 B
│   └── POST /test-hybrid      # 測試 C
│
backend/src/integrations/poc/
├── __init__.py
├── shared_task_list.py        # SharedTaskList 實作（~80 LOC）
└── team_tools.py              # claim_task / report_result 等工具（~60 LOC）
```

### SharedTaskList 設計

```python
class SharedTaskList:
    """Thread-safe shared task list for Agent Team collaboration."""

    def __init__(self):
        self._tasks: dict[str, TaskItem] = {}
        self._messages: list[TeamMessage] = []  # 團隊溝通記錄

    def add_task(self, task_id, description, priority=1) -> None
    def claim_task(self, agent_name) -> TaskItem | None
    def complete_task(self, task_id, result) -> None
    def add_message(self, from_agent, content) -> None
    def get_status(self) -> str         # 任務狀態摘要
    def get_messages(self) -> str       # 最近的團隊訊息
    def is_all_done(self) -> bool       # 所有任務是否完成
```

### Agent 工具定義

```python
# 每個 Teammate 可用的工具
def claim_next_task(agent_name: str) -> str
    """領取下一個最高優先級的待處理任務"""

def report_task_result(task_id: str, result: str) -> str
    """回報任務完成結果"""

def view_team_status() -> str
    """查看所有任務狀態 + 誰在做什麼"""

def send_message(from_agent: str, message: str) -> str
    """發送訊息給團隊（所有人可見）"""

def get_team_messages() -> str
    """查看最近的團隊訊息"""
```

### GroupChatBuilder 配置（API 預驗證已完成）

```python
builder = GroupChatBuilder(
    participants=[teammate_1, teammate_2, teammate_3],
    orchestrator_agent=team_lead,     # Team Lead 控制對話流程（非 round-robin）
    max_rounds=10,
    termination_condition=condition,  # 支持自訂終止條件
)
```

### ConcurrentBuilder 配置（API 預驗證已完成）

```python
builder = ConcurrentBuilder(participants=[sub1, sub2, sub3])
builder = builder.with_aggregator(aggregator_func)  # 結果聚合器
workflow = builder.build()
```

---

## 3. API 預驗證結果（2026-03-23 已完成）

| # | 確認項 | 結果 | 發現 |
|---|--------|------|------|
| 1 | `GroupChatBuilder` 構造函數 | ✅ | 支持 `orchestrator_agent`（Team Lead）、`termination_condition`、`max_rounds` |
| 2 | `GroupChatBuilder` Agent + tools | ✅ | Agent(client, tools=[...]) 建構成功，有 warning 但可用 |
| 3 | `ConcurrentBuilder` 構造函數 | ✅ | `participants`（必填）、`checkpoint_storage`、`intermediate_outputs` |
| 4 | `ConcurrentBuilder.with_aggregator()` | ✅ | 支持 `Callable[[list[AgentExecutorResponse]], Any]` 聚合函數 |
| 5 | MAF `Agent` + `tools` | ✅ | `Agent(client, tools=[tool1, tool2])` 可用 |
| 6 | `@tool` 裝飾器 | ✅ | `@tool def func() -> str` 自動建立 `FunctionTool`，docstring 變 description |
| 7 | GroupChat Agent 對話歷史 | ⏳ 待實測 | 需要在 PoC 測試 B 中驗證 |

### 關鍵發現（影響架構設計）

**GroupChatBuilder.orchestrator_agent：**
- 可以指定一個 Agent 作為 orchestrator 控制對話流程
- 不指定時是 round-robin（輪流發言）
- 指定後，orchestrator 決定每輪誰發言 — **接近 Team Lead 概念**
- 底層是 `BaseGroupChatOrchestrator`，有 `handle_participant_response` 等方法

**ConcurrentBuilder.with_aggregator()：**
- 可以配置結果聚合函數
- 接受 `Callable[[list[AgentExecutorResponse]], Any]`
- **不需要手動用 Orchestrator 整合 Subagent 結果**

**@tool 裝飾器：**
- `from agent_framework import tool`
- `@tool def claim_task(agent_name: str) -> str:` → 自動建立 `FunctionTool`
- docstring 自動變成 tool description
- 支持 `name`, `description`, `schema` 等覆寫參數

---

## 4. 前端測試 UI

在 SwarmTestPage 加入新的測試區塊（或建立新頁面 `/agent-team-test`）：

```
┌─ Agent Team PoC 測試面板 ────────────────────────┐
│                                                   │
│  Mode: [Subagent] [Team] [Hybrid]                 │
│  Provider: [Claude Haiku] [GPT-5.2] [Claude Opus] │
│  Task: [________________________]                  │
│                                                   │
│  [Run Test]                                       │
│                                                   │
│  ── Results ──────────────────────────────────     │
│  Steps:                                           │
│    [OK] build_agents (312ms)                      │
│    [OK] run_workflow (25300ms)                     │
│    [OK] final_answer                              │
│                                                   │
│  ── SharedTaskList Status ────────────────────     │
│  [completed] T1: 分析日誌 (by: LogExpert)          │
│  [completed] T2: 檢查 DB (by: DBExpert)           │
│  [in_progress] T3: 檢查網路 (by: AppExpert)       │
│                                                   │
│  ── Team Messages ────────────────────────────     │
│  [LogExpert] 發現 Column not found 錯誤            │
│  [DBExpert] 確認有 schema migration                │
│                                                   │
│  ── Events (48) ──────────────────────────────     │
│  [0] WorkflowEvent ...                            │
│  [1] WorkflowEvent ...                            │
└───────────────────────────────────────────────────┘
```

---

## 5. 驗收標準

### 必須通過（PoC 才算成功）

| # | 標準 | 重要性 |
|---|------|--------|
| 1 | ConcurrentBuilder 3 個 Agent 真正並行執行 | 🔴 |
| 2 | GroupChatBuilder 中 Agent 能呼叫自訂工具 | 🔴 |
| 3 | Agent A 的發言在 Agent B 的回合中可見 | 🔴 |
| 4 | SharedTaskList 的 claim/complete 正確運作 | 🔴 |
| 5 | Orchestrator 能整合最終結果 | 🔴 |

### 最好通過（加分項）

| # | 標準 | 重要性 |
|---|------|--------|
| 6 | Agent 根據其他 Agent 的發現主動調整行為 | 🟡 |
| 7 | Orchestrator 能動態決定用 Subagent 或 Team | 🟡 |
| 8 | 混合模式（Subagent + Team）在同一次任務中使用 | 🟡 |
| 9 | Azure OpenAI 和 Claude 都可作為 Agent | 🟡 |

### 記錄但不阻擋

| # | 觀察項 |
|---|--------|
| 10 | GroupChat 的輪流限制對協作效果的影響 |
| 11 | 多輪 GroupChat 的 token 消耗趨勢 |
| 12 | SharedTaskList 在真實場景中的實用性 |

---

## 6. 執行步驟

```
Step 0: API 預驗證
  → inspect GroupChatBuilder / ConcurrentBuilder 構造函數
  → 確認 Agent tools 參數用法
  → 確認 MAF @tool 裝飾器

Step 1: 建立 git worktree
  → git worktree add ../ai-semantic-kernel-poc-team -b poc/agent-team HEAD
  → 複製 .env

Step 2: 建立 SharedTaskList + 工具
  → shared_task_list.py
  → team_tools.py

Step 3: 建立 PoC API 端點
  → agent_team_poc.py（3 個端點）

Step 4: 測試 A — Subagent（ConcurrentBuilder）
  → 3 個 Agent 並行
  → 驗證結果收集

Step 5: 測試 B — Agent Team（GroupChatBuilder + SharedTaskList）
  → 3 個 Teammate + 共享任務
  → 驗證溝通 + 領取 + 協作

Step 6: 測試 C — 混合模式
  → Orchestrator 動態選擇

Step 7: 記錄結果到 poc-results.md

Step 8: Commit 到 worktree 分支
```

---

## 7. 風險和備選方案

| 風險 | 影響 | 備選方案 |
|------|------|---------|
| GroupChatBuilder 不支持 Agent tools | 🔴 Team 模式無法運作 | 改用 MagenticBuilder + 自建訊息傳遞 |
| ConcurrentBuilder 不支持 stream | 🟡 無法即時觀察進度 | 接受，只看最終結果 |
| GroupChat Agent 看不到其他人的發言 | 🔴 溝通不成立 | 改用自建的訊息佇列 + ConcurrentBuilder |
| 工具呼叫格式不相容 | 🟡 | 調整工具定義方式 |
| token 消耗過大 | 🟡 | 用 Haiku 降低成本 |

---

## 8. 與 IPA Platform 的整合路徑（PoC 後）

如果 PoC 成功，後續整合到 IPA 的路徑：

```
Phase 44（已規劃）: AnthropicChatClient + ManagerModelRegistry
    ↓
Phase 45（新增）: Agent Team 整合
    Sprint A: SharedTaskList + TeamTools 移入正式代碼
    Sprint B: Orchestrator Agent（頂層路由 + 工具）
    Sprint C: MagenticEventBridge（事件 → AG-UI SSE）
    Sprint D: 前端 TeamPanel（SharedTaskList 視覺化）
    Sprint E: E2E 驗證（完整流程：路由 → Orchestrator → Team/Subagent → 結果）
```
