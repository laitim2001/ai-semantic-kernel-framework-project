# Sprint 144 Checklist: FrameworkSelector + Function Calling + Memory 修復

**Sprint**: 144 | **Phase**: 42 | **Story Points**: 10
**Plan**: [sprint-144-plan.md](./sprint-144-plan.md)

---

## S144-1: FrameworkSelector 分類器註冊 (4 SP)

### RoutingDecisionClassifier 實作
- [ ] `hybrid/intent/router.py` — 新增 `RoutingDecisionClassifier` class
- [ ] 分類規則：intent=query/greeting + low risk → CHAT_MODE
- [ ] 分類規則：intent=request/change + 多步驟 → WORKFLOW_MODE
- [ ] 分類規則：intent=incident + 多系統 → SWARM_MODE
- [ ] 分類規則：intent=analysis + 單系統 → AGENT_MODE
- [ ] LLM fallback：confidence < 0.6 時用 LLM 二次判斷

### Bootstrap 註冊
- [ ] `bootstrap.py` — FrameworkSelector 初始化傳入 RoutingDecisionClassifier
- [ ] FrameworkSelector 在 pipeline 中被正確調用（非空 classifiers）

### 單元測試
- [ ] 測試不同 intent + risk 組合的分類結果
- [ ] 測試 LLM fallback 觸發條件
- [ ] 測試邊界情況（unknown intent、missing fields）

## S144-2: AgentHandler Function Calling (4 SP)

### Function Calling 替換
- [ ] `agent_handler.py` — `generate()` 替換為 Azure OpenAI function calling API
- [ ] 定義 6 個 tool schemas（create_task, dispatch_workflow, dispatch_swarm, assess_risk, search_memory, search_knowledge）
- [ ] 實作 tool call 處理迴圈（最多 5 次迭代）
- [ ] 工具調用結果附加到 PipelineResponse.metadata.tool_calls

### ToolRegistry 工具註冊表
- [ ] 新增 `tool_registry.py` — ToolRegistry class
- [ ] 每個工具對應 `async def execute(params) -> dict` 方法
- [ ] Bootstrap 時註冊所有工具到 registry

### 單元測試
- [ ] Mock Azure OpenAI response with tool_calls
- [ ] 測試 tool call 迴圈（單次 / 多次 / max_iterations）
- [ ] 測試工具執行失敗的錯誤處理

## S144-3: Memory Client + Bootstrap 修復 (2 SP)

### Memory Client 修復
- [ ] `bootstrap.py` (~line 209) — 傳入 UnifiedMemoryManager 到 OrchestratorMemoryManager
- [ ] 確認 memory_client 不再為 None

### InputGateway Source Handlers
- [ ] `input_gateway.py` — 註冊 `user` source handler
- [ ] `input_gateway.py` — 註冊 `api` source handler
- [ ] `input_gateway.py` — 註冊 `system` source handler
- [ ] 每個 handler 標準化輸入格式

### 驗證測試
- [ ] 測試 memory_client 在 pipeline 中非 None
- [ ] 測試記憶寫入後可讀取
- [ ] 測試 InputGateway 各 source handler 路由正確

## 驗收測試

- [ ] FrameworkSelector 對 query/greeting → CHAT_MODE
- [ ] FrameworkSelector 對多步驟 request → WORKFLOW_MODE
- [ ] FrameworkSelector 對多系統 incident → SWARM_MODE
- [ ] AgentHandler 使用 function calling API
- [ ] LLM 能觸發工具調用
- [ ] 工具結果出現在 PipelineResponse.metadata
- [ ] memory_client 非 None，記憶讀寫生效
- [ ] InputGateway 處理 3 種 source
- [ ] `black . && isort . && flake8 .` 通過
- [ ] 單元測試覆蓋率 ≥ 80%

---

**狀態**: 📋 計劃中
