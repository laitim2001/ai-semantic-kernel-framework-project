# PoC 結果：Agent Team + Subagent

> **Date**: 2026-03-23
> **Status**: 全部通過
> **Branch**: `poc/agent-team` (git worktree at `../ai-semantic-kernel-poc-team/`)
> **Provider**: Azure OpenAI GPT-5.2（function calling 需要，Claude Haiku 不支持 tool use）

---

## API 預驗證

| 確認項 | 結果 | 備註 |
|--------|------|------|
| GroupChatBuilder 構造函數 | ✅ | 支持 `orchestrator_agent`, `selection_func`, `max_rounds`, `termination_condition` |
| GroupChatBuilder + Agent tools | ✅ | Agent(client, tools=[...]) 建構成功。但 AnthropicChatClient 不支持 function calling |
| ConcurrentBuilder 構造函數 | ✅ | `participants`（必填）、`checkpoint_storage`、`intermediate_outputs` |
| ConcurrentBuilder.with_aggregator() | ✅ | 支持 `Callable[[list[AgentExecutorResponse]], Any]` |
| MAF @tool 裝飾器 | ✅ | `@tool def func() -> str` 自動建立 FunctionTool，docstring 變 description |
| GroupChatBuilder 需要 orchestrator | ✅ | 必須提供 `orchestrator_agent` 或 `selection_func`，否則 ValueError |
| orchestrator_agent 需要 Structured Output | ✅ | Agent 需返回 `AgentOrchestrationOutput` JSON（terminate, reason, next_speaker） |

---

## 測試 A：Subagent（ConcurrentBuilder）

| 驗證項 | 結果 | 備註 |
|--------|------|------|
| ConcurrentBuilder 建構成功 | ✅ | 170ms build time |
| 3 個 Agent 真正並行 | ✅ | **4.4 秒**完成（順序約需 12 秒） |
| 結果回報 | ✅ | 18 events，3 個 AgentExecutorResponse |
| Orchestrator 整合 | ✅ | 結果收集成功 |
| 執行時間 | ✅ 4,427ms | 接近最慢單個 Agent 時間，確認並行 |

**結論：ConcurrentBuilder 完全實現 Subagent 並行模式。**

---

## 測試 B：Agent Team（GroupChatBuilder + SharedTaskList）

> 使用 Azure OpenAI GPT-5.2（Claude Haiku 不支持 function calling，Agent 無法呼叫工具）

| 驗證項 | 結果 | 備註 |
|--------|------|------|
| SharedTaskList 初始化 | ✅ | 4 個任務建立成功 |
| claim_task() 工具呼叫 | ✅ | LogExpert 成功 claim 所有 4 個任務 |
| report_task_result() | ✅ | 4/4 任務都有結果回報 |
| view_team_status() | ✅ | Agent 可查看任務狀態 |
| Agent 間溝通可見 | ✅ | **6 條 team messages**，DBExpert 和 AppExpert 看到 LogExpert 發現後回應 |
| 協作效果 | ✅ | 3 個 Agent 都指向同一個根因（SQLSTATE 42P01 schema drift） |
| SharedTaskList 狀態同步 | ✅ | 多輪中狀態正確同步 |
| 執行時間 | 99,799ms | 6 輪 GroupChat，每輪含 LLM 呼叫 |

### 實際任務完成情況

```
[completed] T1: Analyze ETL application logs (by: LogExpert)
  → ETL logs show DB write failures, SQLSTATE 42P01

[completed] T2: Check database schema changes (by: LogExpert)
  → Probable DDL changes to apac_stage tables

[completed] T3: Verify network connectivity (by: LogExpert)
  → No network-layer failure, errors are DB-related

[completed] T4: Review ETL scheduling configuration (by: LogExpert)
  → Jobs start on schedule, fail during LoadStep
```

### 團隊訊息（Agent 間溝通）

```
[LogExpert]: T1 findings: ETL logs show DB schema-related failures...
[LogExpert]: T2 (DB changes) hypothesis aligned to errors...
[LogExpert]: T3: Network not implicated as primary...
[LogExpert]: T4: Scheduler likely not root cause...
[DBExpert]: DB angle: error pair (42P01 missing apac_stage.customer_delta)...
[AppExpert]: DB/infra angle: ETL failures point to schema drift...
```

### 觀察到的問題

1. **LogExpert 太積極** — Round-robin 讓它先發言，它 claim 了全部 4 個任務
2. **DBExpert 和 AppExpert 沒 claim 到任務** — 但透過 team messages 補充了各自專長的分析
3. **需要改進**：在 instructions 中加入「每人最多 claim 2 個任務」限制，或用智能 orchestrator 分配

**結論：GroupChatBuilder + SharedTaskList 成功實現 Agent Team 協作模式。Agent 之間能互相看到發言和溝通。**

---

## 測試 C：混合模式

### C1：獨立任務 → 應選 Subagent

| 驗證項 | 結果 | 備註 |
|--------|------|------|
| 任務 | 「Check VPN for Taipei, HK, Singapore」 | 3 個獨立任務 |
| Orchestrator 選擇 | ✅ **subagent** | 正確判斷 |
| 推理 | 「independent and can be run in parallel」 | 合理 |
| 執行結果 | ✅ | 3 agent 並行完成 |

### C2：協作任務 → 應選 Team

| 驗證項 | 結果 | 備註 |
|--------|------|------|
| 任務 | 「ERP performance degradation, DBA + app team collaborate」 | 需要協作 |
| Orchestrator 選擇 | ✅ **team** | 正確判斷 |
| 推理 | 「cross-layer, needs DBA and application team collaboration」 | 合理 |
| 執行結果 | ✅ | 4/4 tasks done, 6 team messages |

**結論：Orchestrator 能正確根據任務特性選擇 Subagent 或 Team 模式。**

---

## 關鍵發現

### 成功驗證

1. **ConcurrentBuilder = Subagent 模式** — 完全匹配 Claude Code Subagent 概念
2. **GroupChatBuilder + SharedTaskList = Agent Team 模式** — Agent 互相溝通、自主領取任務
3. **Orchestrator + function calling = 動態模式選擇** — LLM 推理決定用哪種模式
4. **Azure OpenAI GPT-5.2 支持所有功能** — function calling + structured output

### 發現的限制

| 限制 | 影響 | 解決方案 |
|------|------|---------|
| AnthropicChatClient 不支持 function calling | Claude Agent 無法在 GroupChat 中使用工具 | 需加 `FUNCTION_INVOKING_CHAT_CLIENT_MARKER` + tools 轉換 |
| GroupChatBuilder 的 orchestrator_agent 需要 Structured Output | Claude 不能直接當 Team Lead orchestrator | 用 `selection_func` 替代，或加 Structured Output 支持 |
| Round-robin 讓第一個 Agent 搶走所有任務 | 任務分配不均 | instructions 加限制或用智能 orchestrator |
| GroupChat 是輪流制不是並行 | 不像真正的即時協作 | 可接受 — IT 場景不需毫秒級 |

### 需要後續開發的功能

1. **AnthropicChatClient function calling** — 讓 Claude 也能使用 @tool
2. **智能 orchestrator** — 不只是 round-robin，而是根據任務狀態和專長分配
3. **任務限制機制** — 每個 Agent 最多 claim N 個任務
4. **MagenticEventBridge** — 事件 → AG-UI SSE 前端串流

---

## 結論

**PoC 成功驗證了 MAF 可以實現接近 Claude Code Agent Team 和 Subagent 的多 Agent 協作模式。**

核心組合：
- **Subagent** = `ConcurrentBuilder`（並行、獨立、結果回報）
- **Agent Team** = `GroupChatBuilder` + 自建 `SharedTaskList`（共享任務、互相溝通、自主領取）
- **Orchestrator** = `Agent` + function calling（動態選擇模式）

需要自建的部分（MAF 沒有的）：
- `SharedTaskList`（~80 行）
- `team_tools`（~60 行）
- Orchestrator 路由邏輯（~100 行）

MAF 提供的基礎設施足夠，只需少量自建代碼即可實現完整的多 Agent 協作。
