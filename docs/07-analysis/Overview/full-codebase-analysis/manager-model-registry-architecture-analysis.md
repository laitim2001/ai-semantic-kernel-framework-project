# ManagerModelRegistry + ManagerModelSelector 架構可行性分析

> 分析日期: 2026-03-22
> 分析師: System Architect
> 範圍: IPA Platform 11-Layer Architecture 整合評估

---

## 1. 現有架構回顧與設計定位

### 1.1 現有 11 層架構中的相關層

```
L1: HTTP Request (API Layer)
L2: Session/Context Management
L3: InputGateway (Source detection)
L4: BusinessIntentRouter (3-tier) + RiskAssessor (7 dimensions)
    ├── PatternMatcher (<10ms)
    ├── SemanticRouter (<100ms)
    └── LLMClassifier (<2s, uses LLMServiceProtocol)
L5: FrameworkSelector (MAF vs Claude SDK vs Hybrid)
    └── CapabilityMatcher → TaskAnalysis → SelectionResult
L6: ExecutionHandler → MAF Builders
    ├── ConcurrentBuilderAdapter
    ├── GroupChatBuilderAdapter
    ├── HandoffBuilderAdapter
    └── MagenticBuilderAdapter (wraps official MagenticBuilder)
L7: LLM Execution (Azure OpenAI / Anthropic Claude)
    ├── LLMServiceProtocol → AzureOpenAILLMService
    ├── LLMServiceFactory (singleton, auto-detect provider)
    └── LLMCallPool (priority queue, rate control)
L8-L11: Response/SSE/Monitoring layers
```

### 1.2 現有 LLM 基礎設施的關鍵限制

| 元件 | 位置 | 限制 |
|------|------|------|
| `LLMServiceFactory` | `integrations/llm/factory.py` | 只支援 `azure` 和 `mock` 兩個 provider，singleton 模式，全域單一實例 |
| `LLMServiceProtocol` | `integrations/llm/protocol.py` | 介面只有 `generate()` / `generate_structured()` / `chat_with_tools()`，無模型選擇語意 |
| `LLMCallPool` | `core/performance/llm_pool.py` | 只做並發控制和優先級排程，不區分 provider |
| `FrameworkSelector` | `claude_sdk/hybrid/selector.py` | 選「框架」(MAF vs Claude SDK)，不選「模型」(gpt-4o vs claude-opus) |
| `MagenticBuilderAdapter` | `agent_framework/builders/magentic.py` | 直接用 `MagenticBuilder` 官方 API，模型由 MAF 內部決定 |

**核心問題**: 現有架構在 L5 選框架、L7 執行時使用固定的單一 LLM provider。沒有「根據角色動態選擇模型」的機制。

---

## 2. 設計可行性評估

### 2.1 能否整合到現有 11 層架構？—— 可以，但需要新增子層

**結論: 可行，但不應放在 L5 旁邊，而是放在 L5.5（新子層）和 L7（基礎設施擴展）。**

原因分析:

- **L5 (FrameworkSelector)** 的職責是選「哪個框架執行」(MAF / Claude SDK / Hybrid)，這是一個正交的決策維度。FrameworkSelector 不應該知道具體模型。
- **ManagerModelSelector** 的職責是選「哪個 LLM 模型」(claude-opus-4 / gpt-4o / claude-haiku)，這是在框架確定之後、執行之前的決策。
- 因此，正確的位置是 **L5.5: Model Selection Layer**（在 FrameworkSelector 之後，ExecutionHandler 之前）。

### 2.2 需要改動的層

| 層 | 改動類型 | 改動範圍 | 風險 |
|----|---------|---------|------|
| **L4** (BusinessIntentRouter) | 無改動 | 0 | - |
| **L5** (FrameworkSelector) | 輸出擴展 | `SelectionResult` 增加 `model_hint` 欄位 | LOW |
| **L5.5** (新增) | 新建 | `ManagerModelSelector` + `ManagerModelRegistry` | MEDIUM |
| **L6** (ExecutionHandler) | 注入改動 | Builder 接收 `model_config` 參數 | MEDIUM |
| **L7** (LLM Execution) | 基礎設施擴展 | `LLMServiceFactory` 支援多 provider 共存 | HIGH |

### 2.3 不需要改動的層

- L1-L3: HTTP/Session/Input 層完全不受影響
- L4: BusinessIntentRouter 的 `RoutingDecision` 已包含 `intent_category` + `risk_level`，可直接作為 ModelSelector 輸入，無需改動
- L8-L11: Response/SSE/Monitoring 層不受影響（但 metrics 可以增加 model 維度）

---

## 3. ManagerModelRegistry 的架構位置

### 3.1 推薦: L7 基礎設施層（與 LLMServiceFactory 同層）

**理由**:

1. **Registry 是配置和能力描述**，不是業務邏輯。它描述的是「系統有哪些可用的 LLM provider」，這屬於基礎設施關注點。
2. **與 LLMServiceFactory 天然互補**: Factory 負責建立連接，Registry 負責描述可用選項和能力。
3. **被多個上層消費**: L5.5 (ModelSelector)、L6 (Builder)、L4 (LLMClassifier 的 model 選擇) 都需要查詢 Registry。放在基礎設施層符合依賴方向（上層依賴下層）。

### 3.2 不推薦放在 L5 的原因

如果放在 L5（與 FrameworkSelector 旁邊），會造成:
- FrameworkSelector 和 ModelRegistry 互相耦合
- 違反 Single Responsibility: L5 同時負責「選框架」和「管模型配置」
- 依賴方向錯誤: L6 Builder 需要查詢 Registry，但 L6 不應依賴 L5

### 3.3 推薦的模組結構

```
backend/src/integrations/llm/          # L7 基礎設施
├── protocol.py                        # LLMServiceProtocol (不變)
├── factory.py                         # LLMServiceFactory (擴展多 provider)
├── azure_openai.py                    # AzureOpenAILLMService (不變)
├── mock.py                            # MockLLMService (不變)
├── cached.py                          # CachedLLMService (不變)
├── model_registry.py                  # 新增: ManagerModelRegistry
└── model_selector.py                  # 新增: ManagerModelSelector

backend/config/                        # 配置
└── model_registry.yaml                # 新增: 模型配置檔
```

---

## 4. 每個 Agent/Participant 用不同模型的技術挑戰

### 4.1 MagenticOne Manager 使用不同模型的挑戰

**挑戰 1: MAF 官方 API 的模型綁定**

```python
# 目前的 MagenticBuilderAdapter 用法
from agent_framework.orchestrations import MagenticBuilder
self._builder = MagenticBuilder()
# MagenticBuilder 內部使用單一 ChatCompletionClient
# 沒有「Manager 用 Model A, Worker 用 Model B」的官方 API
```

MAF 的 `MagenticBuilder` 在構建時接受 `ChatCompletionClient`，該 client 綁定到單一模型。要讓 Manager 和 Worker 用不同模型，需要:

**方案 A (推薦): Participant-level Model Override**
```python
class MagenticBuilderAdapter:
    def build(self, manager_model_config=None, worker_model_configs=None):
        # Manager 使用指定的 ChatCompletionClient
        manager_client = self._create_client(manager_model_config)
        # 每個 Worker Participant 可以有自己的 client
        for worker in workers:
            worker_client = self._create_client(
                worker_model_configs.get(worker.name, default_config)
            )
```

**方案 B: 代理模式 (Proxy Pattern)**
建立一個 `RoutingChatCompletionClient`，在內部根據呼叫者身份路由到不同的底層 client。

**風險評估**: MAF 是 Preview 版本 (1.0.0b251204)，`MagenticBuilder` 是否支援 per-participant model 需要驗證官方 API。如果官方不支援，只能用 Proxy Pattern。

### 4.2 Swarm Worker 使用不同模型的挑戰

**相對簡單**。目前 `SwarmIntegration` 透過 callback 追蹤 worker 狀態，每個 worker 的執行是獨立的。

```python
# worker_executor.py 中每個 worker 獨立執行
# 只需在建立 worker 時注入不同的 LLMServiceProtocol 實例
class WorkerExecutor:
    async def execute(self, worker_config):
        llm_service = model_registry.get_service(worker_config.model_id)
        # 用指定模型執行 worker 任務
```

### 4.3 跨 Provider 的語意差異

| 差異維度 | Azure OpenAI (GPT) | Anthropic Claude | 影響 |
|---------|--------------------|--------------------|------|
| Tool Calling 格式 | OpenAI function calling schema | Anthropic tool_use | 需要格式轉換層 |
| Streaming 格式 | SSE with `data: [DONE]` | SSE with `event: message_stop` | SSE adapter 需要 |
| Token 計算 | tiktoken | Anthropic tokenizer | 預算控制不同 |
| System Prompt | `messages[0].role = "system"` | `system` parameter | Prompt 構建不同 |
| Max Context | 128K (GPT-4o) | 200K (Claude) | 策略不同 |

**結論**: 需要一個 **Model Capability Descriptor** 來抽象這些差異，Registry 的 YAML schema 必須包含這些維度。

---

## 5. YAML 配置 Schema 設計建議

```yaml
# backend/config/model_registry.yaml
version: "1.0"

# ============================================================
# Provider Definitions
# ============================================================
providers:
  azure_openai:
    type: azure_openai
    endpoint: "${AZURE_OPENAI_ENDPOINT}"
    api_key: "${AZURE_OPENAI_API_KEY}"
    api_version: "2025-03-01-preview"
    rate_limit:
      max_concurrent: 10
      max_per_minute: 120
    health_check:
      enabled: true
      interval_seconds: 60

  anthropic:
    type: anthropic
    api_key: "${ANTHROPIC_API_KEY}"
    rate_limit:
      max_concurrent: 5
      max_per_minute: 60
    health_check:
      enabled: true
      interval_seconds: 60

# ============================================================
# Model Definitions
# ============================================================
models:
  gpt-4o:
    provider: azure_openai
    deployment_name: "gpt-4o"
    capabilities:
      max_context_tokens: 128000
      max_output_tokens: 16384
      supports_tool_calling: true
      supports_structured_output: true
      supports_vision: true
      supports_streaming: true
      tool_call_format: "openai_function"
    cost:
      input_per_1k_tokens: 0.005
      output_per_1k_tokens: 0.015
    tags: ["general", "fast", "cost-effective"]

  gpt-4o-mini:
    provider: azure_openai
    deployment_name: "gpt-4o-mini"
    capabilities:
      max_context_tokens: 128000
      max_output_tokens: 16384
      supports_tool_calling: true
      supports_structured_output: true
      supports_vision: true
      supports_streaming: true
      tool_call_format: "openai_function"
    cost:
      input_per_1k_tokens: 0.00015
      output_per_1k_tokens: 0.0006
    tags: ["fast", "cheap", "worker"]

  claude-opus-4:
    provider: anthropic
    model_id: "claude-opus-4-20250514"
    capabilities:
      max_context_tokens: 200000
      max_output_tokens: 32000
      supports_tool_calling: true
      supports_structured_output: true
      supports_vision: true
      supports_streaming: true
      supports_extended_thinking: true
      tool_call_format: "anthropic_tool_use"
    cost:
      input_per_1k_tokens: 0.015
      output_per_1k_tokens: 0.075
    tags: ["reasoning", "complex", "manager"]

  claude-sonnet-4:
    provider: anthropic
    model_id: "claude-sonnet-4-20250514"
    capabilities:
      max_context_tokens: 200000
      max_output_tokens: 16000
      supports_tool_calling: true
      supports_structured_output: true
      supports_vision: true
      supports_streaming: true
      supports_extended_thinking: true
      tool_call_format: "anthropic_tool_use"
    cost:
      input_per_1k_tokens: 0.003
      output_per_1k_tokens: 0.015
    tags: ["balanced", "worker", "general"]

  claude-haiku-3.5:
    provider: anthropic
    model_id: "claude-3-5-haiku-20241022"
    capabilities:
      max_context_tokens: 200000
      max_output_tokens: 8192
      supports_tool_calling: true
      supports_structured_output: true
      supports_vision: false
      supports_streaming: true
      supports_extended_thinking: false
      tool_call_format: "anthropic_tool_use"
    cost:
      input_per_1k_tokens: 0.001
      output_per_1k_tokens: 0.005
    tags: ["fast", "cheap", "classification"]

# ============================================================
# Role-based Model Assignment (Default Policies)
# ============================================================
role_assignments:
  # MagenticOne Manager — needs strong reasoning
  magentic_manager:
    primary: claude-opus-4
    fallback: gpt-4o
    selection_criteria:
      min_context_tokens: 100000
      requires_extended_thinking: true

  # Intent Classification (L4 LLMClassifier)
  intent_classifier:
    primary: claude-haiku-3.5
    fallback: gpt-4o-mini
    selection_criteria:
      max_cost_per_call: 0.01
      max_latency_ms: 2000

  # Swarm Workers — default
  swarm_worker_default:
    primary: claude-sonnet-4
    fallback: gpt-4o
    selection_criteria:
      supports_tool_calling: true

  # Swarm Workers — specialized research
  swarm_worker_research:
    primary: gpt-4o
    fallback: claude-sonnet-4
    selection_criteria:
      supports_tool_calling: true

  # Task Decomposition
  task_decomposer:
    primary: claude-opus-4
    fallback: gpt-4o
    selection_criteria:
      supports_structured_output: true
      min_context_tokens: 50000

# ============================================================
# Dynamic Selection Rules (Intent + Risk → Model)
# ============================================================
dynamic_rules:
  # CRITICAL risk → use strongest model
  - condition:
      risk_level: critical
    override:
      model: claude-opus-4
      reason: "Critical risk requires strongest reasoning capability"

  # Simple QUERY → use cheapest model
  - condition:
      intent_category: query
      risk_level: low
    override:
      model: claude-haiku-3.5
      reason: "Low-risk query can use cost-effective model"

  # INCIDENT with system_down → use fastest model
  - condition:
      intent_category: incident
      sub_intent: system_down
    override:
      model: gpt-4o
      reason: "System down needs fastest response time"

  # Complex CHANGE → use best reasoning
  - condition:
      intent_category: change
      risk_level: high
    override:
      model: claude-opus-4
      reason: "High-risk change needs thorough analysis"
```

---

## 6. 與現有 LLMServiceProtocol / LLMServiceFactory 的關係

### 6.1 關係圖

```
                        ManagerModelRegistry (新增)
                            │ 讀取 YAML 配置
                            │ 管理 provider + model 定義
                            ▼
                    ManagerModelSelector (新增)
                        │ 輸入: intent + risk + role
                        │ 輸出: ModelSelection(model_id, provider)
                        ▼
                LLMServiceFactory (擴展)
                    │ 原有: create(provider="azure") → 單一實例
                    │ 新增: create_for_model(model_id="claude-opus-4") → 指定模型實例
                    ▼
            ┌───────────────────────┐
            │  LLMServiceProtocol   │ (不變)
            │  generate()           │
            │  generate_structured()│
            │  chat_with_tools()    │
            └───────┬───────────────┘
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
  AzureOpenAI   AnthropicLLM    MockLLM
  LLMService    Service(新增)    Service
```

### 6.2 具體改動

**LLMServiceProtocol** — 不需要改動。介面足夠通用。

**LLMServiceFactory** — 需要擴展:
```python
class LLMServiceFactory:
    @classmethod
    def create_for_model(
        cls,
        model_id: str,
        registry: ManagerModelRegistry,
    ) -> LLMServiceProtocol:
        """根據 model_id 從 registry 取得配置，建立對應的 LLM service。"""
        model_config = registry.get_model(model_id)
        provider_config = registry.get_provider(model_config.provider)

        if provider_config.type == "azure_openai":
            return AzureOpenAILLMService(
                endpoint=provider_config.endpoint,
                api_key=provider_config.api_key,
                deployment_name=model_config.deployment_name,
            )
        elif provider_config.type == "anthropic":
            return AnthropicLLMService(  # 新增
                api_key=provider_config.api_key,
                model_id=model_config.model_id,
            )
```

**新增 AnthropicLLMService** — 實現 `LLMServiceProtocol`，使用 `anthropic.AsyncAnthropic` client。

**LLMCallPool** — 需要擴展為 per-provider pool:
```python
class LLMCallPool:
    # 目前: 全域單一 pool
    # 改為: per-provider pool，每個 provider 有獨立的並發和速率限制
    _provider_pools: Dict[str, ProviderPool]
```

---

## 7. 潛在風險和限制

### 7.1 HIGH 風險

| 風險 | 描述 | 緩解措施 |
|------|------|---------|
| **MAF API 限制** | `MagenticBuilder` 官方 API 可能不支援 per-participant model。MAF 是 Preview 版本，行為未穩定。 | 先驗證官方 API。若不支援，使用 Proxy ChatCompletionClient 模式繞過。需要維護自訂的 RoutingClient。 |
| **跨 Provider 語意差異** | OpenAI 和 Anthropic 的 tool calling、streaming、prompt 格式完全不同。統一抽象可能丟失能力。 | 在 `LLMServiceProtocol` 的 `chat_with_tools()` 中做格式轉換。保留 `tool_call_format` metadata 讓上層感知差異。 |
| **Anthropic LLMService 不存在** | 目前只有 `AzureOpenAILLMService`。要支援 Claude 作為 LLM Provider（而非透過 Claude SDK），需要新增完整實現。 | 可以利用現有 `claude_sdk/client.py` 的 `anthropic.AsyncAnthropic`，但需要包裝為 `LLMServiceProtocol` 介面。注意區分「Claude SDK 做 Agent」和「Claude 做 LLM Provider」。 |

### 7.2 MEDIUM 風險

| 風險 | 描述 | 緩解措施 |
|------|------|---------|
| **成本失控** | 動態選模型可能無意中頻繁使用昂貴模型 (claude-opus-4)。 | Registry YAML 中設定 `max_cost_per_call` 限制；LLMCallPool 增加 per-model 預算追蹤。 |
| **延遲不可預測** | 不同 provider 延遲差異大 (Azure ~200ms, Anthropic ~500ms)。跨 provider 混用可能影響 UX。 | Registry 中標註 `avg_latency_ms`，ModelSelector 可設定延遲上限。Swarm worker 並行執行時，最慢的 provider 決定整體延遲。 |
| **Failover 複雜度** | Primary 模型不可用時切換 fallback，涉及不同 provider 的 client 建立、認證、格式轉換。 | Registry 中定義 `fallback` 鏈；LLMServiceFactory 預建立 fallback service 實例（lazy init）。 |
| **配置膨脹** | YAML 配置隨模型和規則增加會變得龐大難維護。 | 將 `providers`、`models`、`role_assignments`、`dynamic_rules` 分為 4 個 YAML 檔案。 |

### 7.3 LOW 風險

| 風險 | 描述 | 緩解措施 |
|------|------|---------|
| **測試複雜度** | 需要 mock 多個 provider 的行為。 | 擴展現有 `MockLLMService`，增加 model_id 感知。 |
| **監控維度增加** | 需要按 model 追蹤延遲、成本、錯誤率。 | 擴展 `OrchestrationMetricsCollector`，增加 `model_id` label。 |

---

## 8. 實施路線圖建議

### Phase 1: 基礎設施 (2 Sprints)
1. 建立 `model_registry.yaml` schema 和載入機制
2. 實現 `ManagerModelRegistry` (YAML parser + in-memory cache)
3. 新增 `AnthropicLLMService` (實現 `LLMServiceProtocol`)
4. 擴展 `LLMServiceFactory.create_for_model()`
5. 擴展 `LLMCallPool` 為 per-provider

### Phase 2: 選擇引擎 (1 Sprint)
1. 實現 `ManagerModelSelector`
2. 整合 `RoutingDecision` (intent + risk) 作為輸入
3. 實現 `role_assignments` 和 `dynamic_rules` 匹配邏輯
4. 添加 fallback 和健康檢查機制

### Phase 3: MagenticOne 整合 (1 Sprint)
1. 驗證 MAF `MagenticBuilder` per-participant model API
2. 修改 `MagenticBuilderAdapter` 接收 model_config
3. 實現 Proxy ChatCompletionClient（如官方不支援）
4. Manager 用 Claude Opus，Workers 用可配置模型

### Phase 4: Swarm 整合 + E2E 驗證 (1 Sprint)
1. `WorkerExecutor` 根據 worker_type 查詢 ModelSelector
2. `SwarmIntegration` 追蹤每個 worker 使用的模型
3. E2E 測試: intent → model selection → execution → response
4. 成本和延遲監控面板

---

## 9. 架構決策記錄 (ADR)

### ADR-001: ManagerModelRegistry 放在 L7 (基礎設施層)

- **決策**: Registry 作為基礎設施元件，與 LLMServiceFactory 同層
- **理由**: 符合依賴方向；被多個上層消費；配置管理屬於基礎設施關注點
- **取捨**: 犧牲了與 FrameworkSelector 的直接關聯性，但獲得了更好的解耦

### ADR-002: ManagerModelSelector 作為 L5.5 新子層

- **決策**: 在 FrameworkSelector (L5) 和 ExecutionHandler (L6) 之間新增 Model Selection 子層
- **理由**: 模型選擇是框架選擇之後、執行之前的正交決策
- **取捨**: 增加了一個決策步驟的延遲 (<5ms for in-memory lookup)，但獲得了清晰的職責邊界

### ADR-003: 使用 YAML 而非資料庫存儲模型配置

- **決策**: 模型配置使用 YAML 檔案，應用啟動時載入到記憶體
- **理由**: 模型配置是低頻變更的靜態配置；YAML 可版本控制；啟動時載入消除運行時 I/O
- **取捨**: 變更需要重啟（或實現 hot-reload）。未來可考慮 Redis 配置熱更新

### ADR-004: LLMServiceProtocol 不變，Factory 擴展

- **決策**: 保持現有 Protocol 介面，透過 Factory 新增 `create_for_model()` 方法
- **理由**: 最小改動原則；現有 generate/chat_with_tools 介面足夠通用
- **取捨**: tool_call_format 差異需要在實現層處理，Protocol 層不感知

---

## 10. 結論

ManagerModelRegistry + ManagerModelSelector 的設計**架構上可行**，可以整合到現有 11 層架構中。關鍵決策:

1. **Registry 放 L7** (基礎設施層，與 LLMServiceFactory 同層)
2. **Selector 放 L5.5** (新子層，FrameworkSelector 之後，ExecutionHandler 之前)
3. **最大風險是 MAF API 限制** — 需要先驗證 MagenticBuilder 是否支援 per-participant model
4. **需要新增 AnthropicLLMService** — 目前只有 Azure OpenAI 實現
5. **YAML 配置 schema** 應包含 providers、models、role_assignments、dynamic_rules 四個段落
6. **預估 5 個 Sprint** 完成全部整合

整體設計遵循了現有架構的依賴方向和職責邊界，不會破壞已有的 L4 路由和 L5 框架選擇邏輯。
