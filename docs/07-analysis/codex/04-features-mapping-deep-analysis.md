# 智能體編排平台功能架構映射指南（Codex 完整版）

> **文件版本**: 1.0
> **最後更新**: 2026-02-11
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **前置文件**: `docs/07-analysis/codex/03-architecture-deep-analysis.md`
> **對齊參考**: `docs/07-analysis/MAF-Features-Architecture-Mapping-V7.md`
> **分析方式**: 全量掃描 + 關鍵功能路徑驗證

---

## 實現狀態總覽

本報告採用狀態分類：

1. `REAL`：有可追蹤的執行路徑
2. `PARTIAL`：主體存在，但邊界受 fallback/硬編碼影響
3. `STUB`：僅骨架或占位
4. `EMPTY`：結構存在、實質能力缺失
5. `MOCK-FALLBACK`：非測試路徑可落入 mock

### 八大能力分類結論

| 類別 | 主要層級 | 狀態 | 說明 |
|---|---|---|---|
| Agent 編排能力 | L6 + L10 | REAL | builders + domain orchestration 主鏈完整 |
| 人機協作能力 | L4 + L3 + L1 | REAL / MOCK-FALLBACK | HITL 完整，但存在 InMemory/mock 邊界 |
| 狀態與記憶能力 | L5 + L9 | PARTIAL | checkpoint/memory 存在，持久化一致性需收斂 |
| 前端介面能力 | L1 | REAL | pages/components/hooks 規模完整 |
| 連接與整合能力 | L4 + L8 + L9 | REAL | InputGateway + MCP + A2A 可組合 |
| 智能決策能力 | L4 + L5 + L7 | REAL | 3-tier intent + hybrid + claude runtime |
| 可觀測性能力 | L4 + L9 | PARTIAL | audit/patrol 有，correlation/rootcause 仍偏弱 |
| Agent Swarm 能力 | L9 + L3 + L2 + L1 | REAL | backend/api/frontend 三端覆蓋 |

---

## 1. 功能映射總圖

```text
Agent 編排 (L6/L10)
  -> WorkflowExecutor / Concurrent / GroupChat / Handoff / Nested / Planning
  -> Domain orchestration handlers

人機協作 (L4/L3/L1)
  -> RiskAssessor -> HITLController -> ApprovalHandler -> AG-UI SSE -> Frontend Approval UI

狀態記憶 (L5/L9)
  -> Hybrid checkpoint backends + unified memory + mem0 bridge

連接整合 (L4/L8/L9)
  -> InputGateway -> source handlers -> MCP servers -> A2A protocol

智能決策 (L4/L5/L7)
  -> PatternMatcher -> SemanticRouter -> LLMClassifier -> Hybrid switch

Swarm (L9/L2/L1)
  -> SwarmTracker/Integration -> /api/v1/swarm -> SwarmTestPage/useSwarm*
```

---

## 2. 功能群組詳細映射

### 2.1 Agent 編排能力（REAL）

| 功能群組 | 主要檔案 |
|---|---|
| Sequential workflow | `backend/src/integrations/agent_framework/builders/workflow_executor.py` |
| Parallel workflow | `backend/src/integrations/agent_framework/builders/concurrent.py` |
| GroupChat orchestration | `backend/src/integrations/agent_framework/builders/groupchat.py` |
| Handoff orchestration | `backend/src/integrations/agent_framework/builders/handoff.py` |
| Nested workflow | `backend/src/integrations/agent_framework/builders/nested_workflow.py` |
| Planning adapter | `backend/src/integrations/agent_framework/builders/planning.py` |
| Magentic workflow | `backend/src/integrations/agent_framework/builders/magentic.py` |
| Agent executor | `backend/src/integrations/agent_framework/builders/agent_executor.py` |
| Code interpreter path | `backend/src/integrations/agent_framework/builders/code_interpreter.py` |

判定：

- Builder 檔案共 23
- 8 個 builder 直接使用 `agent_framework` import
- `code_interpreter.py` 走獨立路徑，標記為 `PARTIAL`

### 2.2 人機協作能力（REAL / MOCK-FALLBACK）

| 功能群組 | 主要檔案 | 狀態 |
|---|---|---|
| HITL 控制 | `backend/src/integrations/orchestration/hitl/controller.py` | REAL |
| 審批處理 | `backend/src/integrations/orchestration/hitl/approval_handler.py` | REAL |
| 通知服務 | `backend/src/integrations/orchestration/hitl/notification.py` | REAL |
| AG-UI 審批流 | `backend/src/integrations/ag_ui/features/human_in_loop.py` | REAL |
| 前端審批 UI | `frontend/src/components/ag-ui`, `frontend/src/pages/approvals` | REAL |

風險：默認/常見路徑可能落入 InMemory storage，標記 `MOCK-FALLBACK` 邊界。

### 2.3 狀態與記憶能力（PARTIAL）

| 功能群組 | 主要檔案 | 狀態 |
|---|---|---|
| Hybrid checkpoint | `backend/src/integrations/hybrid/checkpoint` | REAL |
| Context sync | `backend/src/integrations/hybrid/context/sync/synchronizer.py` | PARTIAL |
| Claude hybrid sync | `backend/src/integrations/claude_sdk/hybrid/synchronizer.py` | PARTIAL |
| Unified memory | `backend/src/integrations/memory/unified_memory.py` | REAL |
| mem0 bridge | `backend/src/integrations/memory/mem0_client.py` | PARTIAL |

### 2.4 前端介面能力（REAL）

| 模組 | 檔案數 |
|---|---:|
| pages | 39 |
| components | 127 |
| hooks | 17 |
| stores | 4 |

重點：`unified-chat` 65 檔，屬核心互動主體。

### 2.5 連接與整合能力（REAL）

| 能力 | 證據 |
|---|---|
| InputGateway | `backend/src/integrations/orchestration/input_gateway` |
| Source handlers | ServiceNow / Prometheus / User input handlers |
| MCP servers | azure/filesystem/ldap/shell/ssh |
| A2A protocol | `backend/src/integrations/a2a` |

### 2.6 智能決策能力（REAL）

| 能力 | 主要檔案 |
|---|---|
| Tier1 Pattern matching | `backend/src/integrations/orchestration/intent_router/pattern_matcher` |
| Tier2 Semantic router | `backend/src/integrations/orchestration/intent_router/semantic_router` |
| Tier3 LLM classifier | `backend/src/integrations/orchestration/intent_router/llm_classifier` |
| Completeness checking | `backend/src/integrations/orchestration/intent_router/completeness` |
| Hybrid switching | `backend/src/integrations/hybrid/switching` |

### 2.7 可觀測性能力（PARTIAL）

| 能力 | 檔案 | 狀態 |
|---|---|---|
| Decision audit | `backend/src/integrations/audit` | REAL |
| Patrol checks | `backend/src/integrations/patrol` | REAL |
| Correlation | `backend/src/integrations/correlation` | PARTIAL |
| Rootcause | `backend/src/integrations/rootcause` | PARTIAL |

### 2.8 Swarm 能力（REAL）

| 區塊 | 證據 |
|---|---|
| Swarm backend | `backend/src/integrations/swarm` (7 files) |
| Swarm API | `backend/src/api/v1/swarm` (5 files) |
| Swarm frontend | `frontend/src/pages/SwarmTestPage.tsx`, `frontend/src/hooks/useSwarmMock.ts`, `frontend/src/hooks/useSwarmReal.ts` |

---

## 3. 完整量化對照表

| 指標 | 數值 |
|---|---:|
| backend/src files | 625 |
| frontend/src files | 203 |
| backend/src/api files | 140 |
| api route files | 52 |
| endpoint decorators | 542 |
| include_router refs | 61 |
| frontend pages/components/hooks | 39 / 127 / 17 |
| backend >800 LOC files | 25 |
| frontend >800 LOC files | 7 |
| frontend console.log count | 54 |
| InMemory class count | 9 |
| Mock class count | 19 |

---

## 4. 缺口與改進優先級

### P0（立即）

1. ContextSynchronizer 併發保護（兩實作同步治理）
2. Vite proxy/CORS/後端 port 配置對齊
3. API 授權覆蓋策略收斂（至少先鎖高風險路由）

### P1（短期）

1. InMemory/Mock fallback 顯式化（feature flag + runtime guard）
2. correlation/rootcause 真實資料源接入
3. 大檔案拆分（先拆 >1000 LOC）

### P2（中期）

1. workflow visualization 依賴補齊與頁面整合
2. 統一 store/stores 結構
3. 測試覆蓋與路徑驗證自動化

---

## 5. 結論

本專案已具備完整平台級能力；要達成「企業可運營」的下一階段，核心在於 **一致性治理** 而非新增功能。從功能映射角度，最關鍵是：

1. 將 `REAL` 與 `MOCK-FALLBACK` 的邊界制度化
2. 以可重跑指標維持架構與功能報告的一致性
3. 將高風險項目納入固定驗收門檻

證據索引：`docs/07-analysis/codex/appendix-evidence-index.md`
