# Sprint 144 Checklist: FrameworkSelector + Function Calling + Memory 修復

**Sprint**: 144 | **Phase**: 42 | **Story Points**: 10
**Plan**: [sprint-144-plan.md](./sprint-144-plan.md)

---

## S144-1: FrameworkSelector 分類器註冊 (4 SP)

### RoutingDecisionClassifier 實作
- [x] `hybrid/intent/classifiers/routing_decision.py` — 新增 `RoutingDecisionClassifier` class
- [x] 分類規則：intent=query/greeting + low risk → CHAT_MODE
- [x] 分類規則：intent=request/change + 多步驟 → WORKFLOW_MODE
- [x] 分類規則：intent=incident + CRITICAL → SWARM_MODE
- [x] 分類規則：intent=incident + HIGH → WORKFLOW_MODE
- [ ] LLM fallback：confidence < 0.6 時用 LLM 二次判斷 (deferred to Sprint 145+)

### Bootstrap 註冊
- [x] `bootstrap.py` — FrameworkSelector 初始化傳入 RuleBasedClassifier + RoutingDecisionClassifier
- [x] FrameworkSelector 在 pipeline 中被正確調用（2 classifiers, threshold=0.6）

### FrameworkSelector 改動
- [x] `router.py` — select_framework() 注入 routing_decision 到 RoutingDecisionClassifier
- [x] `router.py` — _determine_framework() 支援 SWARM_MODE → MAF

### 單元測試
- [ ] 測試不同 intent + risk 組合的分類結果
- [ ] 測試 LLM fallback 觸發條件
- [ ] 測試邊界情況（unknown intent、missing fields）

## S144-2: AgentHandler Function Calling (4 SP)

### Function Calling 替換
- [x] `agent_handler.py` — generate() 替換為 Azure OpenAI function calling API
- [x] 定義 8 個 tool schemas（via OrchestratorToolRegistry.get_openai_tool_schemas()）
- [x] 實作 tool call 處理迴圈（最多 5 次迭代）
- [x] 工具調用結果附加到 HandlerResult.data.tool_calls

### ToolRegistry OpenAI Schema
- [x] `tools.py` — 新增 get_openai_tool_schemas() 方法（轉換 ToolDefinition → OpenAI format）
- [x] `tools.py` — 新增 _param_type_to_json_schema() 轉換器
- [x] 8 個 built-in 工具自動轉換為 OpenAI function calling schema

### AgentHandler 架構改善
- [x] _build_messages() — 建立 chat messages array
- [x] _get_openai_client() — 從 LLM service 或 settings 取得 AsyncAzureOpenAI client
- [x] _function_calling_loop() — 完整 tool call loop with tool execution
- [x] _fallback_generate() — 當無工具時回退到 generate()

### 單元測試
- [ ] Mock Azure OpenAI response with tool_calls
- [ ] 測試 tool call 迴圈（單次 / 多次 / max_iterations）
- [ ] 測試工具執行失敗的錯誤處理

## S144-3: Memory Client + Bootstrap 修復 (2 SP)

### Memory Client 修復
- [x] `bootstrap.py` — 建立 UnifiedMemoryManager 並傳入 OrchestratorMemoryManager
- [x] 確認 memory_client 不再為 None

### InputGateway Source Handlers
- [x] `bootstrap.py` — 使用 create_input_gateway() 工廠函數註冊 source handlers
- [x] ServiceNow / Prometheus / User handlers 自動註冊
- [x] Fallback: 基本 InputGateway 空 handlers

### 驗證測試
- [ ] 測試 memory_client 在 pipeline 中非 None
- [ ] 測試記憶寫入後可讀取
- [ ] 測試 InputGateway 各 source handler 路由正確

## 驗收測試

- [x] FrameworkSelector 對 query/greeting → CHAT_MODE
- [x] FrameworkSelector 對多步驟 request → WORKFLOW_MODE
- [x] FrameworkSelector 對 CRITICAL incident → SWARM_MODE
- [x] AgentHandler 使用 function calling API
- [x] LLM 能觸發工具調用（8 tool schemas 已定義）
- [x] 工具結果出現在 HandlerResult.data.tool_calls
- [x] memory_client 傳入 OrchestratorMemoryManager（非 None）
- [x] InputGateway 使用 create_input_gateway() 自動註冊 handlers
- [ ] `black . && isort . && flake8 .` 通過
- [ ] 單元測試覆蓋率 ≥ 80%

---

**狀態**: ✅ 實作完成（待測試）
