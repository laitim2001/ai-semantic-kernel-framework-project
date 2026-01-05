# Phase 13 UAT 測試：混合 MAF + Claude SDK 整合

> **Phase 13**：混合核心架構
> **故事點數**：105 pts (Sprint 52-54)
> **重點**：真實業務場景測試，非僅 API 功能測試

---

## 開發狀態

| Sprint | 名稱 | 點數 | 狀態 | 進度檔案 |
|--------|------|------|------|----------|
| Sprint 52 | Intent Router & Mode Detection | 35 pts | ✅ 完成 | `sprint-52/progress.md` |
| Sprint 53 | Context Bridge & Sync | 35 pts | ✅ 完成 | `sprint-53/progress.md` |
| Sprint 54 | HybridOrchestrator Refactor | 35 pts | ✅ 完成 | `sprint-54/progress.md` |

**Phase 13 開發總進度**: 105/105 pts (100%) ✅

> **重要**：Phase 13 開發已於 2026-01-03 完成。本文件為 UAT 測試規劃。

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

> **注意**：Mode Switching Mid-Execution 測試已移至 Phase 14 (Sprint 55-57)
> 原因：需要 ModeSwitcher 組件（Phase 14 實現）

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

> **注意**：執行中模式切換測試已移至 Phase 14 (需要 ModeSwitcher)

### 4. 統一工具執行器場景 (`scenario_unified_executor.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| 單一工具執行 | 不同來源的工具執行 (MAF/Claude/Hybrid) | 路由正確性 |
| 批次執行 | 多工具並行執行 | 結果聚合 |
| Hook 管道 | Pre/Post 執行鉤子 | 驗證/日誌/轉換 |
| 錯誤處理 | 未知工具、無效參數、逾時 | 錯誤類型識別 |

### 5. MAF Tool Callback 場景 (`scenario_tool_callback.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| 攔截邏輯 | MAF 工具呼叫攔截 | 路由至 UnifiedToolExecutor |
| 封鎖工具 | 安全敏感工具封鎖 | 封鎖模式匹配 |
| 審批路由 | 需審批工具的路由 | HITL 整合 |
| 回退行為 | Claude 不可用時回退至 MAF | 降級處理 |
| 上下文傳播 | 執行上下文傳遞 | 變數/工具結果保留 |

### 6. 複雜度分析器場景 (`scenario_analyzers.py`)

| 場景 | 描述 | 預期複雜度 |
|------|------|----------|
| 簡單任務 | FAQ、狀態查詢 | 0.0-0.3 (CHAT_MODE) |
| 中等任務 | 報告生成、排程 | 0.3-0.6 (HYBRID_MODE) |
| 複雜任務 | 審批流程、入職流程 | 0.6-0.8 (WORKFLOW_MODE) |
| 極複雜任務 | 預算規劃、系統遷移 | 0.8-1.0 (WORKFLOW_MODE) |
| 上下文影響 | 相同任務不同上下文 | 動態調整 |
| 邊界案例 | 空輸入、極長輸入、特殊字元 | 穩健處理 |

### 7. Mapper 場景 (`scenario_mappers.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| MAF → Claude 上下文 | 工作流程變數轉換 | 類型保留 |
| MAF 歷史轉換 | 對話歷史格式轉換 | 工具呼叫格式 |
| Agent → Prompt | 代理狀態生成系統提示 | 指令/約束包含 |
| Claude → MAF Checkpoint | Claude 狀態轉 Checkpoint | 會話/工具保留 |
| Claude → 執行記錄 | 執行資料轉 MAF 格式 | 狀態/錯誤映射 |
| 工具 → 審批請求 | 工具呼叫生成審批 | 風險等級判定 |
| 雙向往返 | MAF → Claude → MAF | 資料無損 |

### 8. 同步器場景 (`scenario_synchronizer.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| 樂觀鎖 | 版本檢查更新 | 版本遞增 |
| 並發修改 | 多客戶端同時更新 | 衝突偵測 |
| 衝突解決策略 | LWW/Server Wins/Merge/Manual | 策略套用 |
| 深度合併 | 巢狀物件/陣列合併 | 欄位級合併 |
| 回滾操作 | 失敗回滾/Checkpoint 恢復 | 狀態還原 |
| 狀態恢復 | 網路失敗/崩潰/Split-brain | 恢復動作 |
| 跨框架同步 | MAF ↔ Claude 雙向 | 一致性維護 |

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

**最後更新**：2026-01-05
**作者**：IPA Platform 團隊
