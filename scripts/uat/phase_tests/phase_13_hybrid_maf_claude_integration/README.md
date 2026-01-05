# Phase 13 UAT 測試：混合 MAF + Claude SDK 整合

> **Phase 13**：混合核心架構
> **故事點數**：105 pts (Sprint 52-54)
> **重點**：真實業務場景測試，非僅 API 功能測試

---

## 概述

Phase 13 實現核心混合架構，啟用 Microsoft Agent Framework (MAF) 與 Claude Agent SDK 之間的智慧路由。這些 UAT 測試驗證真實業務場景，而非僅測試 API 功能。

## Sprint 涵蓋範圍

### Sprint 52：意圖路由器與模式偵測 (35 pts)
- **S52-1**：IntentClassifier (8 pts) - 基於 LLM 的意圖分類
- **S52-2**：ModeDecisionEngine (10 pts) - 多因素模式決策
- **S52-3**：RoutingPolicy (10 pts) - 基於策略的路由規則
- **S52-4**：IntentRouter API (7 pts) - REST API 端點

### Sprint 53：上下文橋接與同步 (35 pts)
- **S53-1**：ContextBridge Core (10 pts) - 雙向狀態同步
- **S53-2**：StateTransformer (8 pts) - MAF ↔ Claude 格式轉換
- **S53-3**：ConflictResolver (10 pts) - 狀態衝突處理
- **S53-4**：Context Bridge API (7 pts) - REST API 端點

### Sprint 54：HybridOrchestrator 重構 (35 pts)
- **S54-1**：HybridOrchestratorV2 (12 pts) - 增強版編排器
- **S54-2**：ModeAwareExecution (10 pts) - 模式感知執行
- **S54-3**：UnifiedToolExecutor (8 pts) - 統一工具層
- **S54-4**：Orchestrator API (5 pts) - REST API 端點

---

## 測試場景

### 1. 意圖路由場景 (`scenario_intent_routing.py`)

| 場景 | 描述 | 預期模式 |
|------|------|----------|
| 發票處理 | "處理發票 #INV-2026-001 進行審批" | WORKFLOW_MODE |
| 客戶諮詢 | "退款政策是什麼？" | CHAT_MODE |
| 模糊輸入 | "幫我處理這份報告" | HYBRID_MODE (依上下文決定) |
| 強制覆蓋 | 用戶明確請求特定模式 | 強制模式 |

### 2. 上下文橋接場景 (`scenario_context_bridge.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| MAF → Claude 同步 | 工作流程步驟狀態同步至 Claude | 上下文保留 |
| Claude → MAF 同步 | 對話上下文同步至 MAF | 變數更新 |
| 雙向同步 | 完整狀態往返 | 資料完整性 |
| 衝突解決 | 衝突狀態更新 | 解決策略套用 |

### 3. 混合編排器場景 (`scenario_hybrid_orchestrator.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| 工作流程模式 | 多步驟結構化工作流程 | 步驟完成度 |
| 對話模式 | 對話式互動 | 回應品質 |
| 混合自動路由 | 動態模式選擇 | 正確路由 |
| 執行中切換 | 執行期間切換模式 | 狀態保留 |

---

## 執行測試

### 完整 Phase 13 測試套件
```bash
cd scripts/uat/phase_tests
python -m phase_13_hybrid_maf_claude_integration.phase_13_hybrid_core_test
```

### 個別場景測試
```bash
# 僅意圖路由
python -m phase_13_hybrid_maf_claude_integration.scenario_intent_routing

# 僅上下文橋接
python -m phase_13_hybrid_maf_claude_integration.scenario_context_bridge

# 僅混合編排器
python -m phase_13_hybrid_maf_claude_integration.scenario_hybrid_orchestrator
```

### 使用真實 LLM (Azure OpenAI)
```bash
export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<key>"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5.2"

python -m phase_13_hybrid_maf_claude_integration.phase_13_hybrid_core_test --real-llm
```

---

## 測試的 API 端點

| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/v1/hybrid/analyze` | POST | 分析輸入以偵測模式 |
| `/api/v1/hybrid/execute` | POST | 使用混合路由執行 |
| `/api/v1/hybrid/execute/stream` | POST | 使用 SSE 串流執行 |
| `/api/v1/hybrid/switch-mode` | POST | 手動切換模式 |
| `/api/v1/hybrid/context/sync` | POST | 在框架間同步上下文 |
| `/api/v1/hybrid/context/state` | GET | 取得當前上下文狀態 |
| `/api/v1/hybrid/metrics` | GET | 取得混合執行指標 |

---

## 測試資料

測試場景使用真實業務資料：
- **發票編號**：INV-2026-001、INV-2026-002 等
- **用戶查詢**：真實客服場景
- **工作流程步驟**：實際審批流程
- **上下文變數**：類生產環境的狀態資料

---

## 成功標準

### 必須通過
- [ ] 意圖路由正確識別模式達 90%+ 測試案例
- [ ] 上下文橋接在同步操作中維持狀態完整性
- [ ] 混合編排器處理模式切換時無資料遺失
- [ ] 所有 API 端點回傳預期的回應格式

### 效能目標
- 意圖分類：< 500ms
- 上下文同步：< 200ms
- 模式切換：< 1s
- 完整工作流程執行：< 30s

---

## 依賴項目

- 後端伺服器運行於 `http://localhost:8000`
- PostgreSQL 資料庫可存取
- Redis 用於快取（可選）
- Azure OpenAI 用於真實 LLM 測試（可選）

---

**最後更新**：2026-01-03
**作者**：IPA Platform 團隊
