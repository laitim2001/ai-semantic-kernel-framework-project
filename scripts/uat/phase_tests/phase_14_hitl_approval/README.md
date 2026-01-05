# Phase 14 UAT 測試：人工審核與核准機制

> **Phase 14**：進階混合功能 (HITL & Approval)
> **故事點數**：100 pts (Sprint 55-57)
> **重點**：風險驅動審核、動態模式切換、狀態持久化

---

## 開發狀態

| Sprint | 名稱 | 點數 | 狀態 | 進度檔案 |
|--------|------|------|------|----------|
| Sprint 55 | Risk Assessment Engine | 35 pts | ✅ 完成 | `sprint-55/progress.md` |
| Sprint 56 | Mode Switcher & HITL | 35 pts | ✅ 完成 | `sprint-56/progress.md` |
| Sprint 57 | Unified Checkpoint & Polish | 30 pts | ✅ 完成 | `sprint-57/progress.md` |

**Phase 14 開發總進度**: 100/100 pts (100%) ✅

> **重要**：Phase 14 開發已於 2026-01-03 完成。本文件為 UAT 測試規劃。

---

## 概述

Phase 14 實現進階混合架構功能，包含智慧風險評估、動態模式切換，以及跨框架的統一 Checkpoint 管理。這些 UAT 測試驗證關鍵業務場景下的人工審核機制。

> **從 Phase 13 移入的測試**：
> - Mode Switching Mid-Execution 測試（原 S54-4）已移至本 Phase
> - 原因：需要 ModeSwitcher 組件（Sprint 56 實現）
> - 這確保了測試與實現的正確對應關係

## Sprint 涵蓋範圍

### Sprint 55：風險評估引擎 (35 pts)
- **S55-1**：RiskAssessmentEngine (12 pts) - 多因素風險評分
- **S55-2**：RiskPolicy (10 pts) - 風險閾值與策略管理
- **S55-3**：ApprovalRouter (8 pts) - 風險驅動的審批路由
- **S55-4**：Risk API (5 pts) - REST API 端點

### Sprint 56：模式切換器 (35 pts)
- **S56-1**：ModeSwitcher Core (10 pts) - 優雅模式轉換
- **S56-2**：TransitionManager (10 pts) - 轉換狀態管理
- **S56-3**：ContextPreserver (5 pts) - 切換時上下文保留
- **S56-4**：Switcher API (5 pts) - REST API 端點

### Sprint 57：統一 Checkpoint (30 pts)
- **S57-1**：UnifiedCheckpointStorage (10 pts) - 跨框架存儲
- **S57-2**：StateSerializer (8 pts) - MAF + Claude 狀態序列化
- **S57-3**：RecoveryManager (7 pts) - 狀態恢復管理
- **S57-4**：Checkpoint API (5 pts) - REST API 端點

---

## 測試場景

### 1. 風險評估場景 (`scenario_risk_assessment.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| 高風險交易偵測 | 大額轉帳、異常操作偵測 | 風險分數 > 閾值觸發 HITL |
| 風險驅動審批路由 | 根據風險等級路由至不同審批者 | 正確審批層級 |
| 動態風險閾值調整 | 根據歷史資料調整閾值 | 閾值更新生效 |
| 風險審計軌跡 | 完整記錄風險評估過程 | 審計記錄完整 |

**業務場景範例**：
- 員工報銷 $50,000+ → 自動觸發財務長審批
- 新供應商首次付款 → 需要採購經理確認
- 非工作時間系統操作 → 觸發安全審查

### 2. 模式切換場景 (`scenario_mode_switcher.py`)

> **注意**：此場景包含從 Phase 13 (S54-4) 移入的 Mode Switching Mid-Execution 測試

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| 工作流程 → 對話轉換 | 執行中暫停詢問問題 | 工作流程狀態保留 |
| 對話 → 工作流程升級 | 對話中觸發正式流程 | 無縫銜接執行 |
| 優雅模式轉換 | 等待安全點再切換 | 無資料遺失 |
| 切換時上下文保留 | 跨模式維持對話歷史 | 上下文完整 |
| **執行中模式切換** | 工作流程執行中切換至對話模式 | 安全點檢查、狀態保留 |
| **對話中觸發工作流程** | 對話訊息觸發結構化流程 | 工作流程正確啟動 |
| **切換後回復原模式** | 切換後返回原始執行狀態 | 狀態完全恢復 |

**業務場景範例**：
- 用戶正在執行請假申請，突然問「假期餘額是多少？」
- 客服對話中用戶說「幫我建立一張工單」
- 審批流程中審批者需要查詢政策說明
- 工作流程執行到一半，用戶需要與 AI 討論下一步選項

### 3. 統一 Checkpoint 場景 (`scenario_unified_checkpoint.py`)

| 場景 | 描述 | 驗證項目 |
|------|------|----------|
| Checkpoint 建立與恢復 | 保存並恢復完整狀態 | 狀態完全一致 |
| 跨框架狀態恢復 | MAF + Claude 聯合恢復 | 兩側狀態同步 |
| Checkpoint 版本控制 | 多版本管理與回滾 | 版本選擇正確 |
| 部分狀態恢復 | 選擇性恢復特定組件 | 精確恢復範圍 |

**業務場景範例**：
- 系統故障後恢復用戶的審批流程進度
- 用戶明天繼續昨天的對話和工作
- 回滾到審批前的狀態重新處理

---

## 執行測試

### 完整 Phase 14 測試套件
```bash
cd scripts/uat/phase_tests
python -m phase_14_hitl_approval.phase_14_hitl_approval_test
```

### 個別場景測試
```bash
# 僅風險評估
python -m phase_14_hitl_approval.scenario_risk_assessment

# 僅模式切換
python -m phase_14_hitl_approval.scenario_mode_switcher

# 僅統一 Checkpoint
python -m phase_14_hitl_approval.scenario_unified_checkpoint
```

### 使用真實 LLM (Azure OpenAI)
```bash
export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<key>"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5.2"

python -m phase_14_hitl_approval.phase_14_hitl_approval_test --real-llm
```

---

## 測試的 API 端點

| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/v1/hitl/risk/assess` | POST | 評估操作風險等級 |
| `/api/v1/hitl/risk/policy` | GET/PUT | 取得/更新風險策略 |
| `/api/v1/hitl/approvals` | GET | 列出待審批項目 |
| `/api/v1/hitl/approvals/{id}/approve` | POST | 核准審批項目 |
| `/api/v1/hitl/approvals/{id}/reject` | POST | 拒絕審批項目 |
| `/api/v1/hitl/mode/switch` | POST | 切換執行模式 |
| `/api/v1/hitl/mode/status` | GET | 取得當前模式狀態 |
| `/api/v1/hitl/checkpoint/save` | POST | 建立 Checkpoint |
| `/api/v1/hitl/checkpoint/restore` | POST | 恢復 Checkpoint |
| `/api/v1/hitl/checkpoint/list` | GET | 列出可用 Checkpoint |

---

## 測試資料

測試場景使用真實業務資料：
- **交易金額**：$100 ~ $1,000,000 各級距
- **風險等級**：LOW、MEDIUM、HIGH、CRITICAL
- **審批者**：經理、總監、財務長、CEO
- **工作流程**：報銷、採購、請假、入職

---

## 成功標準

### 必須通過
- [ ] 高風險操作 100% 觸發 HITL 審批
- [ ] 模式切換不遺失任何對話或工作流程狀態
- [ ] Checkpoint 恢復後狀態與保存時完全一致
- [ ] 審計軌跡完整記錄所有風險評估決策

### 效能目標
- 風險評估：< 300ms
- 模式切換：< 500ms
- Checkpoint 保存：< 1s
- Checkpoint 恢復：< 2s

---

## 依賴項目

- 後端伺服器運行於 `http://localhost:8000`
- PostgreSQL 資料庫可存取
- Redis 用於 Checkpoint 快取
- Azure OpenAI 用於真實 LLM 測試（可選）

---

**最後更新**：2026-01-05
**作者**：IPA Platform 團隊
