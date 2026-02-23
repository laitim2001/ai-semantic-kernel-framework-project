# 智能體編排平台：MAF + Claude Agent SDK 混合架構實現（Codex 完整版）

> **文件版本**: 1.0
> **最後更新**: 2026-02-11
> **定位**: Agent Orchestration Platform (智能體編排平台)
> **分析範圍**: `backend/src`, `frontend/src`, `backend/tests`, `frontend/e2e`
> **分析方式**: 全量靜態掃描 + 關鍵代碼路徑驗證 + 交叉統計
> **對齊參考**: `docs/07-analysis/MAF-Claude-Hybrid-Architecture-V7.md`

---

## 實現狀態總覽

### 核心規模（2026-02-11 實測）

- Backend source files: **625**
- Frontend source files: **203**
- Backend tests: **305**
- Frontend E2E: **13**
- Backend Python LOC: **190,724**
- Frontend TS/TSX LOC: **43,012**
- API endpoint decorators: **542**
- Route files: **52**
- include_router references: **61**

### 11 層實現狀態

| 層級 | 目錄範圍 | 檔案數 | LOC | 狀態 |
|---|---|---:|---:|---|
| L1 Frontend | `frontend/src` | 203 | 43,012 | ✅ REAL |
| L2 API Layer | `backend/src/api` | 138(.py) | 36,301 | ✅ REAL |
| L3 AG-UI Protocol | `backend/src/integrations/ag_ui` | 23 | 8,062 | ✅ REAL |
| L4 Orchestration Entry | `backend/src/integrations/orchestration` | 39 | 13,330 | ✅ REAL + MOCK-FALLBACK |
| L5 Hybrid | `backend/src/integrations/hybrid` | 60 | 17,872 | ✅ REAL |
| L6 MAF Builder | `backend/src/integrations/agent_framework` | 53 | 30,687 | ✅ REAL |
| L7 Claude SDK | `backend/src/integrations/claude_sdk` | 47 | 12,506 | ✅ REAL |
| L8 MCP | `backend/src/integrations/mcp` | 43 | 10,528 | ✅ REAL |
| L9 Supporting+Swarm | `a2a/memory/audit/patrol/correlation/rootcause/swarm` | 38 | 8,928 | ⚠️ PARTIAL |
| L10 Domain | `backend/src/domain` | 112 | 39,407 | ✅ REAL |
| L11 Infrastructure | `backend/src/infrastructure` | 22 | 2,812 | ⚠️ PARTIAL |

---

## 執行摘要

此 codebase 已具備大型智能體編排平台的完整骨架，架構重心清晰位於 `integrations`（105,060 LOC），核心能力已覆蓋：

1. 多 Agent 編排（MAF builders）
2. 混合調度（Hybrid orchestrator）
3. 智能決策鏈（Intent Router + Claude SDK）
4. 人機協作（HITL + AG-UI）
5. 工具整合（MCP + A2A + Memory + Swarm）

目前主要缺口不在「功能存在性」，而在「生產一致性」與「風險邊界」：

1. 並行狀態同步保護不足（雙 `ContextSynchronizer`）
2. 開發與運行環境配置錯位（port/CORS）
3. fallback 邊界（InMemory / Mock）治理不足

---

## 1. 完整架構設計

### 1.1 11 層架構圖（Codex）

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ L1 Frontend (React 18 + TS + Vite:3005)                                  │
│   pages(39) + components(127) + hooks(17) + stores(4)                    │
└───────────────┬────────────────────────────────────────────────────────────┘
                │ HTTP/SSE
┌───────────────▼────────────────────────────────────────────────────────────┐
│ L2 API Layer (FastAPI)                                                    │
│   52 route files, 542 decorators, 61 include_router                       │
└───────────────┬────────────────────────────────────────────────────────────┘
                │ event stream / approval
┌───────────────▼────────────────────────────────────────────────────────────┐
│ L3 AG-UI Protocol                                                         │
│   SSE bridge, shared state, HITL event stream                             │
└───────────────┬────────────────────────────────────────────────────────────┘
                │ route intent + validate + gate
┌───────────────▼────────────────────────────────────────────────────────────┐
│ L4 Orchestration Entry                                                    │
│   InputGateway + IntentRouter + GuidedDialog + RiskAssessor + HITL        │
└───────────────┬────────────────────────────────────────────────────────────┘
                │ framework switch / context bridge
┌───────────────▼────────────────────────────────────────────────────────────┐
│ L5 Hybrid                                                                  │
│   orchestrator_v2 + switching + checkpoint + context sync                  │
└───────┬──────────────┬───────────────────┬─────────────────────────────────┘
        │              │                   │
┌───────▼──────┐ ┌─────▼────────┐ ┌────────▼────────┐
│ L6 MAF       │ │ L7 Claude SDK│ │ L8 MCP          │
│ builders(53) │ │ runtime(47)  │ │ servers(43)     │
└───────┬──────┘ └─────┬────────┘ └────────┬────────┘
        │              │                   │
┌───────▼───────────────────────────────────▼────────────────────────────────┐
│ L9 Supporting Integrations                                                 │
│ memory / a2a / audit / patrol / correlation / rootcause / swarm           │
└───────────────┬────────────────────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────────────────────┐
│ L10 Domain (business modules: sessions/workflows/orchestration/...)       │
└───────────────┬────────────────────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────────────────────┐
│ L11 Infrastructure (db/cache/messaging/storage abstractions)              │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 端到端執行流程圖（E2E）

```text
[User / External Source]
   -> [Frontend UI or Webhook]
   -> [API Router]
   -> [InputGateway]
   -> [3-tier Intent Routing]
      - Tier1 Pattern
      - Tier2 Semantic
      - Tier3 LLM
   -> [Guided Dialog if incomplete]
   -> [RiskAssessor + HITL Gate]
   -> [Hybrid Orchestrator]
      -> (MAF Builder path | Claude SDK path | mixed path)
   -> [MCP tools + memory/a2a/swarm]
   -> [Decision/Audit/Telemetry]
   -> [AG-UI SSE stream + API response]
   -> [Frontend state render]
```

---

## 2. 子系統深度分析

### 2.1 Backend 五大區塊

| 區塊 | 檔案數 | LOC | 說明 |
|---|---:|---:|---|
| `api` | 138 | 36,301 | API 入口與路由聚合 |
| `core` | 23 | 7,143 | 設定、安全、共用核心 |
| `domain` | 112 | 39,407 | 業務模組核心邏輯 |
| `infrastructure` | 22 | 2,812 | DB/快取等基礎設施 |
| `integrations` | 315 | 105,060 | 編排與外部整合主體 |

### 2.2 Integrations 深度拆分

| 模組 | 檔案數 | LOC | 狀態 |
|---|---:|---:|---|
| `agent_framework` | 53 | 30,687 | REAL |
| `hybrid` | 60 | 17,872 | REAL |
| `claude_sdk` | 47 | 12,506 | REAL |
| `mcp` | 43 | 10,528 | REAL |
| `orchestration` | 39 | 13,330 | REAL + MOCK-FALLBACK |
| `ag_ui` | 23 | 8,062 | REAL |
| `swarm` | 7 | 2,332 | REAL |
| `memory` | 5 | 1,508 | PARTIAL |
| `a2a` | 4 | 745 | PARTIAL |
| `audit` | 4 | 972 | REAL |
| `patrol` | 11 | 2,142 | REAL |
| `correlation` | 4 | 993 | PARTIAL |
| `rootcause` | 3 | 652 | PARTIAL |

### 2.3 Frontend 深度拆分

| 區塊 | 檔案數 | 說明 |
|---|---:|---|
| `pages` | 39 | 業務頁與工具頁 |
| `components` | 127 | 可重用 UI 與領域元件 |
| `hooks` | 17 | 狀態和流程 hook |
| `store + stores` | 4 | 全域狀態管理 |

`components` 內部分佈：

- `unified-chat`: 65
- `ag-ui`: 19
- `ui`: 18
- `DevUI`: 15
- 其餘：layout/shared/auth

---

## 3. 關鍵實作驗證

### 3.1 MAF Builder 整合

- Builder `.py` 檔：23
- 含 `agent_framework` import 的 builder：8
- `code_interpreter.py` 未見 `agent_framework` import（獨立路徑）

### 3.2 MCP Server 覆蓋

MCP servers 目錄存在 5 類：

1. azure
2. filesystem
3. ldap
4. shell
5. ssh

### 3.3 Swarm 端到端覆蓋

- backend integration: `backend/src/integrations/swarm` (7 files)
- api routes: `backend/src/api/v1/swarm` (5 files)
- frontend page: `frontend/src/pages/SwarmTestPage.tsx`
- frontend hooks: `useSwarmMock.ts`, `useSwarmReal.ts`

---

## 4. 已知問題（完整清單）

| # | 問題 | 影響 | 嚴重度 | 證據 |
|---|---|---|---|---|
| 1 | 兩套 `ContextSynchronizer` 使用 in-memory dict，未見鎖 | 競爭條件 | 嚴重 | `backend/src/integrations/hybrid/context/sync/synchronizer.py`, `backend/src/integrations/claude_sdk/hybrid/synchronizer.py` |
| 2 | 前端 proxy `8010` vs 後端 `8000` | API 打點偏差 | 高 | `frontend/vite.config.ts`, `backend/main.py` |
| 3 | CORS 預設 `3000`，前端 dev `3005` | 跨域失敗風險 | 高 | `backend/src/core/config.py`, `frontend/vite.config.ts` |
| 4 | `main.py` 啟動採 `reload=True` | 生產啟動配置風險 | 高 | `backend/main.py` |
| 5 | API auth pattern 只覆蓋部分檔案（8 files） | 授權覆蓋不足風險 | 高 | `backend/src/api/v1` pattern scan |
| 6 | 存在 InMemory 類（9）與 Mock 類（19） | fallback 邊界不明 | 中 | 全庫 pattern scan |
| 7 | 前端 `console.log` 54 處 | 訊息外露/噪音 | 中 | `frontend/src` scan |
| 8 | 大檔案集中：backend >800 行 25 檔、frontend 7 檔 | 維護成本高 | 中 | size scan |
| 9 | 缺少 `reactflow` 依賴 | workflow 視覺化風險 | 中 | `frontend/package.json` |

---

## 5. 架構成熟度評估

| 維度 | 評級 | 結論 |
|---|---|---|
| 架構分層清晰度 | A- | 11 層分工明確 |
| 核心能力完整度 | A- | 關鍵能力存在且可串聯 |
| 生產可運行一致性 | B | 配置與 fallback 邊界待治理 |
| 可維護性 | B- | 大檔案與跨層耦合需分解 |
| 風險治理成熟度 | B- | 已有審計/巡檢，但策略不一 |

---

## 6. 結論

這個 codebase 已達「完整平台級」實作，不是 demo 等級。下一階段的核心任務不是增加更多功能，而是做 **一致性與治理收斂**：

1. 併發狀態一致性（ContextSynchronizer）
2. dev/prod 配置一致性（port/CORS/startup profile）
3. REAL 與 MOCK-FALLBACK 邊界清晰化

完整證據索引見：`docs/07-analysis/codex/appendix-evidence-index.md`
