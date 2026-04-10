# 討論記錄：Claude Agent 架構分析 + MAF 映射

> **Date**: 2026-03-23
> **Context**: 基於 Claude Code 的 Subagent / Agent Team 架構圖分析

---

## 1. Claude 架構圖解讀

### Subagents（子代理模式）

```
Main Agent
  ├── Spawn Subagent 1 → Work → Result ─┐
  ├── Spawn Subagent 2 → Work → Result ─┤ Report
  └── Spawn Subagent 3 → Work → Result ─┘
```

核心特點： 
- Main Agent 動態 Spawn 多個 Subagent
- 每個 Subagent **獨立工作**（互不溝通）
- 每個產生 Result
- Result 回報給 Main Agent 整合

### Agent Teams（團隊模式）

```
Main Agent (Team Lead)
  → Spawn Team & Assign Tasks
      ↓
  Shared Task List（共享任務池）
      ↑↓ Claim & Update    ↑↓ Claim & Update    ↑↓ Claim & Update
  Teammate 1 ←──Communicate──→ Teammate 2 ←──Communicate──→ Teammate 3
      ↓ Work                    ↓ Work                    ↓ Work
```

核心特點：
- Main Agent (Team Lead) 建立團隊 + 初始任務分配
- **Shared Task List** — 中央任務池，Teammate 自主領取
- Teammate 之間有**雙向溝通**（不只跟 Team Lead 溝通）
- 每個 Teammate 獨立工作但可以協作

### 兩者的根本差異

| 維度 | Subagents | Agent Teams |
|------|-----------|-------------|
| 溝通方式 | 只跟 Main Agent | Teammate 之間互相溝通 |
| 任務分配 | Main Agent 指派 | Teammate 自主領取 |
| 協作性 | 無（各自獨立） | 有（共享任務 + 溝通） |
| 適用場景 | 獨立並行的子任務 | 需要協作的複雜任務 |

---

## 2. MAF 元件映射分析

### MAF 有 5 個 Builder

| Builder | 並行？ | Agent 互相溝通？ | 有 Manager？ | 最接近什麼 |
|---------|--------|----------------|-------------|-----------|
| `ConcurrentBuilder` | ✅ 全部並行 | ❌ 無 | ❌ 無 | **Subagents** |
| `GroupChatBuilder` | ❌ 輪流 | ✅ 共享對話 | ❌ 無 | **Agent Teams 的溝通** |
| `MagenticBuilder` | ❌ 每輪 1 個 | ❌ 透過 Manager 間接 | ✅ Manager | 有 Manager 的順序調度 |
| `HandoffBuilder` | ❌ 順序 | ❌ A→B 單向 | ❌ 無 | 流水線 |
| `WorkflowBuilder` | ⚠️ DAG | ❌ 按邊傳遞 | ❌ 無 | 結構化流程 |

### 缺口分析

| Claude Agent Teams 特點 | MAF 有沒有 | 彌補方案 |
|------------------------|-----------|---------|
| Shared Task List | ❌ 完全沒有 | 自建 `SharedTaskList` 類 |
| Task Claiming | ❌ 完全沒有 | 自建 `claim_task()` 工具 |
| Teammate 雙向溝通 | ⚠️ GroupChatBuilder 提供共享對話 | 可用但是輪流制 |
| 動態 Spawn Agent | ❌ 構建時就固定 | Orchestrator 用 function calling 動態構建 |
| Teammate 並行 + 溝通 | ❌ 並行(Concurrent)和溝通(GroupChat)不能同時 | 需要自建機制 |

---

## 3. 設計方案

### Subagent 模式 — ConcurrentBuilder

```python
# Orchestrator 動態決定 subagent 數量和角色
orchestrator = Agent(client, instructions="...", tools=[create_and_run_subagents])

async def create_and_run_subagents(task, agent_specs):
    agents = [Agent(client, name=s["name"], instructions=s["inst"]) for s in agent_specs]
    builder = ConcurrentBuilder(participants=agents)
    workflow = builder.build()
    return await workflow.run(message=task)
```

### Agent Team 模式 — GroupChatBuilder + SharedTaskList

```python
# 自建共享任務池
class SharedTaskList:
    def add_task(task_id, description, priority)
    def claim_task(agent_name) -> task | None
    def complete_task(task_id, result)
    def get_status() -> str

# 包裝為 Agent 工具
@tool claim_next_task(agent_name) -> str
@tool report_task_result(task_id, result) -> str
@tool view_team_status() -> str
@tool send_message_to_team(message) -> str

# Teammates 用 GroupChatBuilder 溝通
builder = GroupChatBuilder(
    participants=[teammate_1, teammate_2, teammate_3],
    max_rounds=10,
)
```

### 混合模式 — Orchestrator 判斷

```
Orchestrator Agent
    │
    ├─ 判斷「獨立子任務」→ ConcurrentBuilder（Subagent 模式）
    ├─ 判斷「需要協作」→ GroupChatBuilder + SharedTaskList（Team 模式）
    └─ 判斷「需要深度推理」→ MagenticBuilder（MagenticOne 模式）
```

---

## 4. 關鍵問題待 PoC 驗證

| # | 問題 | 驗證方式 |
|---|------|---------|
| 1 | GroupChatBuilder 的 Agent 能不能呼叫工具（claim_task 等）？ | 給 Agent 加 tools，觀察是否執行 |
| 2 | GroupChat 中 Agent 是否真的能看到其他 Agent 的發言？ | 觀察對話歷史 |
| 3 | Agent 是否會主動根據 view_team_status 決定行為？ | 觀察 Agent 的推理過程 |
| 4 | ConcurrentBuilder 的結果格式是什麼？能被 Orchestrator 解析嗎？ | 檢查返回值結構 |
| 5 | Orchestrator 能否用 function calling 動態構建 Builder？ | 實測 |
| 6 | SharedTaskList 在 GroupChat 的多輪中狀態是否正確同步？ | 多輪測試 |
| 7 | 多個 Agent 同時 claim_task 會有競爭條件嗎？ | GroupChat 是順序的，應該沒問題 |
