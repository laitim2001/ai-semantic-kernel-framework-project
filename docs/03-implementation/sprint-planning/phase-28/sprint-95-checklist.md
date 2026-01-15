# Sprint 95 Checklist: InputGateway + SourceHandlers

## 開發任務

### Story 95-1: 實現 InputGateway 主類
- [ ] 創建 `input_gateway/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `gateway.py`
- [ ] 實現 `InputGateway` 類
- [ ] 實現 `process()` 方法
- [ ] 實現 `_identify_source()` 方法
- [ ] 整合 SourceHandlers
- [ ] 整合 BusinessIntentRouter

### Story 95-2: 實現 BaseSourceHandler
- [ ] 創建 `source_handlers/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `base_handler.py`
- [ ] 定義 `BaseSourceHandler` ABC
- [ ] 定義 `process()` 抽象方法
- [ ] 實現通用輔助方法

### Story 95-3: 實現 ServiceNowHandler
- [ ] 創建 `servicenow_handler.py`
- [ ] 實現 `ServiceNowHandler` 類
- [ ] 定義類別映射表 (CATEGORY_MAPPING)
  - [ ] incident/hardware → hardware_failure
  - [ ] incident/software → software_issue
  - [ ] incident/network → network_failure
  - [ ] request/account → account_request
  - [ ] request/access → access_request
  - [ ] change/standard → standard_change
- [ ] 整合 PatternMatcher (當 subcategory 不足)
- [ ] 確保延遲 < 10ms

### Story 95-4: 實現 PrometheusHandler
- [ ] 創建 `prometheus_handler.py`
- [ ] 實現 `PrometheusHandler` 類
- [ ] 定義告警映射
  - [ ] *_high_cpu_* → performance_issue
  - [ ] *_memory_* → memory_issue
  - [ ] *_disk_* → disk_issue
  - [ ] *_down_* → service_down
- [ ] 實現告警標籤提取

### Story 95-5: 實現 UserInputHandler
- [ ] 創建 `user_input_handler.py`
- [ ] 實現 `UserInputHandler` 類
- [ ] 整合完整三層路由
- [ ] 實現格式標準化

### Story 95-6: 實現 SchemaValidator
- [ ] 創建 `schema_validator.py`
- [ ] 實現 `SchemaValidator` 類
- [ ] 定義 ServiceNow Schema
- [ ] 定義 Prometheus Schema
- [ ] 實現 `validate()` 方法
- [ ] 實現明確的錯誤訊息

## 品質檢查

### 代碼品質
- [ ] Black 格式化通過
- [ ] isort 排序通過
- [ ] flake8 檢查通過
- [ ] mypy 類型檢查通過

### 測試
- [ ] 單元測試覆蓋率 > 85%
- [ ] 所有測試通過
- [ ] 系統來源延遲 < 10ms

### 文檔
- [ ] InputGateway docstrings 完整
- [ ] SourceHandler docstrings 完整
- [ ] 映射表註釋完整

## 驗收標準

- [ ] InputGateway 正確分流
- [ ] ServiceNowHandler 簡化路徑正確
- [ ] PrometheusHandler 正常運作
- [ ] UserInputHandler 調用完整流程
- [ ] Schema 驗證正確
- [ ] 系統來源延遲 < 10ms

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 25
