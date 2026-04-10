# Orchestrator Agent 架構差距分析

## 日期：2026-03-22
## 背景：Phase 42-43 Swarm Agent 討論中發現的根本架構問題

---

## 核心發現：現在的是「路由器」，不是「思考者」

### 現有架構 (HybridOrchestratorV2 / OrchestratorMediator)

```
用戶輸入
    ↓
[L4] BusinessIntentRouter — 三層瀑布式分類
    PatternMatcher (regex) → SemanticRouter (embedding) → LLM Classifier
    ↓
[L4] CompletenessChecker — 資訊是否足夠？
    ↓ 不足 → GuidedDialogEngine（模板式追問）
    ↓
[L4] RiskAssessor — 7 維度評分
    ↓
[L4] HITLController — HIGH/CRITICAL 需審批
    ↓
[L5] FrameworkSelector — 按規則選擇框架
    • 結構化 → MAF Builder
    • 開放式 → Claude SDK Worker
    • 混合 → MAF + Claude
    • 群集 → Swarm
    ↓
[L6/L7] 執行層 — MAF Builder 或 Claude SDK
```

**特徵：**
1. 決策是基於規則的：FrameworkSelector 用預設規則，不是 LLM 推理
2. 路由是靜態映射：意圖→工作流類型是寫死的表
3. 無任務分解能力：6 個 Handler 是固定的處理鏈
4. 無進度追蹤和重規劃：沒有 Task Ledger / Progress Ledger
5. Claude 只在末端執行：被當作「工具」使用，不參與決策

### 期望的 Orchestrator Agent

```
用戶輸入
    ↓
[安全閘門] 三層路由 + RiskAssessor + HITL  ← 保留
    ↓
[Orchestrator Agent = Claude Opus with adaptive thinking]
    │
    ├── 自主分析：「這個問題需要什麼？」
    ├── 動態分解：「分成 N 個子任務」（Task Ledger）
    ├── 智能分派：「任務 1 給 Research Agent，任務 2 給 D365 Agent」
    ├── 持續監控：「任務 2 卡住了」（Progress Ledger）
    ├── 自動重規劃：「改用 MCP 直接查詢」
    └── 綜合結果：「把子任務結果合成最終答案」
```

### 差異對照表

| 維度 | HybridOrchestratorV2 | Orchestrator Agent |
|------|----------------------|-------------------|
| 決策機制 | 規則 + 靜態映射表 | LLM 自主推理 |
| 任務分解 | ❌ 不能 | ✅ 動態分解為 N 個子任務 |
| 進度追蹤 | ❌ 沒有 | ✅ Progress Ledger 持續反思 |
| 重規劃 | ❌ 失敗就 fallback | ✅ stall detection → 自動重新規劃 |
| 代理間通訊 | ❌ 單向分派 | ✅ 共享對話 / 互相挑戰 |
| Claude 角色 | 末端工具 | 核心大腦（決策 + 協調） |
| 框架選擇 | 啟動時靜態選擇一次 | 每個子任務可動態選擇 |
| 人在迴路 | 固定位置 | 任何步驟可動態請求 |

## 關鍵洞見：它們是互補的

- L4 Orchestration（路由 + 風險 + HITL）= **安全閘門**（保留）
- Orchestrator Agent（MagenticOne Manager）= **智能執行層**（新增）
- 不是互相取代，是上下游關係

## AgentHandler 差一步就是 Orchestrator Agent

AgentHandler 已有 LLM + function calling (Sprint 144)，但定位是「回答者」不是「決策者」。
改造方向：把 system prompt 從「回答用戶問題」改為「分析需求、決定策略、分派執行」。
