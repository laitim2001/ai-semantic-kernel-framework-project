# Sprint 11 Checklist: 嵌套工作流 (Nested Workflows & Advanced Orchestration)

**Sprint 目標**: 實現工作流嵌套和遞歸執行能力，支援複雜的階層式流程編排
**週期**: Week 23-24
**總點數**: 39 點
**Phase 2 功能**: P2-F11 Nested Workflows + P2-F12 Sub-workflow Execution + P2-F13 Recursive Patterns
**狀態**: ⏳ 待開發 (0/39 點)

---

## 快速驗證命令

```bash
# 驗證嵌套工作流模組
python -c "from src.domain.orchestration.nested import NestedWorkflowManager; print('OK')"

# 驗證嵌套 API
curl http://localhost:8000/api/v1/nested/status

# 執行嵌套工作流
curl -X POST http://localhost:8000/api/v1/nested/execute \
  -H "Content-Type: application/json" \
  -d '{"parent_workflow_id": "uuid", "sub_workflow_id": "uuid"}'

# 運行嵌套測試
cd backend && pytest tests/unit/test_nested*.py tests/unit/test_recursive*.py -v
```

---

## S11-1: NestedWorkflowManager 嵌套工作流管理器 (8 點) ⏳

### 核心管理器 (src/domain/orchestration/nested/)
- [ ] 創建 `workflow_manager.py`
  - [ ] NestedWorkflowType 枚舉
    - [ ] INLINE - 內聯定義
    - [ ] REFERENCE - 引用現有
    - [ ] DYNAMIC - 動態生成
    - [ ] RECURSIVE - 遞歸調用
  - [ ] WorkflowScope 枚舉
    - [ ] ISOLATED - 完全隔離
    - [ ] INHERITED - 繼承上下文
    - [ ] SHARED - 共享上下文
  - [ ] NestedWorkflowConfig 數據類
    - [ ] workflow_type 屬性
    - [ ] scope 屬性
    - [ ] max_depth 屬性
    - [ ] timeout_seconds 屬性
    - [ ] retry_on_failure 屬性
    - [ ] max_retries 屬性
    - [ ] pass_context 屬性
    - [ ] return_outputs 屬性
  - [ ] SubWorkflowReference 數據類
    - [ ] id 屬性
    - [ ] parent_workflow_id 屬性
    - [ ] workflow_id 屬性
    - [ ] definition 屬性
    - [ ] config 屬性
    - [ ] input_mapping 屬性
    - [ ] output_mapping 屬性
    - [ ] position 屬性
    - [ ] status 屬性
  - [ ] NestedExecutionContext 數據類
    - [ ] execution_id 屬性
    - [ ] parent_execution_id 屬性
    - [ ] workflow_id 屬性
    - [ ] depth 屬性
    - [ ] path 屬性
    - [ ] variables 屬性
    - [ ] parent_variables 屬性
  - [ ] NestedWorkflowManager 類
    - [ ] __init__() 初始化方法
    - [ ] register_sub_workflow() 註冊子工作流
    - [ ] _has_cycle() 循環依賴檢測
    - [ ] execute_sub_workflow() 執行子工作流
    - [ ] _create_child_context() 創建子上下文
    - [ ] _execute_reference_workflow() 執行引用工作流
    - [ ] _execute_inline_workflow() 執行內聯工作流
    - [ ] _execute_dynamic_workflow() 執行動態工作流
    - [ ] _execute_recursive_workflow() 執行遞歸工作流
    - [ ] _map_outputs() 映射輸出
    - [ ] get_execution_tree() 獲取執行樹
    - [ ] cancel_nested_execution() 取消嵌套執行

### 依賴圖管理
- [ ] 創建 `dependency_graph.py`
  - [ ] DependencyGraph 類
  - [ ] add_dependency() 添加依賴
  - [ ] remove_dependency() 移除依賴
  - [ ] has_cycle() 循環檢測
  - [ ] get_topological_order() 拓撲排序
  - [ ] visualize() 視覺化

### 驗證標準
- [ ] 支援工作流嵌套結構
- [ ] 正確的深度限制
- [ ] 循環依賴檢測
- [ ] 上下文傳遞正確
- [ ] 單元測試覆蓋率 > 85%

---

## S11-2: SubWorkflowExecutor 子工作流執行器 (5 點) ⏳

### 執行器實現 (src/domain/orchestration/nested/)
- [ ] 創建 `sub_executor.py`
  - [ ] SubWorkflowExecutionMode 枚舉
    - [ ] SYNC - 同步等待
    - [ ] ASYNC - 異步執行
    - [ ] FIRE_AND_FORGET - 發射即忘
    - [ ] CALLBACK - 完成回調
  - [ ] SubExecutionState 數據類
    - [ ] execution_id 屬性
    - [ ] sub_workflow_id 屬性
    - [ ] mode 屬性
    - [ ] status 屬性
    - [ ] result 屬性
    - [ ] error 屬性
    - [ ] callback 屬性
  - [ ] SubWorkflowExecutor 類
    - [ ] __init__() 初始化方法
    - [ ] execute() 執行
    - [ ] execute_async() 異步執行
    - [ ] execute_with_callback() 回調執行
    - [ ] wait_for_completion() 等待完成
    - [ ] cancel() 取消執行
    - [ ] get_status() 獲取狀態

### 執行池管理
- [ ] 創建 `execution_pool.py`
  - [ ] SubWorkflowPool 類
  - [ ] submit() 提交執行
  - [ ] get_result() 獲取結果
  - [ ] cancel_all() 取消所有
  - [ ] get_active_count() 獲取活躍數

### 驗證標準
- [ ] 同步執行正確
- [ ] 異步執行不阻塞
- [ ] 回調正確觸發
- [ ] 超時處理正常
- [ ] 取消操作有效

---

## S11-3: RecursivePatternHandler 遞歸模式處理器 (5 點) ⏳

### 遞歸處理 (src/domain/orchestration/nested/)
- [ ] 創建 `recursive_handler.py`
  - [ ] RecursionType 枚舉
    - [ ] TAIL - 尾遞歸
    - [ ] TREE - 樹遞歸
    - [ ] MUTUAL - 相互遞歸
  - [ ] TerminationCondition 數據類
    - [ ] condition_type 屬性
    - [ ] check_function 屬性
    - [ ] max_iterations 屬性
    - [ ] timeout_seconds 屬性
  - [ ] RecursivePatternHandler 類
    - [ ] __init__() 初始化方法
    - [ ] execute_recursive() 執行遞歸
    - [ ] _check_termination() 檢查終止
    - [ ] _execute_iteration() 執行迭代
    - [ ] set_termination_condition() 設置終止條件
    - [ ] get_recursion_depth() 獲取深度
    - [ ] get_iteration_history() 獲取迭代歷史

### 堆疊管理
- [ ] 創建 `recursion_stack.py`
  - [ ] RecursionStack 類
  - [ ] push() 入棧
  - [ ] pop() 出棧
  - [ ] peek() 查看棧頂
  - [ ] get_depth() 獲取深度
  - [ ] is_overflow() 溢出檢查
  - [ ] get_trace() 獲取追蹤

### 尾遞歸優化
- [ ] 創建 `tail_recursion.py`
  - [ ] TailRecursionOptimizer 類
  - [ ] optimize() 優化遞歸
  - [ ] convert_to_iteration() 轉換為迭代
  - [ ] is_tail_recursive() 判斷尾遞歸

### 驗證標準
- [ ] 遞歸執行正確
- [ ] 終止條件有效
- [ ] 堆疊溢出保護
- [ ] 尾遞歸優化工作
- [ ] 迭代歷史可追蹤

---

## S11-4: WorkflowCompositionBuilder 工作流組合構建器 (5 點) ⏳

### 組合構建 (src/domain/orchestration/nested/)
- [ ] 創建 `composition_builder.py`
  - [ ] CompositionType 枚舉
    - [ ] SEQUENTIAL - 順序組合
    - [ ] PARALLEL - 並行組合
    - [ ] CONDITIONAL - 條件組合
    - [ ] LOOP - 循環組合
  - [ ] WorkflowComponent 數據類
    - [ ] component_id 屬性
    - [ ] component_type 屬性
    - [ ] workflow_reference 屬性
    - [ ] inputs 屬性
    - [ ] outputs 屬性
  - [ ] WorkflowCompositionBuilder 類
    - [ ] __init__() 初始化方法
    - [ ] add_sequential() 添加順序
    - [ ] add_parallel() 添加並行
    - [ ] add_conditional() 添加條件
    - [ ] add_loop() 添加循環
    - [ ] build() 構建組合
    - [ ] validate() 驗證組合
    - [ ] optimize() 優化組合

### 模板支援
- [ ] 創建 `composition_templates.py`
  - [ ] CompositionTemplate 類
  - [ ] create_map_reduce() Map-Reduce 模板
  - [ ] create_scatter_gather() Scatter-Gather 模板
  - [ ] create_pipeline() Pipeline 模板
  - [ ] create_saga() Saga 模板

### 驗證標準
- [ ] 順序組合正確
- [ ] 並行組合正確
- [ ] 條件組合正確
- [ ] 循環組合正確
- [ ] 模板可用

---

## S11-5: Nested Workflow API 路由 (8 點) ⏳

### API 路由 (src/api/v1/nested/)
- [ ] 創建 `routes.py`
  - [ ] POST /nested/workflows - 創建嵌套工作流
  - [ ] GET /nested/workflows/{id} - 獲取嵌套工作流
  - [ ] POST /nested/workflows/{id}/sub - 添加子工作流
  - [ ] DELETE /nested/workflows/{id}/sub/{sub_id} - 移除子工作流
  - [ ] POST /nested/execute - 執行嵌套工作流
  - [ ] GET /nested/executions/{id}/tree - 獲取執行樹
  - [ ] POST /nested/executions/{id}/cancel - 取消執行
  - [ ] GET /nested/executions/{id}/status - 獲取狀態
  - [ ] POST /nested/compose - 組合工作流
  - [ ] GET /nested/templates - 獲取組合模板
  - [ ] POST /nested/validate - 驗證結構

### 請求/響應 Schema
- [ ] 創建 `schemas.py`
  - [ ] CreateNestedWorkflowRequest
  - [ ] NestedWorkflowResponse
  - [ ] AddSubWorkflowRequest
  - [ ] ExecuteNestedRequest
  - [ ] ExecutionTreeResponse
  - [ ] ComposeWorkflowRequest
  - [ ] CompositionResponse
  - [ ] ValidationResponse

### 執行樹視覺化
- [ ] 創建 `visualization.py`
  - [ ] TreeVisualizer 類
  - [ ] to_json() JSON 格式
  - [ ] to_mermaid() Mermaid 格式
  - [ ] to_graphviz() GraphViz 格式

### 驗證標準
- [ ] 所有 API 端點可用
- [ ] 執行樹正確呈現
- [ ] 組合 API 正確
- [ ] 驗證 API 有效
- [ ] API 文檔完整

---

## S11-6: Context Propagation 上下文傳播 (8 點) ⏳

### 上下文傳播 (src/domain/orchestration/nested/)
- [ ] 創建 `context_propagation.py`
  - [ ] PropagationType 枚舉
    - [ ] COPY - 複製
    - [ ] REFERENCE - 引用
    - [ ] SELECTIVE - 選擇性
    - [ ] TRANSFORM - 轉換
  - [ ] ContextPropagator 類
    - [ ] propagate_down() 向下傳播
    - [ ] propagate_up() 向上傳播
    - [ ] merge_contexts() 合併上下文
    - [ ] isolate_context() 隔離上下文
    - [ ] transform_context() 轉換上下文

### 變數作用域
- [ ] 創建 `variable_scope.py`
  - [ ] VariableScope 類
  - [ ] define_variable() 定義變數
  - [ ] get_variable() 獲取變數
  - [ ] set_variable() 設置變數
  - [ ] resolve_reference() 解析引用
  - [ ] create_child_scope() 創建子作用域

### 數據流追蹤
- [ ] 創建 `data_flow.py`
  - [ ] DataFlowTracker 類
  - [ ] track_input() 追蹤輸入
  - [ ] track_output() 追蹤輸出
  - [ ] get_flow_graph() 獲取流程圖
  - [ ] detect_data_dependency() 檢測數據依賴

### 驗證標準
- [ ] 向下傳播正確
- [ ] 向上傳播正確
- [ ] 作用域隔離有效
- [ ] 數據流可追蹤
- [ ] 引用解析正確

---

## 測試完成 ⏳

### 單元測試
- [ ] test_nested_workflow_manager.py
  - [ ] test_register_sub_workflow
  - [ ] test_cycle_detection
  - [ ] test_execute_sub_workflow
  - [ ] test_depth_limit
  - [ ] test_context_propagation
- [ ] test_sub_executor.py
  - [ ] test_sync_execution
  - [ ] test_async_execution
  - [ ] test_callback_execution
  - [ ] test_cancellation
- [ ] test_recursive_handler.py
  - [ ] test_recursive_execution
  - [ ] test_termination_condition
  - [ ] test_stack_overflow_protection
  - [ ] test_tail_recursion_optimization
- [ ] test_composition_builder.py
  - [ ] test_sequential_composition
  - [ ] test_parallel_composition
  - [ ] test_conditional_composition
  - [ ] test_loop_composition
- [ ] test_context_propagation.py
  - [ ] test_propagate_down
  - [ ] test_propagate_up
  - [ ] test_scope_isolation

### 整合測試
- [ ] test_nested_api.py
  - [ ] test_create_nested_workflow
  - [ ] test_execute_nested
  - [ ] test_execution_tree
  - [ ] test_compose_workflow
- [ ] test_nested_e2e.py
  - [ ] test_complex_nested_flow
  - [ ] test_recursive_workflow

### 覆蓋率
- [ ] 單元測試覆蓋率 >= 85%
- [ ] 整合測試覆蓋主要流程

---

## 資料庫遷移 ⏳

### 遷移腳本
- [ ] 創建 `011_nested_workflow_tables.sql`
  - [ ] nested_workflows 表
  - [ ] sub_workflow_references 表
  - [ ] nested_executions 表
  - [ ] execution_contexts 表
  - [ ] composition_definitions 表
  - [ ] 相關索引

### 驗證
- [ ] 遷移腳本可正確執行
- [ ] 回滾腳本可用
- [ ] 索引效能測試通過

---

## 文檔完成 ⏳

### API 文檔
- [ ] Swagger 嵌套工作流 API 文檔
- [ ] 請求/響應範例
- [ ] 錯誤碼說明

### 開發者文檔
- [ ] 嵌套工作流指南
  - [ ] 嵌套類型說明
  - [ ] 深度限制配置
  - [ ] 循環依賴處理
- [ ] 遞歸模式指南
  - [ ] 終止條件設定
  - [ ] 尾遞歸優化
- [ ] 工作流組合指南
  - [ ] 組合模式說明
  - [ ] 內建模板使用
- [ ] 上下文傳播指南
  - [ ] 作用域類型
  - [ ] 變數映射

---

## Sprint 完成標準

### 必須完成 (Must Have)
- [ ] NestedWorkflowManager 支援嵌套
- [ ] SubWorkflowExecutor 可執行子工作流
- [ ] 循環依賴檢測有效
- [ ] 深度限制正確
- [ ] 測試覆蓋率 >= 85%

### 應該完成 (Should Have)
- [ ] 遞歸模式支援
- [ ] 工作流組合構建器
- [ ] 文檔完整

### 可以延後 (Could Have)
- [ ] 進階組合模板
- [ ] 執行樹視覺化

---

## 依賴確認

### 前置 Sprint
- [ ] Sprint 7-10 完成
  - [ ] 並行執行
  - [ ] 動態規劃

### 外部依賴
- [ ] 工作流引擎核心
- [ ] 執行服務
- [ ] 持久化存儲

---

## Sprint 11 完成統計

| Story | 點數 | 狀態 | 測試數 |
|-------|------|------|--------|
| S11-1: NestedWorkflowManager | 8 | ⏳ | 0 |
| S11-2: SubWorkflowExecutor | 5 | ⏳ | 0 |
| S11-3: RecursivePatternHandler | 5 | ⏳ | 0 |
| S11-4: WorkflowCompositionBuilder | 5 | ⏳ | 0 |
| S11-5: Nested Workflow API | 8 | ⏳ | 0 |
| S11-6: Context Propagation | 8 | ⏳ | 0 |
| **總計** | **39** | **待開發** | **0** |

---

## 相關連結

- [Sprint 11 Plan](./sprint-11-plan.md) - 詳細計劃
- [Phase 2 Overview](./README.md) - Phase 2 概述
- [Sprint 10 Checklist](./sprint-10-checklist.md) - 前置 Sprint
- [Sprint 12 Plan](./sprint-12-plan.md) - 後續 Sprint
