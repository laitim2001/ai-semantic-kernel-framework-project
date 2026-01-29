# Sprint 100 Checklist: Swarm 數據模型 + 後端 API

## 開發任務

### Story 100-1: 定義 Swarm 核心數據模型
- [ ] 創建 `backend/src/integrations/swarm/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `models.py`
- [ ] 定義 `WorkerType` enum
- [ ] 定義 `WorkerStatus` enum
- [ ] 定義 `SwarmMode` enum
- [ ] 定義 `SwarmStatus` enum
- [ ] 定義 `ToolCallInfo` dataclass
- [ ] 定義 `ThinkingContent` dataclass
- [ ] 定義 `WorkerMessage` dataclass
- [ ] 定義 `WorkerExecution` dataclass
- [ ] 定義 `AgentSwarmStatus` dataclass
- [ ] 添加類型註解
- [ ] 編寫單元測試

### Story 100-2: 實現 SwarmTracker 狀態追蹤器
- [ ] 創建 `tracker.py`
- [ ] 實現 `SwarmTracker` 類
- [ ] 實現 `create_swarm()` 方法
- [ ] 實現 `get_swarm()` 方法
- [ ] 實現 `complete_swarm()` 方法
- [ ] 實現 `start_worker()` 方法
- [ ] 實現 `update_worker_progress()` 方法
- [ ] 實現 `add_worker_thinking()` 方法
- [ ] 實現 `add_worker_tool_call()` 方法
- [ ] 實現 `update_tool_call_result()` 方法
- [ ] 實現 `add_worker_message()` 方法
- [ ] 實現 `complete_worker()` 方法
- [ ] 實現 `get_worker()` 方法
- [ ] 實現 `calculate_overall_progress()` 方法
- [ ] 添加線程鎖
- [ ] 添加可選 Redis 支持

### Story 100-3: 建立 Swarm API 端點
- [ ] 創建 `backend/src/api/v1/swarm/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `schemas.py`
  - [ ] `ToolCallInfoSchema`
  - [ ] `ThinkingContentSchema`
  - [ ] `WorkerMessageSchema`
  - [ ] `WorkerSummarySchema`
  - [ ] `WorkerDetailResponse`
  - [ ] `SwarmStatusResponse`
  - [ ] `WorkerListResponse`
- [ ] 創建 `routes.py`
  - [ ] `GET /swarm/{swarm_id}`
  - [ ] `GET /swarm/{swarm_id}/workers/{worker_id}`
  - [ ] `GET /swarm/{swarm_id}/workers`
- [ ] 創建 `dependencies.py`
- [ ] 在主 router 中註冊

### Story 100-4: 整合 ClaudeCoordinator
- [ ] 創建 `swarm_integration.py`
- [ ] 實現 `SwarmIntegration` 類
- [ ] 實現 `on_coordination_started()` 方法
- [ ] 實現 `on_subtask_started()` 方法
- [ ] 實現 `on_subtask_progress()` 方法
- [ ] 實現 `on_tool_call()` 方法
- [ ] 實現 `on_thinking()` 方法
- [ ] 實現 `on_subtask_completed()` 方法
- [ ] 實現 `on_coordination_completed()` 方法
- [ ] 修改 `ClaudeCoordinator` 注入 `SwarmIntegration`
- [ ] 確保向後兼容

### Story 100-5: 單元測試與整合測試
- [ ] 創建 `backend/tests/unit/swarm/` 目錄
- [ ] 創建 `test_models.py`
  - [ ] 測試數據模型序列化
  - [ ] 測試狀態轉換
  - [ ] 測試邊界條件
- [ ] 創建 `test_tracker.py`
  - [ ] 測試創建 Swarm
  - [ ] 測試 Worker 生命週期
  - [ ] 測試進度計算
  - [ ] 測試並發安全
- [ ] 創建 `backend/tests/integration/swarm/` 目錄
- [ ] 創建 `test_api.py`
  - [ ] 測試 GET /swarm/{id}
  - [ ] 測試 GET /swarm/{id}/workers/{id}
  - [ ] 測試錯誤處理
- [ ] 創建 `test_coordinator_integration.py`
  - [ ] 測試完整執行流程

### Story 100-6: API 文檔與開發文檔
- [ ] 創建 `docs/api/swarm-api-reference.md`
- [ ] 編寫 API 端點說明
- [ ] 編寫請求/響應示例
- [ ] 編寫錯誤碼說明
- [ ] 創建開發指南文檔

## 品質檢查

### 代碼品質
- [ ] Black 格式化通過
- [ ] isort 排序通過
- [ ] flake8 檢查通過
- [ ] mypy 類型檢查通過

### 測試
- [ ] 單元測試覆蓋率 > 90%
- [ ] 所有測試通過
- [ ] 無 flaky tests

### 文檔
- [ ] 函數 docstrings 完整
- [ ] 類 docstrings 完整
- [ ] API 文檔完整

## 驗收標準

- [ ] 所有數據模型定義正確
- [ ] SwarmTracker 正常運作
- [ ] API 端點返回正確數據
- [ ] ClaudeCoordinator 整合成功
- [ ] 測試覆蓋率 > 90%

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 28
**開始日期**: 2026-01-30
