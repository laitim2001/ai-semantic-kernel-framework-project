# Claude Agent Study — Orchestrator Agent 架構研究

## 日期：2026-03-22
## 目的：分析如何從「路由器」升級為「思考者」

---

## 文件索引

| # | 文件 | 內容 |
|---|------|------|
| 01 | [orchestrator-agent-architecture-gap.md](01-orchestrator-agent-architecture-gap.md) | 核心差距：路由器 vs 思考者，現有架構 vs 期望架構 |
| 02 | [manager-model-registry-design.md](02-manager-model-registry-design.md) | ManagerModelRegistry + ManagerModelSelector YAML 配置方案 |
| 03 | [maf-multi-model-capability.md](03-maf-multi-model-capability.md) | MAF 1.0.0rc4 多模型能力實測（import 驗證） |
| 04 | [agent-team-feasibility-report.md](04-agent-team-feasibility-report.md) | 5 Agent Team 可行性分析報告（架構 + MAF + 效能 + 成本） |
| 05 | [existing-architecture-inventory.md](05-existing-architecture-inventory.md) | Phase 42-43 後的完整系統盤點 |

## 相關分析報告（由 Agent Team 產出）

| 報告 | 路徑 | 作者 |
|------|------|------|
| 架構分析 | `docs/07-analysis/Overview/full-codebase-analysis/manager-model-registry-architecture-analysis.md` | 系統架構師 |
| MAF 整合 | `claudedocs/6-ai-assistant/analysis/magentic-multi-model-registry-analysis.md` | 後端架構師 |
| 效能分析 | `claudedocs/6-ai-assistant/analysis/manager-model-registry-performance-analysis.md` | 效能工程師 |

## 核心結論

1. **現有架構是「路由器」不是「思考者」** — Mediator 7-handler 是固定 Chain of Responsibility
2. **MAF 原生支援 per-agent 模型** — `Agent(client, ...)` positional + `BaseChatClient` 抽象
3. **MAF 沒有 Anthropic ChatClient** — 需要自建 `AnthropicChatClient(BaseChatClient)`
4. **ManagerModelRegistry + Selector 可行** — YAML 零代碼切換
5. **L1-L4 不需改動** — 安全閘門保留，只在 L5-L7 新增/修改

## PoC 驗證結果（2026-03-23）

### PoC-1: AnthropicChatClient + MagenticOne（分支 `poc/anthropic-chatclient`）
- ✅ Claude Haiku 和 Azure GPT-5.2 都可作為 MagenticOne Manager
- ✅ MagenticOne 完整迴圈運作（PLAN → Worker → Progress Ledger → Replan）
- ⚠️ AnthropicChatClient 不支持 function calling（需加 FUNCTION_INVOKING 標記）
- 詳見 [poc-findings.md](poc-findings.md)

### PoC-2: Agent Team + Subagent（分支 `poc/agent-team`）
- ✅ ConcurrentBuilder 3 agent 真正並行（4.4s）
- ✅ GroupChatBuilder + SharedTaskList 協作模式（4/4 tasks, 6 team messages）
- ✅ Orchestrator 能正確判斷用 subagent 或 team 模式
- ⚠️ GroupChatBuilder 的 orchestrator_agent 需要 Structured Output（Claude 不支持）
- 詳見 [../poc-agent-team/](../poc-agent-team/)

## 下一步

基於 PoC 驗證結果，Phase 44 規劃（Sprint 151-152, ~16 SP）：
- AnthropicChatClient（PoC 代碼可直接複製）
- ManagerModelRegistry + YAML 配置
- ManagerModelSelector + routing rules
- MagenticBuilderAdapter 構造函數注入 `manager_agent=`

後續 Phase 待規劃：
- AnthropicChatClient function calling 支持
- Agent Team 整合（SharedTaskList + GroupChatBuilder）
- Orchestrator Agent（頂層路由 + 工具 + 記憶）
- MagenticEventBridge（MagenticOne → AG-UI SSE）
