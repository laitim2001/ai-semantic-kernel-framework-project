# Sprint 55 Checklist: Risk Assessment Engine

## Pre-Sprint Setup

- [ ] 確認 Phase 13 已完成
- [ ] 確認 ApprovalHook 可用
- [ ] 建立 `backend/src/integrations/hybrid/risk/` 目錄結構

---

## S55-1: Risk Assessment Engine 核心 (12 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/risk/__init__.py`
- [ ] `backend/src/integrations/hybrid/risk/models.py`
  - [ ] `RiskLevel` 枚舉
  - [ ] `RiskFactor` 資料類別
  - [ ] `RiskAssessment` 資料類別
  - [ ] `OperationRisk`, `ContextRisk`, `PatternRisk` 資料類別
  - [ ] `RiskConfig` 配置類別
- [ ] `backend/src/integrations/hybrid/risk/engine.py`
  - [ ] `RiskAssessmentEngine` 主類別
  - [ ] `assess()` 方法
- [ ] `backend/src/integrations/hybrid/risk/scoring/scorer.py`
  - [ ] `RiskScorer` 類別
  - [ ] `calculate()` 方法
  - [ ] 權重配置

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/risk/test_models.py`
- [ ] `backend/tests/unit/integrations/hybrid/risk/test_engine.py`
- [ ] 測試覆蓋率 > 90%

### 驗證
- [ ] 風險評估正確返回分數和等級
- [ ] 不同輸入產生合理的風險評估

---

## S55-2: Operation Analyzer (8 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/risk/analyzers/__init__.py`
- [ ] `backend/src/integrations/hybrid/risk/analyzers/base.py`
  - [ ] `BaseAnalyzer` 抽象類
- [ ] `backend/src/integrations/hybrid/risk/analyzers/operation.py`
  - [ ] `OperationAnalyzer` 類別
  - [ ] `TOOL_BASE_RISK` 風險矩陣
  - [ ] `SENSITIVE_PATHS` 敏感路徑列表
  - [ ] `DANGEROUS_COMMANDS` 危險命令列表
  - [ ] `analyze()` 方法
  - [ ] `_analyze_parameters()` 方法
  - [ ] `_analyze_scope()` 方法
  - [ ] `_detect_dangerous_patterns()` 方法

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/risk/analyzers/test_operation.py`
- [ ] 各種 Tool 類型測試
- [ ] 敏感路徑檢測測試
- [ ] 危險命令檢測測試

### 驗證
- [ ] Read 操作風險 < Write 操作風險
- [ ] 敏感路徑正確被檢測
- [ ] 危險命令正確被標記

---

## S55-3: Context Evaluator & Pattern Detector (5 pts)

### 檔案建立
- [ ] `backend/src/integrations/hybrid/risk/analyzers/context.py`
  - [ ] `ContextEvaluator` 類別
  - [ ] `evaluate()` 方法
  - [ ] `_evaluate_user_trust()` 方法
  - [ ] `_evaluate_environment()` 方法
  - [ ] `_evaluate_session_state()` 方法
- [ ] `backend/src/integrations/hybrid/risk/analyzers/pattern.py`
  - [ ] `PatternDetector` 類別
  - [ ] `detect()` 方法
  - [ ] `_detect_frequency_anomaly()` 方法
  - [ ] `_detect_behavior_deviation()` 方法
  - [ ] `_detect_escalation_pattern()` 方法

### 測試
- [ ] `backend/tests/unit/integrations/hybrid/risk/analyzers/test_context.py`
- [ ] `backend/tests/unit/integrations/hybrid/risk/analyzers/test_pattern.py`

### 驗證
- [ ] 不同環境產生不同風險評分
- [ ] 異常頻率被正確檢測
- [ ] 升級模式被正確識別

---

## S55-4: API 與 ApprovalHook 整合 (5 pts)

### 檔案建立/修改
- [ ] `backend/src/api/v1/hybrid/risk_routes.py`
  - [ ] `POST /api/v1/hybrid/risk/assess`
  - [ ] `GET /api/v1/hybrid/risk/config`
  - [ ] `PUT /api/v1/hybrid/risk/config`
- [ ] 修改 `backend/src/integrations/claude_sdk/hooks/approval.py`
  - [ ] 整合 `RiskAssessmentEngine`
  - [ ] 基於風險等級決定審批需求

### 測試
- [ ] `backend/tests/unit/api/v1/hybrid/test_risk_routes.py`
- [ ] 整合測試

### 驗證
- [ ] API 端點可訪問
- [ ] ApprovalHook 正確使用風險評估

---

## Quality Gates

### 代碼品質
- [ ] `black .` 格式化通過
- [ ] `isort .` 導入排序通過
- [ ] `flake8 .` 無錯誤
- [ ] `mypy .` 類型檢查通過

### 測試品質
- [ ] 單元測試全部通過
- [ ] 覆蓋率 > 85%

---

## Notes

```
Sprint 55 開始日期: ___________
Sprint 55 結束日期: ___________
實際完成點數: ___ / 30 pts
```
