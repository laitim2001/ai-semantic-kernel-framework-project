# Sprint 93 Checklist: BusinessIntentRouter 整合 + 完整度

## 開發任務

### Story 93-1: 實現 BusinessIntentRouter 協調器
- [ ] 創建 `router.py`
- [ ] 實現 `BusinessIntentRouter` 類
- [ ] 整合 PatternMatcher
- [ ] 整合 SemanticRouter
- [ ] 整合 LLMClassifier
- [ ] 實現三層路由邏輯
- [ ] 實現置信度/相似度閾值判斷
- [ ] 實現 `_build_decision()` 方法
- [ ] 實現延遲追蹤

### Story 93-2: 實現 CompletenessChecker
- [ ] 創建 `completeness/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `checker.py`
- [ ] 實現 `CompletenessChecker` 類
- [ ] 實現 `check()` 方法
- [ ] 實現欄位提取邏輯
- [ ] 實現完整度分數計算

### Story 93-3: 定義完整度規則
- [ ] 創建 `rules.py`
- [ ] 定義 `CompletenessRule` dataclass
- [ ] 定義 incident 規則 (閾值 60%)
  - [ ] affected_system
  - [ ] symptom_type
  - [ ] urgency
- [ ] 定義 request 規則 (閾值 60%)
  - [ ] request_type
  - [ ] requester
  - [ ] justification
- [ ] 定義 change 規則 (閾值 70%)
  - [ ] change_type
  - [ ] target_system
  - [ ] schedule
- [ ] 定義 query 規則 (閾值 50%)
  - [ ] query_type

### Story 93-4: 整合測試
- [ ] 創建 `test_business_intent_router.py`
- [ ] 編寫 Pattern 直接匹配測試
- [ ] 編寫降級到 Semantic 測試
- [ ] 編寫降級到 LLM 測試
- [ ] 編寫完整度計算測試
- [ ] 編寫缺失欄位識別測試
- [ ] 編寫延遲統計測試

### Story 93-5: 性能基準測試
- [ ] 創建 `test_router_performance.py`
- [ ] 測試 Pattern 層 P95 延遲
- [ ] 測試 Semantic 層 P95 延遲
- [ ] 測試 LLM 層 P95 延遲
- [ ] 測試整體 P95 延遲 (無 LLM)

## 品質檢查

### 代碼品質
- [ ] Black 格式化通過
- [ ] isort 排序通過
- [ ] flake8 檢查通過
- [ ] mypy 類型檢查通過

### 測試
- [ ] 單元測試覆蓋率 > 90%
- [ ] 整合測試通過
- [ ] 性能基準測試通過

### 文檔
- [ ] BusinessIntentRouter docstrings 完整
- [ ] CompletenessChecker docstrings 完整
- [ ] 完整度規則註釋完整

## 驗收標準

- [ ] 三層路由正確運作
- [ ] 完整度檢查正確
- [ ] 缺失欄位識別正確
- [ ] Pattern 層延遲 < 10ms
- [ ] Semantic 層延遲 < 100ms
- [ ] LLM 層延遲 < 2000ms
- [ ] 整體 P95 延遲 < 500ms (無 LLM)

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 25
