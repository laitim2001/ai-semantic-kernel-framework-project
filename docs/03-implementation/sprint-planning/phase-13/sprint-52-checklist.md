# Sprint 52 Checklist: Intent Router & Mode Detection

## Pre-Sprint Setup

- [ ] 確認 Phase 12 (Sprint 51) 已完成
- [ ] 確認 HybridOrchestrator 基礎架構可用
- [ ] 建立 `backend/src/integrations/hybrid/intent/` 目錄結構
- [ ] 更新 requirements.txt (如有新依賴)

---

## S52-1: Intent Router 核心實現 (13 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/intent/__init__.py`
- [ ] `backend/src/integrations/hybrid/intent/models.py`
  - [ ] `ExecutionMode` 枚舉
  - [ ] `IntentAnalysis` Pydantic 模型
  - [ ] `SessionContext` 資料類別
- [ ] `backend/src/integrations/hybrid/intent/router.py`
  - [ ] `IntentRouter` 主類別
  - [ ] `analyze_intent()` 方法
  - [ ] `should_switch_mode()` 方法
- [ ] `backend/src/integrations/hybrid/intent/classifiers/__init__.py`
- [ ] `backend/src/integrations/hybrid/intent/classifiers/base.py`
  - [ ] `BaseClassifier` 抽象類

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/intent/test_models.py`
- [ ] `backend/tests/unit/integrations/hybrid/intent/test_router.py`
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] `IntentRouter` 可正確實例化
- [ ] `analyze_intent()` 返回正確的 `IntentAnalysis`
- [ ] 不同輸入產生預期的模式分類

---

## S52-2: Mode Detection Algorithm (10 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/intent/classifiers/rule_based.py`
  - [ ] `RuleBasedClassifier` 類別
  - [ ] `WORKFLOW_KEYWORDS` 關鍵字列表
  - [ ] `CHAT_KEYWORDS` 關鍵字列表
  - [ ] `classify()` 方法
- [ ] `backend/src/integrations/hybrid/intent/classifiers/llm_based.py`
  - [ ] `LLMBasedClassifier` 類別 (可選 fallback)
- [ ] `backend/src/integrations/hybrid/intent/analyzers/__init__.py`
- [ ] `backend/src/integrations/hybrid/intent/analyzers/complexity.py`
  - [ ] `ComplexityAnalyzer` 類別
  - [ ] `ComplexityScore` 資料類別
- [ ] `backend/src/integrations/hybrid/intent/analyzers/multi_agent.py`
  - [ ] `MultiAgentDetector` 類別

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/intent/classifiers/test_rule_based.py`
- [ ] `backend/tests/unit/integrations/hybrid/intent/analyzers/test_complexity.py`
- [ ] 準確率測試套件 (目標 > 85%)

### 驗證
- [ ] 規則分類器對已知輸入正確分類
- [ ] 複雜度分析器產生合理的分數
- [ ] 多代理檢測器正確識別協作需求

---

## S52-3: API 整合與路由端點 (7 pts)

### 檔案建立/修改
- [ ] `backend/src/api/v1/hybrid/intent_routes.py`
  - [ ] `POST /api/v1/hybrid/analyze-intent`
  - [ ] `GET /api/v1/hybrid/modes`
- [ ] `backend/src/api/v1/hybrid/__init__.py` 更新路由註冊
- [ ] `backend/src/api/v1/hybrid/schemas.py`
  - [ ] `IntentAnalysisRequest`
  - [ ] `IntentAnalysisResponse`
  - [ ] `ExecutionModeResponse`

### 整合
- [ ] 更新 `HybridOrchestrator` 整合 `IntentRouter`
- [ ] 在 `execute()` 方法中調用意圖分析

### 測試
- [ ] `backend/tests/unit/api/v1/hybrid/test_intent_routes.py`
- [ ] API 端對端測試

### 驗證
- [ ] API 端點可訪問
- [ ] 請求/響應格式正確
- [ ] OpenAPI 文檔自動生成

---

## S52-4: 整合測試與文檔 (5 pts)

### 測試
- [ ] `backend/tests/integration/hybrid/test_intent_integration.py`
  - [ ] 測試完整流程：輸入 → 分類 → 執行模式
  - [ ] 邊界情況：空輸入、超長輸入、特殊字符
  - [ ] 上下文影響測試
- [ ] 效能測試
  - [ ] 分類延遲 < 50ms (無 LLM)
  - [ ] 分類延遲 < 500ms (含 LLM fallback)

### 文檔
- [ ] `docs/03-implementation/sprint-execution/sprint-52/README.md`
- [ ] API 使用範例文檔
- [ ] 架構決策記錄 (ADR)

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
- [ ] 覆蓋率報告生成

### 文檔品質
- [ ] README 更新
- [ ] API 文檔完整
- [ ] 代碼註釋充足

---

## Sprint Review Checklist

- [ ] 所有 User Stories 完成
- [ ] Demo 準備就緒
- [ ] 技術債務記錄
- [ ] 下一 Sprint 依賴項確認

---

## Notes

```
Sprint 52 開始日期: ___________
Sprint 52 結束日期: ___________
實際完成點數: ___ / 35 pts
```
