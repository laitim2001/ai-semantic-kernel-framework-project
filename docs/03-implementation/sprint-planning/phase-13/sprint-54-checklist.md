# Sprint 54 Checklist: HybridOrchestrator Refactor

## Pre-Sprint Setup

- [ ] 確認 Sprint 52 (Intent Router) 已完成
- [ ] 確認 Sprint 53 (Context Bridge) 已完成
- [ ] 確認所有 MAF Adapters 可用
- [ ] 建立 `backend/src/integrations/hybrid/execution/` 目錄結構

---

## S54-1: Unified Tool Executor 實現 (13 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/execution/__init__.py`
- [ ] `backend/src/integrations/hybrid/execution/unified_executor.py`
  - [ ] `ToolSource` 枚舉
  - [ ] `ToolExecutionResult` 資料類別
  - [ ] `UnifiedToolExecutor` 主類別
  - [ ] `execute()` 方法
  - [ ] `_run_pre_hooks()` 方法
  - [ ] `_run_post_hooks()` 方法
  - [ ] `_execute_via_claude()` 方法
  - [ ] `_sync_result_to_source()` 方法
  - [ ] `_request_approval()` 方法
- [ ] `backend/src/integrations/hybrid/execution/tool_router.py`
  - [ ] `ToolRouter` 類別
  - [ ] 路由規則定義
- [ ] `backend/src/integrations/hybrid/execution/result_handler.py`
  - [ ] `ResultHandler` 類別
  - [ ] 結果轉換邏輯

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/execution/test_unified_executor.py`
- [ ] `backend/tests/unit/integrations/hybrid/execution/test_tool_router.py`
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] Tool 執行成功通過 Claude
- [ ] Pre/Post hooks 正確觸發
- [ ] 結果正確同步

---

## S54-2: MAF Tool Callback 整合 (10 pts)

### 檔案建立/修改
- [ ] `backend/src/integrations/hybrid/execution/tool_callback.py`
  - [ ] `MAFToolCallback` 類別
  - [ ] `on_tool_request()` 方法
  - [ ] 上下文轉換邏輯
- [ ] 修改 `backend/src/integrations/agent_framework/builders/groupchat.py`
  - [ ] 添加 `tool_callback` 參數支持
- [ ] 修改 `backend/src/integrations/agent_framework/builders/handoff.py`
  - [ ] 添加 `tool_callback` 參數支持
- [ ] 修改 `backend/src/integrations/agent_framework/builders/concurrent.py`
  - [ ] 添加 `tool_callback` 參數支持

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/execution/test_tool_callback.py`
- [ ] MAF Adapter 整合測試
- [ ] Tool 回調完整流程測試

### 驗證
- [ ] MAF Agent 的 Tool 請求正確路由
- [ ] 結果正確返回給 MAF Agent
- [ ] 錯誤處理正常

---

## S54-3: HybridOrchestrator V2 重構 (7 pts)

### 檔案建立/修改
- [ ] `backend/src/integrations/hybrid/orchestrator_v2.py`
  - [ ] `HybridOrchestratorV2` 類別
  - [ ] `execute()` 方法
  - [ ] `_execute_workflow_mode()` 方法
  - [ ] `_execute_chat_mode()` 方法
  - [ ] `_execute_hybrid_mode()` 方法
- [ ] 更新 `backend/src/integrations/hybrid/__init__.py`
  - [ ] 導出 V2 版本
  - [ ] 保留 V1 向後兼容
- [ ] `backend/src/integrations/hybrid/factory.py`
  - [ ] `create_orchestrator_v2()` 工廠函數
  - [ ] 依賴注入配置

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/test_orchestrator_v2.py`
- [ ] 三種模式執行測試
- [ ] 向後兼容測試

### 驗證
- [ ] V2 Orchestrator 正確整合所有組件
- [ ] 三種模式都能正常執行
- [ ] V1 API 仍然可用

---

## S54-4: 整合測試與文檔 (5 pts)

### 測試
- [ ] `backend/tests/integration/hybrid/test_phase13_integration.py`
  - [ ] 端到端 Workflow 模式測試
  - [ ] 端到端 Chat 模式測試
  - [ ] 端到端 Hybrid 模式測試
  - [ ] 模式切換測試
  - [ ] 上下文同步測試
  - [ ] Tool Callback 完整流程測試
- [ ] 效能基準測試
  - [ ] 意圖分析延遲 < 100ms
  - [ ] 上下文同步延遲 < 100ms
  - [ ] Tool 執行開銷 < 50ms

### 文檔
- [ ] `docs/03-implementation/sprint-execution/sprint-54/README.md`
- [ ] `docs/guides/hybrid-orchestrator-v2-migration.md`
  - [ ] 遷移步驟
  - [ ] API 變更說明
  - [ ] 示範程式碼
- [ ] API 文檔更新

---

## Quality Gates

### 代碼品質
- [ ] `black .` 格式化通過
- [ ] `isort .` 導入排序通過
- [ ] `flake8 .` 無錯誤
- [ ] `mypy .` 類型檢查通過

### 測試品質
- [ ] 單元測試全部通過
- [ ] 整合測試全部通過
- [ ] 效能測試達標
- [ ] 覆蓋率報告生成

### 向後兼容
- [ ] V1 API 測試通過
- [ ] 現有功能回歸測試通過

---

## Phase 13 Completion Checklist

- [ ] Sprint 52 完成 (Intent Router)
- [ ] Sprint 53 完成 (Context Bridge)
- [ ] Sprint 54 完成 (HybridOrchestrator V2)
- [ ] Phase 13 整合測試通過
- [ ] 文檔完整
- [ ] 效能基準達標
- [ ] Code Review 完成

---

## Sprint Review Checklist

- [ ] 所有 User Stories 完成
- [ ] Phase 13 Demo 準備就緒
- [ ] 技術債務記錄
- [ ] Phase 14 準備確認

---

## Notes

```
Sprint 54 開始日期: ___________
Sprint 54 結束日期: ___________
實際完成點數: ___ / 35 pts

Phase 13 總計完成: ___ / 105 pts
```
