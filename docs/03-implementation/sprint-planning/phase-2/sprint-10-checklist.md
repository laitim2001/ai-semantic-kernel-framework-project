# Sprint 10 Checklist: 動態規劃引擎 (Dynamic Planning & Autonomous Decision)

**Sprint 目標**: 實現自主規劃和決策能力，讓 Agent 能夠動態分解任務並自主決策
**週期**: Week 21-22
**總點數**: 42 點
**Phase 2 功能**: P2-F8 Dynamic Planning + P2-F9 Autonomous Decision + P2-F10 Trial-and-Error
**狀態**: ⏳ 待開發 (0/42 點)

---

## 快速驗證命令

```bash
# 驗證規劃模組
python -c "from src.domain.orchestration.planning import TaskDecomposer, DynamicPlanner; print('OK')"

# 驗證規劃 API
curl http://localhost:8000/api/v1/planning/status

# 分解任務
curl -X POST http://localhost:8000/api/v1/planning/decompose \
  -H "Content-Type: application/json" \
  -d '{"task_description": "實現用戶認證系統", "strategy": "hybrid"}'

# 運行規劃測試
cd backend && pytest tests/unit/test_planning*.py tests/unit/test_decision*.py -v
```

---

## S10-1: TaskDecomposer 任務分解器 (8 點) ⏳

### 核心分解器 (src/domain/orchestration/planning/)
- [ ] 創建 `task_decomposer.py`
  - [ ] TaskPriority 枚舉
    - [ ] CRITICAL - 關鍵
    - [ ] HIGH - 高
    - [ ] MEDIUM - 中
    - [ ] LOW - 低
  - [ ] TaskStatus 枚舉
    - [ ] PENDING - 待處理
    - [ ] READY - 可執行
    - [ ] IN_PROGRESS - 進行中
    - [ ] COMPLETED - 已完成
    - [ ] FAILED - 失敗
    - [ ] BLOCKED - 被阻塞
  - [ ] DependencyType 枚舉
    - [ ] FINISH_TO_START - 完成後開始
    - [ ] START_TO_START - 同時開始
    - [ ] FINISH_TO_FINISH - 同時完成
    - [ ] DATA_DEPENDENCY - 數據依賴
  - [ ] SubTask 數據類
    - [ ] id 屬性
    - [ ] parent_task_id 屬性
    - [ ] name 屬性
    - [ ] description 屬性
    - [ ] priority 屬性
    - [ ] status 屬性
    - [ ] assigned_agent_id 屬性
    - [ ] dependencies 屬性
    - [ ] dependency_type 屬性
    - [ ] estimated_duration_minutes 屬性
    - [ ] actual_duration_minutes 屬性
    - [ ] inputs 屬性
    - [ ] outputs 屬性
    - [ ] metadata 屬性
  - [ ] DecompositionResult 數據類
    - [ ] task_id 屬性
    - [ ] original_task 屬性
    - [ ] subtasks 屬性
    - [ ] execution_order 屬性
    - [ ] estimated_total_duration 屬性
    - [ ] confidence_score 屬性
    - [ ] decomposition_strategy 屬性
  - [ ] TaskDecomposer 類
    - [ ] __init__() 初始化方法
    - [ ] decompose() 分解任務
    - [ ] _decompose_hierarchical() 階層式分解
    - [ ] _decompose_sequential() 順序式分解
    - [ ] _decompose_parallel() 並行式分解
    - [ ] _decompose_hybrid() 混合式分解
    - [ ] _build_decomposition_prompt() 構建提示
    - [ ] _parse_decomposition_response() 解析響應
    - [ ] _analyze_execution_order() 分析執行順序
    - [ ] _estimate_total_duration() 估算總時間
    - [ ] _calculate_confidence() 計算信心分數
    - [ ] refine_decomposition() 精煉分解結果

### 驗證標準
- [ ] 支援 4 種分解策略
- [ ] 正確識別任務依賴
- [ ] 計算合理的執行順序
- [ ] 信心分數準確反映分解質量
- [ ] 單元測試覆蓋率 > 85%

---

## S10-2: DynamicPlanner 動態規劃器 (8 點) ⏳

### 動態規劃 (src/domain/orchestration/planning/)
- [ ] 創建 `dynamic_planner.py`
  - [ ] PlanStatus 枚舉
    - [ ] DRAFT - 草稿
    - [ ] APPROVED - 已批准
    - [ ] EXECUTING - 執行中
    - [ ] PAUSED - 暫停
    - [ ] COMPLETED - 完成
    - [ ] FAILED - 失敗
    - [ ] REPLANNING - 重新規劃中
  - [ ] PlanEvent 枚舉
    - [ ] TASK_STARTED - 任務開始
    - [ ] TASK_COMPLETED - 任務完成
    - [ ] TASK_FAILED - 任務失敗
    - [ ] RESOURCE_UNAVAILABLE - 資源不可用
    - [ ] NEW_INFORMATION - 新信息
    - [ ] USER_INTERVENTION - 用戶介入
    - [ ] DEADLINE_APPROACHING - 截止時間逼近
  - [ ] PlanAdjustment 數據類
    - [ ] id 屬性
    - [ ] plan_id 屬性
    - [ ] trigger_event 屬性
    - [ ] original_state 屬性
    - [ ] new_state 屬性
    - [ ] reason 屬性
    - [ ] approved 屬性
    - [ ] approved_by 屬性
  - [ ] ExecutionPlan 數據類
    - [ ] id 屬性
    - [ ] name 屬性
    - [ ] description 屬性
    - [ ] goal 屬性
    - [ ] decomposition 屬性
    - [ ] status 屬性
    - [ ] current_phase 屬性
    - [ ] progress_percentage 屬性
    - [ ] adjustments 屬性
    - [ ] deadline 屬性
  - [ ] DynamicPlanner 類
    - [ ] __init__() 初始化方法
    - [ ] create_plan() 建立計劃
    - [ ] approve_plan() 批准計劃
    - [ ] execute_plan() 執行計劃
    - [ ] _execute_phase() 執行階段
    - [ ] _should_replan() 判斷重新規劃
    - [ ] _replan() 重新規劃
    - [ ] _analyze_situation() 分析情況
    - [ ] _apply_adjustment() 應用調整
    - [ ] _start_monitoring() 開始監控
    - [ ] _stop_monitoring() 停止監控
    - [ ] _emit_event() 發送事件
    - [ ] on_event() 註冊事件處理器
    - [ ] get_plan_status() 獲取計劃狀態

### 驗證標準
- [ ] 支援計劃建立和執行
- [ ] 實時進度追蹤
- [ ] 自動重新規劃
- [ ] 事件通知機制
- [ ] 人工審批流程

---

## S10-3: AutonomousDecisionEngine 自主決策引擎 (8 點) ⏳

### 決策引擎 (src/domain/orchestration/planning/)
- [ ] 創建 `decision_engine.py`
  - [ ] DecisionType 枚舉
    - [ ] ROUTING - 路由決策
    - [ ] RESOURCE - 資源分配
    - [ ] ERROR_HANDLING - 錯誤處理
    - [ ] PRIORITY - 優先級調整
    - [ ] ESCALATION - 升級決策
    - [ ] OPTIMIZATION - 優化決策
  - [ ] DecisionConfidence 枚舉
    - [ ] HIGH - 高信心 (>80%)
    - [ ] MEDIUM - 中信心 (50-80%)
    - [ ] LOW - 低信心 (<50%)
  - [ ] DecisionOption 數據類
    - [ ] id 屬性
    - [ ] name 屬性
    - [ ] description 屬性
    - [ ] pros 屬性
    - [ ] cons 屬性
    - [ ] risk_level 屬性
    - [ ] estimated_impact 屬性
    - [ ] prerequisites 屬性
  - [ ] Decision 數據類
    - [ ] id 屬性
    - [ ] decision_type 屬性
    - [ ] situation 屬性
    - [ ] options_considered 屬性
    - [ ] selected_option 屬性
    - [ ] confidence 屬性
    - [ ] reasoning 屬性
    - [ ] risk_assessment 屬性
    - [ ] human_approved 屬性
    - [ ] execution_result 屬性
  - [ ] AutonomousDecisionEngine 類
    - [ ] __init__() 初始化方法
    - [ ] make_decision() 做出決策
    - [ ] _expand_options() 擴展選項
    - [ ] _evaluate_options() 評估選項
    - [ ] _select_best_option() 選擇最佳選項
    - [ ] _calculate_confidence() 計算信心
    - [ ] _assess_risk() 評估風險
    - [ ] _categorize_risk() 分類風險
    - [ ] _generate_mitigations() 生成緩解建議
    - [ ] explain_decision() 解釋決策
    - [ ] add_rule() 添加規則
    - [ ] apply_rules() 應用規則

### 驗證標準
- [ ] 支援多選項評估
- [ ] 風險評估準確
- [ ] 信心計算合理
- [ ] 決策可解釋
- [ ] 支援自定義規則

---

## S10-4: TrialAndErrorEngine 試錯學習引擎 (5 點) ⏳

### 試錯引擎 (src/domain/orchestration/planning/)
- [ ] 創建 `trial_error.py`
  - [ ] TrialStatus 枚舉
    - [ ] PENDING - 待執行
    - [ ] RUNNING - 執行中
    - [ ] SUCCESS - 成功
    - [ ] FAILURE - 失敗
    - [ ] TIMEOUT - 超時
  - [ ] LearningType 枚舉
    - [ ] PARAMETER_TUNING - 參數調整
    - [ ] STRATEGY_SWITCH - 策略切換
    - [ ] ERROR_PATTERN - 錯誤模式
    - [ ] SUCCESS_PATTERN - 成功模式
  - [ ] Trial 數據類
    - [ ] id 屬性
    - [ ] task_id 屬性
    - [ ] attempt_number 屬性
    - [ ] parameters 屬性
    - [ ] strategy 屬性
    - [ ] status 屬性
    - [ ] result 屬性
    - [ ] error 屬性
    - [ ] duration_ms 屬性
  - [ ] LearningInsight 數據類
    - [ ] id 屬性
    - [ ] learning_type 屬性
    - [ ] pattern 屬性
    - [ ] confidence 屬性
    - [ ] evidence 屬性
    - [ ] recommendation 屬性
  - [ ] TrialAndErrorEngine 類
    - [ ] __init__() 初始化方法
    - [ ] execute_with_retry() 帶重試執行
    - [ ] _analyze_and_adjust() 分析並調整
    - [ ] _check_known_patterns() 檢查已知模式
    - [ ] _simple_param_adjustment() 簡單參數調整
    - [ ] _record_success() 記錄成功
    - [ ] _record_error_pattern() 記錄錯誤模式
    - [ ] _extract_error_keywords() 提取錯誤關鍵詞
    - [ ] learn_from_history() 從歷史學習
    - [ ] _analyze_success_patterns() 分析成功模式
    - [ ] _analyze_failure_patterns() 分析失敗模式
    - [ ] _analyze_parameter_effects() 分析參數效果
    - [ ] get_recommendations() 獲取建議

### 驗證標準
- [ ] 支援自動重試
- [ ] 錯誤模式識別
- [ ] 自動參數調整
- [ ] 學習洞察提取
- [ ] 建議生成

---

## S10-5: Planning API 路由 (5 點) ⏳

### API 路由 (src/api/v1/planning/)
- [ ] 創建 `routes.py`
  - [ ] POST /planning/decompose - 分解任務
  - [ ] POST /planning/decompose/{task_id}/refine - 精煉分解
  - [ ] POST /planning/plans - 建立計劃
  - [ ] GET /planning/plans/{plan_id} - 獲取計劃
  - [ ] POST /planning/plans/{plan_id}/approve - 批准計劃
  - [ ] POST /planning/plans/{plan_id}/execute - 執行計劃
  - [ ] GET /planning/plans/{plan_id}/status - 獲取狀態
  - [ ] POST /planning/plans/{plan_id}/pause - 暫停計劃
  - [ ] POST /planning/decisions - 請求決策
  - [ ] GET /planning/decisions/{decision_id}/explain - 解釋決策
  - [ ] POST /planning/trial - 試錯執行
  - [ ] GET /planning/trial/insights - 獲取學習洞察
  - [ ] GET /planning/recommendations - 獲取建議

### 請求/響應 Schema
- [ ] 創建 `schemas.py`
  - [ ] DecomposeTaskRequest
  - [ ] DecompositionResponse
  - [ ] SubTaskResponse
  - [ ] CreatePlanRequest
  - [ ] PlanResponse
  - [ ] DecisionRequest
  - [ ] DecisionResponse
  - [ ] TrialRequest
  - [ ] TrialResponse
  - [ ] InsightResponse

### 驗證標準
- [ ] 任務分解 API 完整
- [ ] 計劃管理 API 完整
- [ ] 決策 API 完整
- [ ] 試錯執行 API 完整
- [ ] API 文檔完整

---

## 測試完成 ⏳

### 單元測試
- [ ] test_task_decomposer.py
  - [ ] test_decompose_task
  - [ ] test_hierarchical_decomposition
  - [ ] test_sequential_decomposition
  - [ ] test_parallel_decomposition
  - [ ] test_execution_order
  - [ ] test_duration_estimation
- [ ] test_dynamic_planner.py
  - [ ] test_create_plan
  - [ ] test_execute_plan
  - [ ] test_replan_on_failure
  - [ ] test_event_handling
  - [ ] test_plan_adjustment
- [ ] test_decision_engine.py
  - [ ] test_make_decision
  - [ ] test_evaluate_options
  - [ ] test_confidence_calculation
  - [ ] test_risk_assessment
  - [ ] test_decision_rules
- [ ] test_trial_error.py
  - [ ] test_execute_with_retry
  - [ ] test_error_pattern_recognition
  - [ ] test_parameter_adjustment
  - [ ] test_learning_insights

### 整合測試
- [ ] test_planning_api.py
  - [ ] test_decompose_and_plan
  - [ ] test_execute_plan_flow
  - [ ] test_decision_api
  - [ ] test_trial_execution
- [ ] test_planning_e2e.py
  - [ ] test_full_planning_flow
  - [ ] test_adaptive_planning

### 覆蓋率
- [ ] 單元測試覆蓋率 >= 85%
- [ ] 整合測試覆蓋主要流程

---

## 資料庫遷移 ⏳

### 遷移腳本
- [ ] 創建 `010_planning_tables.sql`
  - [ ] task_decompositions 表
  - [ ] subtasks 表
  - [ ] execution_plans 表
  - [ ] plan_adjustments 表
  - [ ] decisions 表
  - [ ] trials 表
  - [ ] learning_insights 表
  - [ ] 相關索引

### 驗證
- [ ] 遷移腳本可正確執行
- [ ] 回滾腳本可用
- [ ] 索引效能測試通過

---

## 文檔完成 ⏳

### API 文檔
- [ ] Swagger 規劃 API 文檔
- [ ] 請求/響應範例
- [ ] 錯誤碼說明

### 開發者文檔
- [ ] 任務分解指南
  - [ ] 分解策略說明
  - [ ] 最佳實踐
- [ ] 動態規劃指南
  - [ ] 計劃執行流程
  - [ ] 重新規劃機制
  - [ ] 事件處理
- [ ] 自主決策指南
  - [ ] 決策類型說明
  - [ ] 信心等級配置
  - [ ] 自定義規則
- [ ] 試錯學習指南
  - [ ] 重試機制
  - [ ] 學習模式說明

---

## Sprint 完成標準

### 必須完成 (Must Have)
- [ ] TaskDecomposer 支援 4 種策略
- [ ] DynamicPlanner 可建立和執行計劃
- [ ] AutonomousDecisionEngine 可做決策
- [ ] TrialAndErrorEngine 可重試和學習
- [ ] 測試覆蓋率 >= 85%

### 應該完成 (Should Have)
- [ ] 決策可解釋
- [ ] 學習洞察有效
- [ ] 文檔完整

### 可以延後 (Could Have)
- [ ] 進階學習算法
- [ ] 決策視覺化

---

## 依賴確認

### 前置 Sprint
- [ ] Sprint 7-9 完成
  - [ ] 並行執行基礎
  - [ ] 協作機制
  - [ ] 群組聊天

### 外部依賴
- [ ] LLM 服務（任務分解、決策）
- [ ] 持久化存儲
- [ ] Redis 快取

---

## Sprint 10 完成統計

| Story | 點數 | 狀態 | 測試數 |
|-------|------|------|--------|
| S10-1: TaskDecomposer | 8 | ⏳ | 0 |
| S10-2: DynamicPlanner | 8 | ⏳ | 0 |
| S10-3: AutonomousDecisionEngine | 8 | ⏳ | 0 |
| S10-4: TrialAndErrorEngine | 5 | ⏳ | 0 |
| S10-5: Planning API | 5 | ⏳ | 0 |
| **總計** | **34** | **待開發** | **0** |

> 注意：總點數 34 點對應 Stories 分配。概述表中 42 點包含額外測試和文檔工作。

---

## 相關連結

- [Sprint 10 Plan](./sprint-10-plan.md) - 詳細計劃
- [Phase 2 Overview](./README.md) - Phase 2 概述
- [Sprint 9 Checklist](./sprint-9-checklist.md) - 前置 Sprint
- [Sprint 11 Plan](./sprint-11-plan.md) - 後續 Sprint
