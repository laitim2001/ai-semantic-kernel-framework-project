# PoC: Agent Team + Subagent — MAF 多 Agent 協作架構驗證

> **Date**: 2026-03-23
> **Status**: 規劃中（待確認後執行）
> **Worktree Branch**: `poc/agent-team`（獨立 git worktree，驗證後才決定是否合併）
> **前置 PoC**: `poc/anthropic-chatclient`（已驗證 MagenticOne + Claude）

---

## 目標

驗證能否用 MAF 的建構元件（Agent、ConcurrentBuilder、GroupChatBuilder、MagenticBuilder）
加上自建的 SharedTaskList，實現接近 Claude Code Agent Team 和 Subagent 的多 Agent 協作模式。

## 文件索引

| # | 文件 | 內容 |
|---|------|------|
| 01 | [discussion-summary.md](01-discussion-summary.md) | 討論記錄：Claude 架構圖分析 + MAF 映射 |
| 02 | [poc-design.md](02-poc-design.md) | PoC 設計文件：架構、測試計劃、驗收標準 |
| 03 | [poc-results.md](03-poc-results.md) | PoC 結果（執行後填寫） |

## 核心驗證項目

| # | 驗證項 | 對應 Claude 概念 | MAF 實現方式 |
|---|--------|-----------------|------------|
| 1 | Subagent 並行獨立執行 | Main Agent → Spawn Subagents | ConcurrentBuilder |
| 2 | Subagent 結果回報整合 | Results → Report to Main | Orchestrator Agent 整合 |
| 3 | SharedTaskList 共享任務池 | Shared Task List | 自建 SharedTaskList 類 |
| 4 | Teammate 自主領取任務 | Claim Tasks | 自建 claim_task() 工具 |
| 5 | Teammate 互相溝通 | Communicate | GroupChatBuilder 共享對話 |
| 6 | Team Lead 監控和介入 | Main Agent (Team Lead) | Orchestrator Agent |
| 7 | 混合模式切換 | 根據場景選擇 Subagent 或 Team | Orchestrator 動態決策 |

## 前置條件

- PoC 1（AnthropicChatClient + MagenticOne）已通過
- MAF `Agent`, `ConcurrentBuilder`, `GroupChatBuilder` 可用
- `ANTHROPIC_API_KEY` 和/或 Azure OpenAI 憑證可用
