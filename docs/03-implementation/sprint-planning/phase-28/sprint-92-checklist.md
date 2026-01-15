# Sprint 92 Checklist: Semantic Router + LLM Classifier

## 開發任務

### Story 92-1: 整合 Aurelio Semantic Router
- [ ] 創建 `semantic_router/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `router.py`
- [ ] 安裝 `semantic-router` 依賴
- [ ] 實現 `SemanticRouter` 類
- [ ] 實現 `route()` 方法
- [ ] 配置相似度閾值 (0.85)

### Story 92-2: 定義 10+ 語義路由
- [ ] 創建 `routes.py`
- [ ] 定義 incident 相關路由
  - [ ] incident_etl
  - [ ] incident_network
  - [ ] incident_performance
- [ ] 定義 request 相關路由
  - [ ] request_account
  - [ ] request_access
  - [ ] request_software
- [ ] 定義 change 相關路由
  - [ ] change_deployment
  - [ ] change_config
- [ ] 定義 query 相關路由
  - [ ] query_status
  - [ ] query_report
- [ ] 為每條路由添加 3-5 個範例語句

### Story 92-3: 實現 LLMClassifier
- [ ] 創建 `llm_classifier/` 目錄
- [ ] 創建 `__init__.py`
- [ ] 創建 `classifier.py`
- [ ] 實現 `LLMClassifier` 類
- [ ] 整合 Anthropic SDK
- [ ] 實現 `classify()` 方法
- [ ] 實現回應解析

### Story 92-4: 設計多任務 Prompt
- [ ] 創建 `prompts.py`
- [ ] 設計分類 Prompt
- [ ] 設計完整度評估 Prompt
- [ ] 設計多任務合併 Prompt
- [ ] 定義 JSON 輸出格式
- [ ] 測試 Prompt 穩定性

### Story 92-5: Semantic/LLM 單元測試
- [ ] 創建 `test_semantic_router.py`
- [ ] 創建 `test_llm_classifier.py`
- [ ] 編寫 Semantic 匹配測試
- [ ] 編寫 Semantic 閾值測試
- [ ] 編寫 LLM 分類測試 (Mock)
- [ ] 編寫 LLM 完整度測試 (Mock)
- [ ] 編寫錯誤處理測試

## 品質檢查

### 代碼品質
- [ ] Black 格式化通過
- [ ] isort 排序通過
- [ ] flake8 檢查通過
- [ ] mypy 類型檢查通過

### 測試
- [ ] 單元測試覆蓋率 > 90%
- [ ] 所有測試通過
- [ ] Semantic 層延遲 < 100ms
- [ ] LLM 層延遲 < 2000ms

### 文檔
- [ ] 函數 docstrings 完整
- [ ] Prompt 註釋完整
- [ ] 路由定義註釋完整

## 驗收標準

- [ ] Semantic Router 正常運作
- [ ] 10+ 語義路由定義完成
- [ ] LLM Classifier 正常運作
- [ ] 多任務 Prompt 穩定輸出
- [ ] 測試覆蓋率 > 90%

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 30
