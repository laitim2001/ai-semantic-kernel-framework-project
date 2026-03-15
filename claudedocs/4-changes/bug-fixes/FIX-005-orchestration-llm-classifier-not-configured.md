# FIX-005: Orchestration LLM Classifier 未正確配置 LLM 服務

**修復日期**: 2026-03-14
**嚴重程度**: 高
**影響範圍**: Three-tier Intent Routing — Layer 3 LLM 分類器
**相關 Sprint**: Sprint 128 (LLMServiceProtocol 重構) 遺留問題
**狀態**: ✅ 已修復

---

## 問題描述

### 症狀
- Orchestration Intent Routing 的 Layer 3 (LLM Classifier) 始終回傳 `unknown`
- Routing Decision 顯示 `Reasoning: LLM classifier unavailable: no service configured`
- Confidence 為 `0%`，即使 Azure OpenAI API 連線完全正常

### 重現步驟
1. 啟動 Backend 服務
2. 進入 `/chat` 頁面
3. 發送任何訊息觸發 Orchestration
4. 觀察 Orchestration 面板中 Routing Decision 顯示 `LLM` 層級但 intent 為 `unknown`

### 預期行為
- Layer 3 LLM Classifier 應使用已配置的 Azure OpenAI 服務進行 intent 分類
- 回傳有效的 intent category（INCIDENT / REQUEST / CHANGE / QUERY）和合理的 confidence score

### 實際行為
- LLM Classifier 收到 `llm_service=None`，進入 graceful degradation 路徑
- 回傳 `ITIntentCategory.UNKNOWN`、`confidence=0.0`

---

## 根本原因分析

### 原因
Sprint 128 將 LLM Classifier 從直接使用 API key 重構為 `LLMServiceProtocol` 介面，但 `intent_routes.py` 的 `get_router()` 函式未同步更新。

**具體問題**：`intent_routes.py:111-116` 呼叫 `create_router(llm_api_key=anthropic_key)`，但 `create_router()` 在 Sprint 128 後已不再消費 `llm_api_key` 參數，改為使用 `llm_service` 參數。`llm_api_key` 成為一個 **dead parameter**（被接受但從未使用）。

### 呼叫鏈分析

```
目前的錯誤呼叫鏈:
intent_routes.py:111 → create_router(llm_api_key=anthropic_key)
  → router.py:566 → LLMClassifier(llm_service=None)  ← llm_service 未傳入！
    → classifier.py:106 → self._llm_service is None
      → 回傳 "LLM classifier unavailable: no service configured"

正確的呼叫鏈:
intent_routes.py → create_router_with_llm(config=config)
  → router.py:601 → LLMServiceFactory.create()
    → factory.py → _detect_provider() 偵測到 AZURE_OPENAI_ENDPOINT → "azure"
      → AzureOpenAILLMService(endpoint, api_key, deployment_name)
        → LLMClassifier(llm_service=azure_service) ← 正確注入！
```

### 相關代碼

**Bug 位置** — `backend/src/api/v1/orchestration/intent_routes.py:68-150`
```python
# ❌ 問題：使用已棄用的 llm_api_key 參數
_router_instance = create_router(
    pattern_rules_path=rules_path,
    semantic_routes=semantic_routes,
    llm_api_key=anthropic_key,    # ← 此參數已不被消費
    config=config,
)
```

**Dead parameter** — `backend/src/integrations/orchestration/intent_router/router.py:532-577`
```python
def create_router(
    ...
    llm_service: Optional[Any] = None,    # ← Sprint 128 新增，正確參數
    llm_api_key: Optional[str] = None,    # ← 已棄用，不再使用
    ...
):
    # Sprint 128: 只使用 llm_service
    llm_classifier = LLMClassifier(llm_service=llm_service)  # llm_api_key 被忽略
```

**正確的工廠函式** — `backend/src/integrations/orchestration/intent_router/router.py:580-609`
```python
def create_router_with_llm(config=None):
    """Production factory: auto-creates LLM service from environment."""
    llm_service = LLMServiceFactory.create(use_cache=True, cache_ttl=1800)
    return create_router(llm_service=llm_service, config=config)
```

### 影響分析
- **直接影響**: Layer 3 LLM 分類完全失效，所有無法被 Pattern/Semantic 匹配的 input 回傳 UNKNOWN
- **間接影響**: Risk Assessment 因 `unknown` intent 而預設為 MEDIUM risk，不準確
- **用戶影響**: Orchestration 面板顯示無意義的分類結果

---

## 修復方案

### 解決方法
將 `intent_routes.py` 的 `get_router()` 函式改為使用 `create_router_with_llm()` 工廠函式，此函式會：
1. 透過 `LLMServiceFactory` 自動偵測環境變數中的 LLM provider（Azure OpenAI）
2. 建立正確的 `AzureOpenAILLMService` 實例
3. 注入到 `LLMClassifier` 中

### 修改檔案

| 檔案 | 變更 |
|------|------|
| `backend/src/api/v1/orchestration/intent_routes.py` | 重構 `get_router()` 使用 `create_router_with_llm()` |

### 修改內容

1. **更新 import**：新增 `create_router_with_llm`
2. **重構 `get_router()`**：
   - 移除已棄用的 `llm_api_key` 傳遞邏輯
   - 使用 `create_router_with_llm()` 自動從環境變數建立 LLM 服務
   - 保留 pattern rules 和 semantic routes 的配置
   - 保留 Azure OpenAI semantic router encoder 配置

---

## 測試驗證

### 驗證步驟
1. 重啟 Backend 服務
2. 檢查 Backend 日誌確認 `LLM service created via LLMServiceFactory` 訊息
3. 透過 API 測試 intent classification:
   ```bash
   curl -X POST http://localhost:8000/api/v1/orchestration/intent/classify \
     -H "Content-Type: application/json" \
     -d '{"text": "ETL Pipeline failed", "source": "user"}'
   ```
4. 驗證回傳的 intent 不再是 `unknown`，confidence > 0
5. 在前端 `/chat` 頁面發送訊息，確認 Orchestration 面板正確顯示分類結果

### 預期結果
- Layer 3 LLM Classifier 使用 Azure OpenAI gpt-5.2 進行分類
- 回傳有效的 intent category 和合理的 confidence score
- Orchestration 面板顯示正確的路由決策

---

## 相關文件

| 文件 | 關聯 |
|------|------|
| `backend/src/api/v1/orchestration/intent_routes.py` | Bug 所在位置 |
| `backend/src/integrations/orchestration/intent_router/router.py` | 工廠函式定義 |
| `backend/src/integrations/orchestration/intent_router/llm_classifier/classifier.py` | 錯誤訊息來源 |
| `backend/src/integrations/llm/factory.py` | LLMServiceFactory 自動偵測邏輯 |
| `backend/src/integrations/llm/azure_openai.py` | AzureOpenAILLMService 實作 |
