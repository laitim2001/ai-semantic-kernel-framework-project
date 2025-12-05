# Sprint 8 Checklist: 智能交接機制 (Agent Handoff & Collaboration)

**Sprint 目標**: 實現 Agent 間的智能交接和協作機制
**週期**: Week 17-18
**總點數**: 31 點
**Phase 2 功能**: P2-F3 Agent 交接 + P2-F4 協作協議
**狀態**: ⏳ 待開發 (0/31 點)

---

## 快速驗證命令

```bash
# 驗證交接模組
python -c "from src.domain.orchestration.handoff import HandoffController; print('OK')"

# 驗證交接 API
curl http://localhost:8000/api/v1/handoff/status

# 觸發交接
curl -X POST http://localhost:8000/api/v1/handoff/trigger \
  -H "Content-Type: application/json" \
  -d '{"source_agent_id": "uuid", "target_agent_id": "uuid", "policy": "graceful"}'

# 運行交接測試
cd backend && pytest tests/unit/test_handoff*.py tests/unit/test_collaboration*.py -v
```

---

## S8-1: HandoffController 交接控制器 (8 點) ⏳

### 核心控制器 (src/domain/orchestration/handoff/)
- [ ] 創建 `controller.py`
  - [ ] HandoffPolicy 枚舉
    - [ ] IMMEDIATE - 立即交接
    - [ ] GRACEFUL - 優雅交接 (等待當前任務完成)
    - [ ] CONDITIONAL - 條件觸發交接
  - [ ] HandoffState 數據類
    - [ ] handoff_id 屬性
    - [ ] source_agent_id 屬性
    - [ ] target_agent_id 屬性
    - [ ] status 屬性
    - [ ] context 屬性
    - [ ] started_at 屬性
    - [ ] completed_at 屬性
  - [ ] HandoffController 類
    - [ ] __init__() 初始化方法
    - [ ] initiate_handoff() 發起交接
    - [ ] execute_handoff() 執行交接
    - [ ] _prepare_context() 準備上下文
    - [ ] _transfer_state() 狀態轉移
    - [ ] _notify_completion() 完成通知
    - [ ] cancel_handoff() 取消交接

### 上下文轉移
- [ ] 創建 `context_transfer.py`
  - [ ] ContextTransferManager 類
  - [ ] extract_context() 提取上下文
  - [ ] transform_context() 轉換上下文
  - [ ] inject_context() 注入上下文
  - [ ] validate_context() 驗證上下文

### 驗證標準
- [ ] 交接正確發起和執行
- [ ] 上下文完整轉移
- [ ] GRACEFUL 模式正確等待
- [ ] 取消交接正常工作
- [ ] 交接狀態正確追蹤

---

## S8-2: HandoffTrigger 交接觸發器 (5 點) ⏳

### 觸發器類型 (src/domain/orchestration/handoff/)
- [ ] 創建 `triggers.py`
  - [ ] TriggerType 枚舉
    - [ ] CONDITION - 條件觸發
    - [ ] EVENT - 事件觸發
    - [ ] TIMEOUT - 超時觸發
    - [ ] ERROR - 錯誤觸發
    - [ ] CAPABILITY - 能力不足觸發
  - [ ] HandoffTrigger 數據類
    - [ ] trigger_type 屬性
    - [ ] condition 屬性
    - [ ] priority 屬性

### 觸發評估器
- [ ] 創建 `trigger_evaluator.py`
  - [ ] HandoffTriggerEvaluator 類
  - [ ] register_trigger() 註冊觸發器
  - [ ] evaluate() 評估觸發條件
  - [ ] _evaluate_condition() 條件評估
  - [ ] _evaluate_capability() 能力評估
  - [ ] _evaluate_timeout() 超時評估
  - [ ] get_matching_triggers() 獲取匹配觸發器

### 驗證標準
- [ ] 條件觸發正確評估
- [ ] 事件觸發即時響應
- [ ] 超時觸發準確
- [ ] 能力觸發正確判斷
- [ ] 多觸發器優先級正確

---

## S8-3: CollaborationProtocol 協作協議 (8 點) ⏳

### 協作協議 (src/domain/orchestration/collaboration/)
- [ ] 創建 `protocol.py`
  - [ ] MessageType 枚舉
    - [ ] REQUEST - 請求訊息
    - [ ] RESPONSE - 回應訊息
    - [ ] BROADCAST - 廣播訊息
    - [ ] NEGOTIATE - 協商訊息
  - [ ] CollaborationMessage 數據類
    - [ ] message_id 屬性
    - [ ] message_type 屬性
    - [ ] sender_id 屬性
    - [ ] recipient_id 屬性
    - [ ] content 屬性
    - [ ] timestamp 屬性
  - [ ] CollaborationProtocol 類
    - [ ] send_message() 發送訊息
    - [ ] receive_message() 接收訊息
    - [ ] broadcast() 廣播訊息
    - [ ] negotiate() 協商方法
    - [ ] _route_message() 訊息路由

### 協作會話管理
- [ ] 創建 `session.py`
  - [ ] CollaborationSession 類
  - [ ] create_session() 創建會話
  - [ ] join_session() 加入會話
  - [ ] leave_session() 離開會話
  - [ ] get_participants() 獲取參與者
  - [ ] close_session() 關閉會話

### 訊息隊列整合
- [ ] 訊息持久化
- [ ] 訊息重試機制
- [ ] 訊息過期處理

### 驗證標準
- [ ] 訊息正確路由
- [ ] 廣播到達所有參與者
- [ ] 協商流程完整
- [ ] 會話管理正確
- [ ] 訊息持久化可靠

---

## S8-4: CapabilityMatcher 能力匹配器 (5 點) ⏳

### 能力匹配 (src/domain/orchestration/handoff/)
- [ ] 創建 `capability_matcher.py`
  - [ ] CapabilityMatcher 類
  - [ ] find_capable_agents() 查找能力匹配 Agent
  - [ ] _calculate_match_score() 計算匹配分數
  - [ ] _check_availability() 檢查可用性
  - [ ] get_best_match() 獲取最佳匹配
  - [ ] register_agent_capabilities() 註冊能力

### 能力描述
- [ ] 創建 `capabilities.py`
  - [ ] AgentCapability 數據類
    - [ ] capability_id 屬性
    - [ ] name 屬性
    - [ ] description 屬性
    - [ ] proficiency_level 屬性 (0-1)
  - [ ] CapabilityRegistry 類
  - [ ] 內建能力定義

### 驗證標準
- [ ] 能力匹配準確
- [ ] 匹配分數計算合理
- [ ] 可用性檢查正確
- [ ] 最佳匹配選擇正確
- [ ] 能力註冊更新正常

---

## S8-5: Handoff API 路由 (5 點) ⏳

### API 路由 (src/api/v1/handoff/)
- [ ] 創建 `routes.py`
  - [ ] POST /handoff/trigger - 觸發交接
  - [ ] GET /handoff/{id}/status - 獲取交接狀態
  - [ ] POST /handoff/{id}/cancel - 取消交接
  - [ ] GET /handoff/history - 獲取交接歷史
  - [ ] POST /handoff/capability/match - 能力匹配查詢
  - [ ] GET /handoff/agents/{id}/capabilities - 獲取 Agent 能力

### 請求/響應 Schema
- [ ] 創建 `schemas.py`
  - [ ] HandoffTriggerRequest
    - [ ] source_agent_id
    - [ ] target_agent_id (可選，自動匹配時)
    - [ ] policy
    - [ ] context
    - [ ] trigger_conditions
  - [ ] HandoffStatusResponse
  - [ ] CapabilityMatchRequest
  - [ ] CapabilityMatchResponse

### 驗證標準
- [ ] 交接 API 完整可用
- [ ] 能力匹配 API 正確返回
- [ ] 歷史查詢支持分頁
- [ ] 錯誤處理完善
- [ ] API 文檔完整

---

## 測試完成 ⏳

### 單元測試
- [ ] test_handoff_controller.py
  - [ ] test_initiate_handoff
  - [ ] test_execute_immediate_handoff
  - [ ] test_execute_graceful_handoff
  - [ ] test_cancel_handoff
  - [ ] test_context_transfer
- [ ] test_handoff_triggers.py
  - [ ] test_condition_trigger
  - [ ] test_event_trigger
  - [ ] test_timeout_trigger
  - [ ] test_capability_trigger
  - [ ] test_trigger_priority
- [ ] test_collaboration_protocol.py
  - [ ] test_send_receive_message
  - [ ] test_broadcast_message
  - [ ] test_negotiation_flow
  - [ ] test_session_management
- [ ] test_capability_matcher.py
  - [ ] test_find_capable_agents
  - [ ] test_match_score_calculation
  - [ ] test_best_match_selection

### 整合測試
- [ ] test_handoff_api.py
  - [ ] test_trigger_handoff_api
  - [ ] test_get_handoff_status
  - [ ] test_capability_match_api
- [ ] test_handoff_e2e.py
  - [ ] test_complete_handoff_flow
  - [ ] test_handoff_with_context

### 覆蓋率
- [ ] 單元測試覆蓋率 >= 85%
- [ ] 整合測試覆蓋主要流程

---

## 資料庫遷移 ⏳

### 遷移腳本
- [ ] 創建 `008_handoff_tables.sql`
  - [ ] handoff_records 表
  - [ ] handoff_triggers 表
  - [ ] collaboration_messages 表
  - [ ] collaboration_sessions 表
  - [ ] agent_capabilities 表
  - [ ] 相關索引

### 驗證
- [ ] 遷移腳本可正確執行
- [ ] 回滾腳本可用
- [ ] 索引效能測試通過

---

## 文檔完成 ⏳

### API 文檔
- [ ] Swagger 交接 API 文檔
- [ ] 請求/響應範例
- [ ] 錯誤碼說明

### 開發者文檔
- [ ] 交接機制使用指南
  - [ ] 交接策略說明
  - [ ] 觸發條件配置
  - [ ] 上下文轉移說明
- [ ] 協作協議指南
  - [ ] 訊息類型說明
  - [ ] 協商流程
  - [ ] 會話管理
- [ ] 能力匹配指南
  - [ ] 能力定義
  - [ ] 匹配算法說明
  - [ ] 最佳實踐

---

## Sprint 完成標準

### 必須完成 (Must Have)
- [ ] HandoffController 可執行交接
- [ ] 觸發器正確評估條件
- [ ] 協作協議訊息正確傳遞
- [ ] 能力匹配可用
- [ ] 測試覆蓋率 >= 85%

### 應該完成 (Should Have)
- [ ] 交接成功率 >= 90%
- [ ] 上下文完整轉移
- [ ] 文檔完整

### 可以延後 (Could Have)
- [ ] 進階協商策略
- [ ] 交接可視化

---

## 依賴確認

### 前置 Sprint
- [ ] Sprint 7 完成
  - [ ] 並行執行基礎設施可用
  - [ ] 狀態管理機制穩定

### 外部依賴
- [ ] RabbitMQ 訊息隊列配置
- [ ] Redis 會話存儲配置

---

## Sprint 8 完成統計

| Story | 點數 | 狀態 | 測試數 |
|-------|------|------|--------|
| S8-1: HandoffController | 8 | ⏳ | 0 |
| S8-2: HandoffTrigger | 5 | ⏳ | 0 |
| S8-3: CollaborationProtocol | 8 | ⏳ | 0 |
| S8-4: CapabilityMatcher | 5 | ⏳ | 0 |
| S8-5: Handoff API | 5 | ⏳ | 0 |
| **總計** | **31** | **待開發** | **0** |

---

## 相關連結

- [Sprint 8 Plan](./sprint-8-plan.md) - 詳細計劃
- [Phase 2 Overview](./README.md) - Phase 2 概述
- [Sprint 7 Checklist](./sprint-7-checklist.md) - 前置 Sprint
- [Sprint 9 Plan](./sprint-9-plan.md) - 後續 Sprint
