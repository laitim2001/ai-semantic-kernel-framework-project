# Sprint 96 Checklist: RiskAssessor + Policies

## 開發任務

### Story 96-1: 實現 RiskAssessor 核心
- [ ] 創建 `risk_assessor/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `assessor.py`
- [ ] 定義 `RiskLevel` enum
- [ ] 定義 `RiskAssessment` dataclass
- [ ] 實現 `RiskAssessor` 類
- [ ] 實現 `assess()` 方法
- [ ] 實現 `_calculate_score()` 方法
- [ ] 實現 `_adjust_for_context()` 方法

### Story 96-2: 定義風險評估策略
- [ ] 創建 `policies.py`
- [ ] 定義 `RiskPolicy` dataclass
- [ ] 定義 `RiskPolicies` 類
- [ ] 定義 Incident 策略
  - [ ] system_down → critical
  - [ ] etl_failure → high
  - [ ] performance_issue → medium
- [ ] 定義 Request 策略
  - [ ] account_request → medium
  - [ ] access_request → high
- [ ] 定義 Change 策略
  - [ ] emergency_change → critical
  - [ ] standard_change → medium
- [ ] 定義 Query 策略
  - [ ] * → low
- [ ] 實現 `get_policy()` 方法

### Story 96-3: 整合 ITIntent → 風險等級映射
- [ ] 實現 `_calculate_risk_level()` 方法
- [ ] 實現上下文調整邏輯
  - [ ] 生產環境提升風險
  - [ ] 週末提升風險
  - [ ] 緊急情況處理
- [ ] 實現 `_elevate_risk()` 方法
- [ ] 實現 `_get_approval_type()` 方法

### Story 96-4: 風險評估單元測試
- [ ] 創建 `test_risk_assessor.py`
- [ ] 編寫各意圖類型風險評估測試
- [ ] 編寫上下文調整測試
- [ ] 編寫策略覆蓋測試
- [ ] 編寫邊界條件測試

### Story 96-5: API 路由實現
- [ ] 創建 `api/v1/orchestration/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `routes.py`
- [ ] 創建 `intent_routes.py`
- [ ] 實現 `POST /intent/classify` 端點
- [ ] 實現 `POST /intent/test` 端點
- [ ] 定義 Pydantic 請求/回應模型
- [ ] 實現錯誤處理

## 品質檢查

### 代碼品質
- [ ] Black 格式化通過
- [ ] isort 排序通過
- [ ] flake8 檢查通過
- [ ] mypy 類型檢查通過

### 測試
- [ ] 單元測試覆蓋率 > 90%
- [ ] 所有測試通過
- [ ] API 測試通過

### 文檔
- [ ] RiskAssessor docstrings 完整
- [ ] RiskPolicies docstrings 完整
- [ ] API 端點 docstrings 完整

## 驗收標準

- [ ] 風險評估邏輯正確
- [ ] 策略矩陣完整
- [ ] 上下文調整正確
- [ ] API 路由正常工作
- [ ] OpenAPI 文檔正確生成

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 25
