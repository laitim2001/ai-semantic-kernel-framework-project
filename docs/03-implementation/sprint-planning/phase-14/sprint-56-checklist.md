# Sprint 56 Checklist: Mode Switcher & HITL

## Pre-Sprint Setup

- [ ] 確認 Sprint 55 (Risk Assessment) 已完成
- [ ] 確認 Context Bridge 可用
- [ ] 建立 `backend/src/integrations/hybrid/switching/` 目錄結構

---

## S56-1: Mode Switcher 核心實現 (13 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/switching/__init__.py`
- [ ] `backend/src/integrations/hybrid/switching/models.py`
  - [ ] `SwitchTrigger` 資料類別
  - [ ] `SwitchResult` 資料類別
  - [ ] `ModeTransition` 資料類別
  - [ ] `MigratedState` 資料類別
- [ ] `backend/src/integrations/hybrid/switching/switcher.py`
  - [ ] `ModeSwitcher` 主類別
  - [ ] `should_switch()` 方法
  - [ ] `execute_switch()` 方法
  - [ ] `rollback_switch()` 方法
  - [ ] `_create_switch_checkpoint()` 方法
  - [ ] `_initialize_target_mode()` 方法
  - [ ] `_validate_switch()` 方法

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/switching/test_models.py`
- [ ] `backend/tests/unit/integrations/hybrid/switching/test_switcher.py`
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 模式切換成功執行
- [ ] 回滾機制正常運作
- [ ] 狀態正確保存和遷移

---

## S56-2: Trigger Detectors (8 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/switching/triggers/__init__.py`
- [ ] `backend/src/integrations/hybrid/switching/triggers/base.py`
  - [ ] `TriggerDetector` 抽象類
- [ ] `backend/src/integrations/hybrid/switching/triggers/complexity.py`
  - [ ] `ComplexityTriggerDetector` 類別
- [ ] `backend/src/integrations/hybrid/switching/triggers/user.py`
  - [ ] `UserRequestTriggerDetector` 類別
- [ ] `backend/src/integrations/hybrid/switching/triggers/failure.py`
  - [ ] `FailureTriggerDetector` 類別
- [ ] `backend/src/integrations/hybrid/switching/triggers/resource.py`
  - [ ] `ResourceTriggerDetector` 類別

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/switching/triggers/test_complexity.py`
- [ ] `backend/tests/unit/integrations/hybrid/switching/triggers/test_failure.py`
- [ ] 各種觸發場景測試

### 驗證
- [ ] 複雜度變化正確觸發切換
- [ ] 失敗後正確觸發診斷模式
- [ ] 用戶請求正確識別

---

## S56-3: State Migration (7 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/switching/migration/__init__.py`
- [ ] `backend/src/integrations/hybrid/switching/migration/state_migrator.py`
  - [ ] `StateMigrator` 類別
  - [ ] `migrate()` 方法
  - [ ] `_workflow_to_chat()` 方法
  - [ ] `_chat_to_workflow()` 方法
  - [ ] `_hybrid_migration()` 方法

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/switching/migration/test_state_migrator.py`
- [ ] Workflow → Chat 遷移測試
- [ ] Chat → Workflow 遷移測試
- [ ] 資料完整性測試

### 驗證
- [ ] 遷移後狀態完整
- [ ] 對話歷史正確轉換
- [ ] Tool 調用記錄保留

---

## S56-4: Enhanced HITL & API (7 pts)

### 檔案建立/修改
- [ ] `backend/src/api/v1/hybrid/switch_routes.py`
  - [ ] `POST /api/v1/hybrid/switch`
  - [ ] `GET /api/v1/hybrid/switch/status/{switch_id}`
  - [ ] `POST /api/v1/hybrid/switch/rollback`
- [ ] `backend/src/api/v1/hybrid/schemas.py` 更新
  - [ ] `SwitchRequest`
  - [ ] `SwitchResponse`
  - [ ] `SwitchStatusResponse`
  - [ ] `RollbackRequest`

### 整合
- [ ] 風險型審批流程整合
- [ ] WebSocket 切換事件通知 (可選)

### 測試
- [ ] `backend/tests/unit/api/v1/hybrid/test_switch_routes.py`
- [ ] API 端對端測試

### 驗證
- [ ] API 端點可訪問
- [ ] 手動切換成功
- [ ] 回滾 API 正常運作

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
- [ ] 模式切換成功率 > 99%

---

## Notes

```
Sprint 56 開始日期: ___________
Sprint 56 結束日期: ___________
實際完成點數: ___ / 35 pts
```
