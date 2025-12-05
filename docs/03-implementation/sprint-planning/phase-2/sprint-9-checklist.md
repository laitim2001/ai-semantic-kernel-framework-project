# Sprint 9 Checklist: 群組協作模式 (GroupChat & Multi-turn Conversation)

**Sprint 目標**: 實現多 Agent 群組聊天和多輪對話能力，支援複雜協作場景
**週期**: Week 19-20
**總點數**: 42 點
**Phase 2 功能**: P2-F5 GroupChat + P2-F6 Multi-turn + P2-F7 Conversation Memory
**狀態**: ⏳ 待開發 (0/42 點)

---

## 快速驗證命令

```bash
# 驗證 GroupChat 模組
python -c "from src.domain.orchestration.groupchat import GroupChatManager; print('OK')"

# 驗證 GroupChat API
curl http://localhost:8000/api/v1/groupchat/status

# 建立群組聊天
curl -X POST http://localhost:8000/api/v1/groupchat/create \
  -H "Content-Type: application/json" \
  -d '{"name": "test-group", "agents": ["agent1", "agent2"]}'

# 運行 GroupChat 測試
cd backend && pytest tests/unit/test_groupchat*.py tests/unit/test_multiturn*.py -v
```

---

## S9-1: GroupChatManager 群組聊天管理器 (8 點) ⏳

### 核心管理器 (src/domain/orchestration/groupchat/)
- [ ] 創建 `manager.py`
  - [ ] SpeakerSelectionMethod 枚舉
    - [ ] AUTO - LLM 自動選擇
    - [ ] ROUND_ROBIN - 輪流發言
    - [ ] RANDOM - 隨機選擇
    - [ ] MANUAL - 人工指定
    - [ ] PRIORITY - 按優先級
    - [ ] EXPERTISE - 按專業能力
  - [ ] MessageType 枚舉
    - [ ] USER - 用戶訊息
    - [ ] AGENT - Agent 訊息
    - [ ] SYSTEM - 系統訊息
    - [ ] FUNCTION_CALL - 函數調用
    - [ ] FUNCTION_RESULT - 函數結果
  - [ ] GroupMessage 數據類
    - [ ] id 屬性
    - [ ] group_id 屬性
    - [ ] sender_id 屬性
    - [ ] sender_name 屬性
    - [ ] content 屬性
    - [ ] message_type 屬性
    - [ ] timestamp 屬性
    - [ ] metadata 屬性
    - [ ] reply_to 屬性
  - [ ] GroupChatConfig 數據類
    - [ ] max_rounds 屬性
    - [ ] max_messages_per_round 屬性
    - [ ] speaker_selection_method 屬性
    - [ ] allow_repeat_speaker 屬性
    - [ ] termination_conditions 屬性
    - [ ] timeout_seconds 屬性
    - [ ] enable_voting 屬性
    - [ ] consensus_threshold 屬性
  - [ ] GroupChatState 數據類
  - [ ] GroupChatManager 類
    - [ ] __init__() 初始化方法
    - [ ] start_conversation() 開始對話
    - [ ] _execute_round() 執行一輪
    - [ ] _get_agent_response() 獲取回應
    - [ ] _build_context_for_agent() 構建上下文
    - [ ] _should_terminate() 終止判斷
    - [ ] add_message() 添加訊息
    - [ ] get_transcript() 獲取記錄
    - [ ] get_summary() 獲取摘要

### 終止檢查器
- [ ] 創建 `termination.py`
  - [ ] TerminationChecker 類
  - [ ] should_terminate() 終止檢查
  - [ ] add_condition() 添加條件
  - [ ] 支援關鍵字終止
  - [ ] 支援輪次終止
  - [ ] 支援超時終止

### 驗證標準
- [ ] GroupChatManager 可管理多 Agent 對話
- [ ] 最大輪次限制正確
- [ ] 超時處理正常
- [ ] 訊息記錄完整
- [ ] 終止條件正確觸發

---

## S9-2: SpeakerSelector 發言者選擇器 (5 點) ⏳

### 選擇器實現 (src/domain/orchestration/groupchat/)
- [ ] 創建 `speaker_selector.py`
  - [ ] SpeakerSelector 類
  - [ ] select_next() 選擇下一位發言者
  - [ ] _select_auto() 自動選擇（LLM）
  - [ ] _select_round_robin() 輪流選擇
  - [ ] _select_random() 隨機選擇
  - [ ] _select_manual() 人工選擇
  - [ ] _select_by_priority() 優先級選擇
  - [ ] _select_by_expertise() 專業能力選擇
  - [ ] _build_selection_prompt() 構建選擇提示
  - [ ] _parse_selection_response() 解析選擇結果

### 專業能力匹配
- [ ] 創建 `expertise_matcher.py`
  - [ ] ExpertiseMatcher 類
  - [ ] match_expertise() 匹配專業能力
  - [ ] calculate_relevance() 計算相關性
  - [ ] get_best_agent() 獲取最佳 Agent

### 驗證標準
- [ ] 所有選擇策略正確運作
- [ ] AUTO 模式 LLM 選擇合理
- [ ] ROUND_ROBIN 順序正確
- [ ] EXPERTISE 匹配準確
- [ ] 不重複發言控制正常

---

## S9-3: MultiTurnSessionManager 多輪對話管理器 (8 點) ⏳

### 會話管理 (src/domain/orchestration/multiturn/)
- [ ] 創建 `session_manager.py`
  - [ ] SessionStatus 枚舉
    - [ ] ACTIVE - 活躍中
    - [ ] PAUSED - 暫停
    - [ ] COMPLETED - 完成
    - [ ] EXPIRED - 過期
  - [ ] MultiTurnSession 數據類
    - [ ] session_id 屬性
    - [ ] user_id 屬性
    - [ ] agent_ids 屬性
    - [ ] status 屬性
    - [ ] context 屬性
    - [ ] history 屬性
    - [ ] created_at 屬性
    - [ ] last_activity 屬性
  - [ ] MultiTurnSessionManager 類
    - [ ] create_session() 創建會話
    - [ ] get_session() 獲取會話
    - [ ] update_session() 更新會話
    - [ ] close_session() 關閉會話
    - [ ] resume_session() 恢復會話
    - [ ] list_active_sessions() 列出活躍會話

### 輪次追蹤
- [ ] 創建 `turn_tracker.py`
  - [ ] TurnTracker 類
  - [ ] start_turn() 開始輪次
  - [ ] end_turn() 結束輪次
  - [ ] get_current_turn() 獲取當前輪次
  - [ ] get_turn_history() 獲取輪次歷史

### 上下文維護
- [ ] 創建 `context_manager.py`
  - [ ] SessionContextManager 類
  - [ ] update_context() 更新上下文
  - [ ] get_context() 獲取上下文
  - [ ] merge_context() 合併上下文
  - [ ] clear_context() 清除上下文

### 驗證標準
- [ ] 會話創建和管理正常
- [ ] 多輪次追蹤準確
- [ ] 上下文在輪次間保持
- [ ] 會話恢復正常
- [ ] 過期會話正確處理

---

## S9-4: ConversationMemoryStore 對話記憶存儲 (8 點) ⏳

### 記憶存儲 (src/domain/orchestration/memory/)
- [ ] 創建 `conversation_store.py`
  - [ ] MemoryType 枚舉
    - [ ] SHORT_TERM - 短期記憶
    - [ ] LONG_TERM - 長期記憶
    - [ ] WORKING - 工作記憶
  - [ ] ConversationMemory 數據類
    - [ ] memory_id 屬性
    - [ ] session_id 屬性
    - [ ] memory_type 屬性
    - [ ] content 屬性
    - [ ] importance 屬性
    - [ ] timestamp 屬性
    - [ ] metadata 屬性
  - [ ] ConversationMemoryStore 類
    - [ ] add_message() 添加訊息
    - [ ] get_recent_messages() 獲取最近訊息
    - [ ] get_messages_by_session() 按會話獲取
    - [ ] search_messages() 搜索訊息
    - [ ] summarize_conversation() 摘要對話
    - [ ] clear_session_memory() 清除會話記憶

### 記憶壓縮
- [ ] 創建 `memory_compressor.py`
  - [ ] MemoryCompressor 類
  - [ ] compress() 壓縮記憶
  - [ ] extract_key_points() 提取關鍵點
  - [ ] create_summary() 創建摘要
  - [ ] prune_old_memories() 修剪舊記憶

### 相關性檢索
- [ ] 創建 `relevance_retriever.py`
  - [ ] RelevanceRetriever 類
  - [ ] retrieve_relevant() 檢索相關記憶
  - [ ] calculate_relevance_score() 計算相關性分數
  - [ ] filter_by_importance() 按重要性過濾

### 驗證標準
- [ ] 訊息正確存儲和檢索
- [ ] 記憶壓縮有效
- [ ] 相關性檢索準確
- [ ] 長期記憶持久化
- [ ] 會話記憶隔離

---

## S9-5: VotingManager 投票管理器 (5 點) ⏳

### 投票機制 (src/domain/orchestration/groupchat/)
- [ ] 創建 `voting.py`
  - [ ] VotingType 枚舉
    - [ ] MAJORITY - 多數決
    - [ ] UNANIMOUS - 全票通過
    - [ ] WEIGHTED - 加權投票
    - [ ] RANKED - 排序投票
  - [ ] Vote 數據類
    - [ ] voter_id 屬性
    - [ ] option_id 屬性
    - [ ] weight 屬性
    - [ ] timestamp 屬性
  - [ ] VotingSession 數據類
    - [ ] voting_id 屬性
    - [ ] group_id 屬性
    - [ ] question 屬性
    - [ ] options 屬性
    - [ ] votes 屬性
    - [ ] status 屬性
    - [ ] result 屬性
  - [ ] VotingManager 類
    - [ ] create_voting() 創建投票
    - [ ] cast_vote() 投票
    - [ ] close_voting() 關閉投票
    - [ ] calculate_result() 計算結果
    - [ ] get_voting_status() 獲取狀態

### 共識達成
- [ ] 創建 `consensus.py`
  - [ ] ConsensusChecker 類
  - [ ] check_consensus() 檢查共識
  - [ ] calculate_agreement_level() 計算同意程度
  - [ ] suggest_compromise() 建議妥協方案

### 驗證標準
- [ ] 所有投票類型正確運作
- [ ] 投票結果計算準確
- [ ] 共識檢查正確
- [ ] 加權投票權重正確
- [ ] 投票狀態追蹤完整

---

## S9-6: GroupChat API 路由 (8 點) ⏳

### API 路由 (src/api/v1/groupchat/)
- [ ] 創建 `routes.py`
  - [ ] POST /groupchat/create - 創建群組
  - [ ] GET /groupchat/{id} - 獲取群組信息
  - [ ] POST /groupchat/{id}/start - 開始對話
  - [ ] POST /groupchat/{id}/message - 發送訊息
  - [ ] GET /groupchat/{id}/transcript - 獲取對話記錄
  - [ ] POST /groupchat/{id}/terminate - 終止對話
  - [ ] GET /groupchat/{id}/summary - 獲取摘要
  - [ ] POST /groupchat/{id}/voting/create - 創建投票
  - [ ] POST /groupchat/{id}/voting/{vid}/vote - 投票
  - [ ] GET /groupchat/{id}/voting/{vid}/result - 獲取結果

### 多輪對話 API
- [ ] 創建 `multiturn_routes.py`
  - [ ] POST /sessions - 創建會話
  - [ ] GET /sessions/{id} - 獲取會話
  - [ ] POST /sessions/{id}/turn - 執行一輪
  - [ ] POST /sessions/{id}/resume - 恢復會話
  - [ ] DELETE /sessions/{id} - 關閉會話
  - [ ] GET /sessions/{id}/history - 獲取歷史

### 請求/響應 Schema
- [ ] 創建 `schemas.py`
  - [ ] CreateGroupChatRequest
  - [ ] GroupChatResponse
  - [ ] SendMessageRequest
  - [ ] TranscriptResponse
  - [ ] VotingRequest
  - [ ] VotingResponse
  - [ ] CreateSessionRequest
  - [ ] SessionResponse
  - [ ] TurnRequest
  - [ ] TurnResponse

### WebSocket 支援
- [ ] 創建 `websocket.py`
  - [ ] 實時訊息推送
  - [ ] 發言者通知
  - [ ] 投票更新通知
  - [ ] 對話狀態通知

### 驗證標準
- [ ] 所有 API 端點可用
- [ ] WebSocket 連接穩定
- [ ] 實時更新正確
- [ ] 錯誤處理完善
- [ ] API 文檔完整

---

## 測試完成 ⏳

### 單元測試
- [ ] test_groupchat_manager.py
  - [ ] test_create_groupchat
  - [ ] test_start_conversation
  - [ ] test_execute_round
  - [ ] test_max_rounds_limit
  - [ ] test_termination_conditions
- [ ] test_speaker_selector.py
  - [ ] test_auto_selection
  - [ ] test_round_robin
  - [ ] test_random_selection
  - [ ] test_priority_selection
  - [ ] test_expertise_selection
- [ ] test_multiturn_session.py
  - [ ] test_create_session
  - [ ] test_multi_turn_context
  - [ ] test_session_resume
  - [ ] test_session_expiry
- [ ] test_conversation_memory.py
  - [ ] test_add_message
  - [ ] test_retrieve_relevant
  - [ ] test_memory_compression
  - [ ] test_summarization
- [ ] test_voting_manager.py
  - [ ] test_majority_voting
  - [ ] test_weighted_voting
  - [ ] test_consensus_check

### 整合測試
- [ ] test_groupchat_api.py
  - [ ] test_create_and_start_groupchat
  - [ ] test_multi_agent_conversation
  - [ ] test_voting_flow
- [ ] test_multiturn_api.py
  - [ ] test_multi_turn_session_flow
  - [ ] test_context_persistence
- [ ] test_groupchat_e2e.py
  - [ ] test_complete_groupchat_flow
  - [ ] test_websocket_updates

### 覆蓋率
- [ ] 單元測試覆蓋率 >= 85%
- [ ] 整合測試覆蓋主要流程

---

## 資料庫遷移 ⏳

### 遷移腳本
- [ ] 創建 `009_groupchat_tables.sql`
  - [ ] group_chats 表
  - [ ] group_messages 表
  - [ ] group_participants 表
  - [ ] voting_sessions 表
  - [ ] votes 表
  - [ ] multiturn_sessions 表
  - [ ] conversation_memories 表
  - [ ] 相關索引

### 驗證
- [ ] 遷移腳本可正確執行
- [ ] 回滾腳本可用
- [ ] 索引效能測試通過

---

## 文檔完成 ⏳

### API 文檔
- [ ] Swagger GroupChat API 文檔
- [ ] WebSocket 協議文檔
- [ ] 請求/響應範例
- [ ] 錯誤碼說明

### 開發者文檔
- [ ] GroupChat 使用指南
  - [ ] 發言者選擇策略說明
  - [ ] 終止條件配置
  - [ ] 投票機制說明
- [ ] 多輪對話指南
  - [ ] 會話管理最佳實踐
  - [ ] 上下文維護說明
- [ ] 對話記憶指南
  - [ ] 記憶類型說明
  - [ ] 相關性檢索配置

---

## Sprint 完成標準

### 必須完成 (Must Have)
- [ ] GroupChatManager 可管理多 Agent 對話
- [ ] 6 種發言者選擇策略可用
- [ ] 多輪對話上下文保持
- [ ] 對話記憶存儲和檢索
- [ ] 測試覆蓋率 >= 85%

### 應該完成 (Should Have)
- [ ] 投票機制完整
- [ ] WebSocket 實時更新
- [ ] 文檔完整

### 可以延後 (Could Have)
- [ ] 進階共識算法
- [ ] 對話摘要優化

---

## 依賴確認

### 前置 Sprint
- [ ] Sprint 7 完成
  - [ ] 並行執行基礎設施
- [ ] Sprint 8 完成
  - [ ] Agent 協作協議

### 外部依賴
- [ ] Redis 會話存儲
- [ ] WebSocket 支援配置
- [ ] LLM 服務（發言者選擇）

---

## Sprint 9 完成統計

| Story | 點數 | 狀態 | 測試數 |
|-------|------|------|--------|
| S9-1: GroupChatManager | 8 | ⏳ | 0 |
| S9-2: SpeakerSelector | 5 | ⏳ | 0 |
| S9-3: MultiTurnSessionManager | 8 | ⏳ | 0 |
| S9-4: ConversationMemoryStore | 8 | ⏳ | 0 |
| S9-5: VotingManager | 5 | ⏳ | 0 |
| S9-6: GroupChat API | 8 | ⏳ | 0 |
| **總計** | **42** | **待開發** | **0** |

---

## 相關連結

- [Sprint 9 Plan](./sprint-9-plan.md) - 詳細計劃
- [Phase 2 Overview](./README.md) - Phase 2 概述
- [Sprint 8 Checklist](./sprint-8-checklist.md) - 前置 Sprint
- [Sprint 10 Plan](./sprint-10-plan.md) - 後續 Sprint
