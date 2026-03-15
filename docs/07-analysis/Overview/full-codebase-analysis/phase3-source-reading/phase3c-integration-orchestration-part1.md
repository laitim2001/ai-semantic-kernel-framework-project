# Phase 3C: Integration Layer - Orchestration Part 1

## Three-Tier Intent Routing System (Phase 28)

**Scope**: `backend/src/integrations/orchestration/` — intent_router/, input_gateway/, input/, guided_dialog/, contracts.py
**Files Analyzed**: 53 Python files + 3 YAML + 1 JSON
**Total LOC**: ~16,000+
**Sprints**: S91-S99 (Phase 28), S115 (Phase 32 Azure upgrade), S116 (Phase 34 contracts), S128 (LLM migration)

---

## 1. Architecture Overview

The orchestration module implements an enterprise IT Service Management (ITSM) intent routing system based on ITIL framework categories. It processes user inputs (text, webhooks, alerts) through a cascading three-tier classification pipeline with decreasing speed but increasing accuracy.

```
Raw Input (chat/webhook/alert)
    |
    v
InputGateway (source detection + normalization)
    |
    v
+--------------------------------------------------+
| Tier 1: PatternMatcher     (< 10ms, conf >= 0.90)|  -- Rule-based regex
| Tier 2: SemanticRouter      (< 100ms, sim >= 0.85)|  -- Vector similarity
| Tier 3: LLMClassifier       (< 2000ms)           |  -- Real LLM API call
+--------------------------------------------------+
    |
    v
RoutingDecision
    |
    +---> CompletenessChecker (missing fields?)
    |         |
    |         v (if incomplete)
    |     GuidedDialogEngine (multi-turn questions)
    |
    +---> RiskAssessor
    +---> HITLController (if HIGH/CRITICAL)
```

### Intent Categories (ITIL-based)

| Category | Description | Example |
|----------|-------------|---------|
| INCIDENT | Unplanned interruption/degradation | "ETL pipeline failed", "系統當機" |
| REQUEST  | Formal service request | "需要新帳號", "申請 VPN" |
| CHANGE   | Modification to IT infrastructure | "更新防火牆規則", "release deployment" |
| QUERY    | General inquiry | "伺服器狀態?", "how to reset password" |
| UNKNOWN  | Cannot classify with confidence | Ambiguous or off-topic |

---

## 2. Core Contracts (Sprint 116)

**File**: `orchestration/contracts.py`

Defines the L4a (Input Processing) <-> L4b (Decision Engine) interface split:

### Data Flow Objects

| Object | Role | Key Fields |
|--------|------|------------|
| `RoutingRequest` | L4a output / L4b input | `query`, `intent_hint`, `context`, `source: InputSource`, `request_id`, `priority` |
| `RoutingResult` | L4b output | `intent`, `sub_intent`, `confidence`, `matched_layer`, `workflow_type`, `risk_level`, `completeness`, `missing_fields` |

### Protocols (ABCs)

| Protocol | Layer | Method |
|----------|-------|--------|
| `InputGatewayProtocol` | L4a | `receive(raw_input) -> RoutingRequest`, `validate(raw_input) -> bool` |
| `RouterProtocol` | L4b | `route(request) -> RoutingResult`, `get_available_layers() -> List[str]` |
| `RoutingLayerProtocol` | L4b per-tier | `classify(request) -> Optional[RoutingResult]`, `get_layer_name()`, `get_confidence_threshold()` |
| `DecisionEngineProtocol` | L4b pipeline | `route(request) -> RoutingPipelineResult`, `get_pipeline_config()` |

### InputSource Enum

Supports: `WEBHOOK_SERVICENOW`, `WEBHOOK_PROMETHEUS`, `HTTP_API`, `SSE_STREAM`, `USER_CHAT`, `RITM`, `UNKNOWN`

### Adapter Functions

Two bridge functions convert between Sprint 93/95 legacy models and Sprint 116 contracts:
- `incoming_request_to_routing_request()` — maps `IncomingRequest.content` -> `RoutingRequest.query`
- `routing_decision_to_routing_result()` — maps `RoutingDecision` -> `RoutingResult`, handling enum `.value` extraction

**File**: `intent_router/contracts.py`

Adds `RoutingPipelineResult` which wraps a `RoutingResult` plus per-layer execution metrics (`LayerExecutionMetric`: layer_name, execution_time_ms, confidence, matched).

---

## 3. Tier 1: PatternMatcher (Sprint 91)

**Files**: `intent_router/pattern_matcher/matcher.py`, `rules.yaml`
**Performance Target**: < 10ms
**Confidence Threshold**: >= 0.90 (configurable via `PATTERN_CONFIDENCE_THRESHOLD` env var)

### Implementation: Real, Rule-Based, Production-Ready

The PatternMatcher is a **fully functional** regex-based classifier:

1. **YAML Loading**: Loads rules from `rules.yaml` (or accepts a dict). Each rule has: `id`, `category`, `sub_intent`, `patterns[]`, `priority`, `workflow_type`, `risk_level`, `enabled`.

2. **Pre-compilation**: All regex patterns are compiled at init time into `CompiledRule` objects (`re.compile(pattern, re.IGNORECASE)`). Invalid patterns are logged and skipped.

3. **Matching**: Rules are sorted by priority (descending). For each rule, each compiled pattern is tested via `regex.search(input)`. First match wins.

4. **Confidence**: Fixed at `DEFAULT_CONFIDENCE = 0.95` for all pattern matches (not dynamically scored).

### YAML Rules Catalog (rules.yaml)

The YAML defines **30+ rules** across 4 ITIL categories with Chinese + English regex patterns:

#### INCIDENT Rules (10+ rules)

| Rule ID | Sub-Intent | Sample Patterns | Workflow | Risk |
|---------|-----------|-----------------|----------|------|
| `incident_etl_failure` | etl_failure | `ETL.*失敗`, `ETL.*fail`, `pipeline.*error` | MAGENTIC | HIGH |
| `incident_system_down` | system_down | `系統.*當機`, `系統.*掛掉`, `service.*down`, `system.*unavailable` | MAGENTIC | CRITICAL |
| `incident_network_issue` | network_issue | `網路.*斷`, `network.*down`, `DNS.*fail` | SEQUENTIAL | HIGH |
| `incident_database_error` | database_error | `資料庫.*錯誤`, `DB.*error`, `database.*fail` | MAGENTIC | HIGH |
| `incident_login_failure` | login_failure | `無法登入`, `login.*fail`, `認證.*失敗` | SIMPLE | MEDIUM |
| `incident_disk_space` | disk_space | `磁碟.*滿`, `disk.*full`, `儲存空間不足` | SEQUENTIAL | HIGH |
| `incident_performance` | performance_degradation | `系統.*慢`, `效能.*下降`, `response.*slow` | SEQUENTIAL | MEDIUM |
| `incident_api_error` | api_error | `API.*錯誤`, `API.*fail`, `端點.*無回應` | SEQUENTIAL | HIGH |
| `incident_batch_failure` | batch_failure | `批次.*失敗`, `batch.*fail`, `排程.*錯誤` | MAGENTIC | HIGH |
| `incident_backup_failure` | backup_failure | `備份.*失敗`, `backup.*fail` | SEQUENTIAL | HIGH |

#### REQUEST Rules (8+ rules)

| Rule ID | Sub-Intent | Sample Patterns | Workflow | Risk |
|---------|-----------|-----------------|----------|------|
| `request_new_account` | new_account | `新帳號`, `new account`, `建立帳號` | SIMPLE | LOW |
| `request_permission` | permission_change | `權限`, `permission`, `存取權` | SIMPLE | MEDIUM |
| `request_vpn` | vpn_access | `VPN`, `遠端連線` | SIMPLE | LOW |
| `request_software` | software_install | `安裝軟體`, `install.*software` | SIMPLE | LOW |
| `request_vm` | vm_provision | `虛擬機`, `VM.*provision`, `開機器` | SEQUENTIAL | MEDIUM |
| `request_certificate` | certificate | `憑證`, `certificate`, `SSL` | SIMPLE | LOW |
| `request_data_extract` | data_extract | `資料.*匯出`, `data.*export`, `報表` | SIMPLE | LOW |
| `request_password_reset` | password_reset | `密碼重設`, `reset.*password`, `忘記密碼` | SIMPLE | LOW |

#### CHANGE Rules (6+ rules)

| Rule ID | Sub-Intent | Sample Patterns | Workflow | Risk |
|---------|-----------|-----------------|----------|------|
| `change_release` | release_deployment | `版本.*部署`, `release.*deploy`, `上版` | MAGENTIC | HIGH |
| `change_config` | configuration_update | `設定.*更新`, `config.*change`, `參數調整` | SEQUENTIAL | MEDIUM |
| `change_firewall` | firewall_rule | `防火牆`, `firewall.*rule` | SEQUENTIAL | HIGH |
| `change_database` | database_change | `資料庫.*變更`, `DB.*migration`, `schema.*change` | MAGENTIC | HIGH |
| `change_dns` | dns_update | `DNS.*更新`, `domain.*change` | SEQUENTIAL | MEDIUM |
| `change_maintenance` | maintenance_window | `維護窗口`, `maintenance.*window` | SEQUENTIAL | MEDIUM |

#### QUERY Rules (5+ rules)

| Rule ID | Sub-Intent | Sample Patterns | Workflow | Risk |
|---------|-----------|-----------------|----------|------|
| `query_status` | system_status | `狀態`, `status`, `健康檢查` | SIMPLE | LOW |
| `query_howto` | how_to | `如何`, `怎麼`, `how to`, `教學` | SIMPLE | LOW |
| `query_policy` | policy_inquiry | `政策`, `policy`, `規定`, `SLA` | SIMPLE | LOW |
| `query_capacity` | capacity_inquiry | `容量`, `capacity`, `資源使用` | SIMPLE | LOW |
| `query_audit` | audit_inquiry | `稽核`, `audit`, `合規` | SIMPLE | LOW |

### Assessment

- **Real or Mock?**: Fully real, production-ready rule engine.
- **Bilingual**: All patterns cover both Traditional Chinese and English variants.
- **Performance**: Pre-compiled regex + priority-sorted scan = well under 10ms target.
- **Limitation**: Fixed confidence of 0.95 for all matches (no scoring granularity).
- **Extensibility**: YAML-driven, new rules can be added without code changes.

---

## 4. Tier 2: SemanticRouter (Sprint 92 + Sprint 115)

**Files**: `intent_router/semantic_router/router.py`, `routes.py`, `azure_semantic_router.py`, `azure_search_client.py`, `embedding_service.py`, `setup_index.py`, `route_manager.py`, `migration.py`

### Two Implementations

The semantic router has **two independent implementations**:

#### 4a. Original SemanticRouter (Sprint 92) — Aurelio Library

**File**: `semantic_router/router.py`

Uses the `semantic-router` library by Aurelio Labs with OpenAI/Azure OpenAI encoders.

**How it works**:
1. **Encoder Selection**: Checks for `AZURE_OPENAI_API_KEY` env var. If present, uses `AzureOpenAIEncoder`; otherwise falls back to `OpenAIEncoder`.
2. **Route Loading**: Converts `SemanticRoute` definitions into Aurelio `Route` objects with utterances.
3. **Classification**: Calls `RouteLayer(encoder=encoder, routes=routes)` which builds a vector index of route utterances. At query time, encodes the input and finds nearest route via cosine similarity.
4. **Graceful Degradation**: If `semantic-router` library is not installed, the flag `_SEMANTIC_ROUTER_AVAILABLE` is False, and `route()` returns `SemanticRouteResult.no_match()`.

**Real Embeddings?**: **YES** — when the library is installed and API keys are configured, it calls real OpenAI/Azure OpenAI embedding APIs. Without keys/library, returns no-match (not mock data, just graceful skip).

#### 4b. AzureSemanticRouter (Sprint 115) — Azure AI Search

**File**: `semantic_router/azure_semantic_router.py`

A production-grade alternative using Azure AI Search for vector similarity:

1. **EmbeddingService** (`embedding_service.py`): Uses `openai.AsyncAzureOpenAI` client to call Azure OpenAI embedding API (`text-embedding-ada-002` by default). Features:
   - LRU cache (OrderedDict, configurable size, default 1024 entries)
   - Exponential backoff retry (3 retries, handles `RateLimitError`)
   - Real async API calls to Azure OpenAI

2. **AzureSearchClient** (`azure_search_client.py`): Wraps Azure AI Search SDK for vector search operations. Features:
   - `search_vectors()` method for KNN vector queries
   - `upload_documents()` for index population
   - Uses `azure.search.documents.aio.SearchClient`

3. **AzureSemanticRouter**: Orchestrates embedding generation + vector search:
   - Generates embedding for user input via `EmbeddingService`
   - Searches Azure AI Search index via `AzureSearchClient`
   - Maps results to `SemanticRouteResult` objects
   - Applies `similarity_threshold` (default 0.85)

4. **Migration** (`migration.py`): Script to sync predefined routes from Python to Azure AI Search index — generates embeddings for all utterances and uploads them.

5. **Route Manager** (`route_manager.py`): CRUD operations for managing semantic routes in Azure AI Search index.

6. **Index Schema** (`index_schema.json`): Azure AI Search index definition with vector fields.

**Real Embeddings?**: **YES** — `EmbeddingService` makes real `AsyncAzureOpenAI` API calls. No mock fallback; requires valid Azure credentials.

### Route Definitions (routes.py)

15 predefined `SemanticRoute` objects in `IT_SEMANTIC_ROUTES` list, each with 6-10 example utterances (bilingual Chinese/English):

| Route Name | Category | Sub-Intent | Sample Utterances |
|-----------|----------|-----------|-------------------|
| `etl_pipeline_failure` | INCIDENT | etl_failure | "ETL pipeline 執行失敗", "數據管道出現異常" |
| `system_unavailable` | INCIDENT | system_down | "系統完全無法使用", "服務中斷了" |
| `network_connectivity` | INCIDENT | network_issue | "網路連接不穩定", "VPN 連不上" |
| `database_incident` | INCIDENT | database_error | "資料庫連接錯誤", "DB 回應超時" |
| `performance_degradation` | INCIDENT | performance_degradation | "系統回應非常慢", "頁面載入很慢" |
| `account_creation` | REQUEST | new_account | "申請一個新的帳號", "new user account needed" |
| `permission_change` | REQUEST | permission_change | "修改我的存取權限", "需要更高的權限" |
| `software_installation` | REQUEST | software_install | "安裝 Visual Studio", "需要安裝軟體" |
| `vpn_access` | REQUEST | vpn_access | "設定 VPN 連線", "遠端存取申請" |
| `release_deployment` | CHANGE | release_deployment | "準備部署新版本", "release 上版申請" |
| `config_change` | CHANGE | configuration_update | "更新生產環境設定", "修改系統參數" |
| `firewall_change` | CHANGE | firewall_rule | "開放防火牆連接埠", "新增防火牆規則" |
| `system_status` | QUERY | system_status | "檢查系統目前狀態", "服務健康狀況如何" |
| `how_to` | QUERY | how_to | "如何重設密碼", "怎麼申請 VPN" |
| `policy_inquiry` | QUERY | policy_inquiry | "密碼政策是什麼", "SLA 規定" |

### Which Router Is Used in Production?

The `BusinessIntentRouter` (Sprint 93) is wired to the **original SemanticRouter** class via the `create_router()` factory. The `AzureSemanticRouter` is a Sprint 115 alternative that can be swapped in but is not the default wiring.

### Assessment

- **Real or Mock?**: Both implementations use **real embeddings** when credentials are present. No mock/simulated similarity.
- **Graceful Degradation**: Original router silently skips if library not installed. Azure router requires Azure infrastructure.
- **Route Coverage**: 15 routes with 90-150 total utterances covering IT service categories.

---

## 5. Tier 3: LLMClassifier (Sprint 92 + Sprint 128)

**Files**: `intent_router/llm_classifier/classifier.py`, `prompts.py`, `cache.py`, `evaluation.py`

### Implementation: Real LLM Calls via LLMServiceProtocol

**Does it call a real LLM?**: **YES** — via the `LLMServiceProtocol` abstraction.

#### Classification Flow

1. **Input**: User text + optional `include_completeness` flag
2. **Cache Check**: If `ClassificationCache` is configured, checks for cached result by input hash
3. **Prompt Construction**: Calls `get_classification_prompt(user_input)` to build a structured system+user prompt
4. **LLM Call**: Calls `self._llm_service.call_llm(prompt, max_tokens, temperature)` via the `LLMServiceProtocol` interface
5. **Response Parsing**: Extracts JSON from LLM response using regex (`re.search(r'\{.*\}', response, re.DOTALL)`)
6. **Result Construction**: Maps parsed JSON to `LLMClassificationResult` with `intent_category`, `sub_intent`, `confidence`, `completeness`, `reasoning`
7. **Cache Store**: Caches successful results

#### LLMServiceProtocol

The classifier does **not** call any specific LLM provider directly. It uses `LLMServiceProtocol` from `src/integrations/llm/`, which supports:
- **Azure OpenAI** (production)
- **Anthropic Claude** (alternative)
- **Mock** (development/testing)

The `create_router_with_llm()` factory uses `LLMServiceFactory.create(use_cache=True, cache_ttl=1800)` to auto-detect and create the appropriate provider from environment variables.

#### Graceful Degradation

When `llm_service is None` (no LLM configured), the `classify()` method returns:
```python
LLMClassificationResult(
    intent_category=ITIntentCategory.UNKNOWN,
    confidence=0.0,
    reasoning="LLM service not configured"
)
```

This means **Layer 3 silently fails open** — it does not crash, it returns UNKNOWN.

#### Classification Prompt (prompts.py)

The `CLASSIFICATION_PROMPT` is a structured system prompt that instructs the LLM to:
- Classify into one of: `incident`, `request`, `change`, `query`
- Provide a `sub_intent` from a defined list with examples
- Assess `confidence` (0.0-1.0)
- Evaluate `completeness` with `is_complete`, `missing_fields`, `completeness_score`
- Provide `reasoning` explanation
- Return structured JSON output

The prompt includes sub-intent examples per category and required field definitions.

#### Classification Cache (cache.py)

`ClassificationCache` provides:
- In-memory dictionary cache keyed by input text hash
- Configurable TTL (default 1800 seconds = 30 min)
- Max size limit with LRU eviction
- Cache hit/miss metrics
- Thread-safe (uses dict, no explicit locks — potential issue under concurrent load)

#### Evaluation Suite (evaluation.py)

`evaluate_classifier()` runs a set of `EVALUATION_CASES` — predefined test inputs with expected categories/sub-intents — against the classifier and reports accuracy metrics. Used for quality validation, not production routing.

### Assessment

- **Real or Mock?**: **Real LLM calls** when LLM service is configured. Mock when no API keys.
- **Provider**: Azure OpenAI (production default via LLMServiceFactory), also supports Anthropic/mock.
- **Fallback**: Returns UNKNOWN with 0.0 confidence when LLM unavailable.
- **Caching**: In-memory with TTL to reduce repeated LLM calls.
- **Cost Control**: Temperature 0.0, max_tokens 500 — deterministic, compact responses.

---

## 6. BusinessIntentRouter — The Coordinator (Sprint 93)

**File**: `intent_router/router.py`

### Three-Tier Cascade Logic

```python
async def route(self, user_input: str) -> RoutingDecision:
    # 1. Validate input
    if empty -> return UNKNOWN

    # 2. Layer 1: Pattern Matcher (synchronous)
    pattern_result = self.pattern_matcher.match(normalized_input)
    if pattern_result.matched and confidence >= 0.90:
        return decision_from_pattern  # <10ms fast path

    # 3. Layer 2: Semantic Router (async)
    semantic_result = await self.semantic_router.route(normalized_input)
    if semantic_result.matched and similarity >= 0.85:
        return decision_from_semantic  # <100ms path

    # 4. Layer 3: LLM Classifier (async, if enabled)
    if config.enable_llm_fallback:
        llm_result = await self.llm_classifier.classify(normalized_input)
        return decision_from_llm  # <2000ms slow path

    # 5. No classification possible
    return UNKNOWN with HANDOFF workflow
```

### RouterConfig

| Setting | Default | Env Var |
|---------|---------|---------|
| `pattern_threshold` | 0.90 | `PATTERN_CONFIDENCE_THRESHOLD` |
| `semantic_threshold` | 0.85 | `SEMANTIC_SIMILARITY_THRESHOLD` |
| `enable_llm_fallback` | True | `ENABLE_LLM_FALLBACK` |
| `enable_completeness` | True | `ENABLE_COMPLETENESS` |
| `track_latency` | True | `TRACK_LATENCY` |

### Workflow Type Determination

After classification, the router maps intent+sub_intent to workflow type:

| Intent | Sub-Intent | Workflow |
|--------|-----------|----------|
| INCIDENT | system_unavailable, system_down | MAGENTIC (multi-agent) |
| INCIDENT | other | SEQUENTIAL |
| CHANGE | release_deployment, database_change | MAGENTIC |
| CHANGE | other | SEQUENTIAL |
| REQUEST | any | SIMPLE |
| QUERY | any | SIMPLE |
| UNKNOWN | any | HANDOFF (human) |

### Risk Level Determination

Keyword-based risk escalation using bilingual keywords:
- **CRITICAL**: `緊急`, `嚴重`, `critical`, `urgent`, `停機`, `當機` + INCIDENT
- **HIGH**: `影響`, `生產`, `無法`, `業務`, `客戶` + INCIDENT; or `生產`/`資料庫` + CHANGE
- **LOW**: QUERY category
- **MEDIUM**: default

### Metrics

`RoutingMetrics` tracks:
- `total_requests`, `pattern_matches`, `semantic_matches`, `llm_fallbacks`
- Latency: avg and p95 from rolling window of 1000 measurements
- Per-layer latency breakdown stored in `metadata.layer_latencies`

### Factory Functions

| Function | Description |
|----------|-------------|
| `create_router()` | Manual wiring with explicit components |
| `create_router_with_llm()` | Production factory: auto-creates LLM service from env vars via `LLMServiceFactory` |

---

## 7. CompletenessChecker (Sprint 93)

**Files**: `intent_router/completeness/checker.py`, `rules.py`

### How It Works

Rule-based field extraction using keyword matching and regex patterns:

1. **Rule Lookup**: Gets `CompletenessRule` for the detected `ITIntentCategory`
2. **Field Extraction**: For each required field, searches user input for keywords/patterns
3. **Score Calculation**: `completeness_score = extracted_count / total_required_count`
4. **Result**: Returns `CompletenessInfo(is_complete, missing_fields, optional_missing, completeness_score, suggestions)`

### Required Fields per Intent

| Category | Required Fields | Optional Fields |
|----------|----------------|-----------------|
| INCIDENT | `affected_system`, `error_description`, `urgency` | `impact_scope`, `error_time`, `recent_changes` |
| REQUEST | `request_type`, `target_system` | `justification`, `timeline`, `approver` |
| CHANGE | `change_type`, `target_system`, `change_description` | `rollback_plan`, `testing_status`, `impact_analysis` |
| QUERY | `query_topic` | `context`, `specific_question` |

### Field Extraction Method

Each `FieldDefinition` has:
- `keywords`: List of trigger words (e.g., for `affected_system`: `["系統", "服務", "server", "service", "application"]`)
- `patterns`: Optional regex patterns for structured extraction
- If any keyword is found in user input, the field is considered "present"

### Assessment

- **Real or Mock?**: Fully real, rule-based. No LLM calls.
- **Limitation**: Keyword presence != actual value extraction. Finding "系統" in the text marks `affected_system` as present, but doesn't extract which system.
- **Strict Mode**: Optional flag requiring ALL required fields (default: off).

---

## 8. InputGateway (Sprint 95)

**Files**: `input_gateway/gateway.py`, `models.py`, `schema_validator.py`, `source_handlers/`

### Architecture

```
IncomingRequest
    |
    v
InputGateway._identify_source()  -- SourceType detection
    |
    v
source_handlers[source_type].handle()  -- Source-specific normalization
    |
    v
BusinessIntentRouter.route()  -- Three-tier classification
    |
    v
RoutingDecision
```

### IncomingRequest Model

```python
@dataclass
class IncomingRequest:
    content: str           # Raw text content
    source_type: SourceType  # servicenow/prometheus/user/api
    data: Dict[str, Any]   # Structured payload
    request_id: str        # Unique ID (auto-generated UUID)
    timestamp: datetime
    metadata: Dict[str, Any]
```

### SourceType Enum

`SERVICENOW`, `PROMETHEUS`, `USER`, `API`, `UNKNOWN`

### Source Handlers

| Handler | Source | What It Does |
|---------|--------|-------------|
| `BaseSourceHandler` | Abstract | Defines `handle()` and `validate()` interface |
| `ServiceNowHandler` | ServiceNow webhooks | Extracts ticket fields (number, priority, category, description), maps ServiceNow priority to risk level, normalizes into RoutingRequest-compatible format |
| `PrometheusHandler` | Prometheus alerts | Extracts alert name, severity, labels, annotations, constructs incident description from alert metadata, maps severity to risk level |
| `UserInputHandler` | User chat text | Minimal processing — passes text directly to router, validates non-empty input |

### Source Detection

`InputGateway._identify_source()` examines the incoming request's `data` dict for source-specific markers:
- ServiceNow: looks for `sys_id`, `number`, `sys_class_name` fields
- Prometheus: looks for `alerts`, `receiver`, `status` fields
- User: default fallback for plain text

### SchemaValidator

JSON Schema validation for webhook payloads:
- `SchemaDefinition`: Wraps a JSON schema dict with name and version
- `SchemaValidator.validate()`: Validates incoming data against registered schemas
- Pre-registered schemas for ServiceNow and Prometheus payload formats

### Assessment

- **Real or Mock?**: Real input processing with structured field extraction.
- **Multi-source**: Genuinely supports 3 distinct input sources with source-specific normalization.
- **Integration Point**: The gateway calls `BusinessIntentRouter.route()` for classification after normalization.

---

## 9. Input Module (ServiceNow + Incident Processing)

**Files**: `input/servicenow_webhook.py`, `ritm_intent_mapper.py`, `incident_handler.py`, `contracts.py`, `ritm_mappings.yaml`, `incident_rules.yaml`

### ServiceNow Webhook Handler

Dedicated webhook processor for ServiceNow events:
- Parses ServiceNow webhook JSON payload
- Extracts ticket fields (number, state, priority, assignment_group, short_description, description)
- Emits structured events for downstream processing

### RITM Intent Mapper

Maps ServiceNow Request Items (RITMs) to intent categories:
- Uses `ritm_mappings.yaml` configuration
- Maps RITM catalog categories (e.g., "Hardware", "Software", "Access") to `ITIntentCategory` values
- Provides `map_ritm_to_intent(ritm_data) -> ITIntentCategory`

### ritm_mappings.yaml

Defines category-to-intent mappings:
```yaml
# Example structure:
mappings:
  hardware_request: request
  software_install: request
  access_request: request
  change_request: change
  incident_report: incident
```

### Incident Handler

Dedicated incident processing from ServiceNow:
- Applies `incident_rules.yaml` for severity/priority mapping
- Extracts structured incident fields
- Determines workflow type based on incident severity

### incident_rules.yaml

Extensive rule set for incident classification:
- Priority-to-risk mapping (P1 -> CRITICAL, P2 -> HIGH, etc.)
- Category-based sub-intent refinement
- Assignment group routing rules
- Escalation criteria

### Assessment

- **Real or Mock?**: Real webhook processing logic with structured field extraction.
- **Separation**: This `input/` module handles raw ServiceNow data; `input_gateway/` handles source detection and routing. Some functional overlap exists.

---

## 10. GuidedDialogEngine (Sprint 94)

**Files**: `guided_dialog/engine.py`, `context_manager.py`, `generator.py`, `refinement_rules.py`

### Dialog State Machine

```
INITIAL ---(start_dialog)---> GATHERING
GATHERING ---(process_response)---> GATHERING (loop until complete)
GATHERING ---(all fields present)---> COMPLETE
GATHERING ---(max turns exceeded)---> HANDOFF
any ---(user requests handoff)---> HANDOFF
```

Phases: `"initial"`, `"gathering"`, `"complete"`, `"handoff"`

### GuidedDialogEngine Flow

1. **`start_dialog(user_input)`**:
   - Calls `BusinessIntentRouter.route(user_input)` for initial classification
   - Checks completeness via router's built-in `CompletenessChecker`
   - If complete: returns `DialogResponse` with `is_complete=True`, phase="complete"
   - If incomplete: generates questions via `QuestionGenerator`, returns phase="gathering"

2. **`process_response(session_id, user_response)`**:
   - Retrieves `ConversationContextManager` for session
   - Calls `context_manager.incremental_update(user_response)` — **NO LLM re-classification**
   - Applies `RefinementRules` to refine `sub_intent` based on newly extracted fields
   - Re-checks completeness
   - If still incomplete: generates new questions for remaining missing fields
   - If complete: returns final result

Key design principle: **Incremental updates without LLM re-classification** — subsequent turns only use rule-based field extraction and refinement, avoiding expensive LLM calls.

### ConversationContextManager

Tracks multi-turn dialog state per session:

| Feature | Implementation |
|---------|---------------|
| State Storage | In-memory dict keyed by session_id |
| Dialog History | List of `DialogTurn(role, content, timestamp, extracted_fields)` |
| Field Accumulation | Merges extracted fields across turns |
| Context State | `ContextState` dataclass with `routing_decision`, `extracted_fields`, `turn_count`, `is_complete` |
| Incremental Update | `incremental_update()` — extracts fields from new response, merges with existing, re-evaluates completeness |

### QuestionGenerator

**Template-based** question generation (not LLM-based by default):

Each `QuestionTemplate` has:
- `field_name`: Target missing field
- `question`: Question text in Traditional Chinese
- `priority`: Higher = asked first
- `follow_up`: Optional follow-up questions
- `examples`: Example valid answers
- `category`: Intent category filter (None = universal)

Sample questions per category:

| Category | Field | Question (Chinese) |
|----------|-------|-------------------|
| INCIDENT | affected_system | "請問是哪個系統或服務受到影響？" |
| INCIDENT | error_description | "可以描述一下錯誤訊息或症狀嗎？" |
| INCIDENT | urgency | "這個問題的緊急程度如何？是否影響業務運作？" |
| REQUEST | request_type | "請問您需要申請什麼類型的服務？" |
| REQUEST | target_system | "這個申請是針對哪個系統或平台？" |
| CHANGE | change_type | "請問這是什麼類型的變更？" |
| CHANGE | change_description | "可以描述一下變更的具體內容嗎？" |

The generator also supports an **LLM-based mode** via `LLMClient` protocol (Sprint 97), but the default factory uses template-based generation.

### RefinementRules

Rule-based sub-intent refinement without LLM:

```
RefinementCondition:
  field_name: "affected_system"
  field_value: "database|DB|資料庫"
  match_any: True

RefinementRule:
  category: INCIDENT
  from_sub_intent: "etl_failure"
  to_sub_intent: "database_error"
  conditions: [above condition]
  priority: 100
```

When a user provides more information in subsequent turns, refinement rules can upgrade the sub-intent (e.g., ETL failure affecting the database becomes a database_error).

### Assessment

- **Real or Mock?**: Fully real, template-based dialog system. No mock data.
- **LLM Usage**: Only initial classification uses LLM (via router). Follow-up turns are pure rule-based.
- **Session Management**: In-memory only — no persistence across server restarts.
- **Question Quality**: Professional Traditional Chinese questions with contextual follow-ups.

---

## 11. Data Flow Summary

### End-to-End Flow

```
User/Webhook/Alert
    |
    v
[InputGateway]
    |--- _identify_source() -> SourceType
    |--- source_handlers[type].handle() -> normalized content
    |
    v
[BusinessIntentRouter.route(text)]
    |
    |--- [Tier 1: PatternMatcher.match()] <10ms
    |       Regex scan against 30+ YAML rules
    |       If confidence >= 0.90 -> DONE
    |
    |--- [Tier 2: SemanticRouter.route()] <100ms
    |       Vector similarity via embeddings
    |       If similarity >= 0.85 -> DONE
    |
    |--- [Tier 3: LLMClassifier.classify()] <2000ms
    |       Real LLM call via LLMServiceProtocol
    |       Returns classification + completeness
    |
    v
[RoutingDecision]
    |--- intent_category: INCIDENT/REQUEST/CHANGE/QUERY/UNKNOWN
    |--- sub_intent: specific type
    |--- confidence: 0.0-1.0
    |--- routing_layer: "pattern"/"semantic"/"llm"
    |--- workflow_type: MAGENTIC/SEQUENTIAL/SIMPLE/HANDOFF
    |--- risk_level: CRITICAL/HIGH/MEDIUM/LOW
    |
    v
[CompletenessChecker.check()]
    |--- Keyword-based field extraction
    |--- Returns CompletenessInfo
    |
    v
(if incomplete)
[GuidedDialogEngine]
    |--- Template-based question generation
    |--- Multi-turn incremental updates (no LLM re-call)
    |--- RefinementRules for sub-intent updates
    |
(if complete)
    v
[RiskAssessor] -> [HITLController] (if HIGH/CRITICAL)
```

### Real vs Rule-Based vs Hardcoded

| Component | Type | Details |
|-----------|------|---------|
| PatternMatcher | **Rule-based** | Pre-compiled regex from YAML, fixed 0.95 confidence |
| SemanticRouter (original) | **Real LLM** (embeddings) | Aurelio library + OpenAI/Azure encoder, real cosine similarity |
| SemanticRouter (Azure) | **Real LLM** (embeddings) | Azure OpenAI embeddings + Azure AI Search vector index |
| LLMClassifier | **Real LLM** (generation) | LLMServiceProtocol -> Azure OpenAI/Claude/Mock |
| CompletenessChecker | **Rule-based** | Keyword presence matching |
| QuestionGenerator | **Template-based** | Pre-written Chinese question templates (LLM mode available) |
| RefinementRules | **Rule-based** | Condition-action rules for sub-intent upgrade |
| Workflow/Risk mapping | **Hardcoded** | Intent+keyword -> workflow/risk in Python code |
| InputGateway | **Rule-based** | Source detection by field presence, handler dispatch |

---

## 12. Cross-Reference with Sprint Plan Features

| Feature | Plan ID | Status | Notes |
|---------|---------|--------|-------|
| Three-tier Routing | F3 | **Implemented** | Full cascade: Pattern->Semantic->LLM with configurable thresholds |
| Guided Dialog | F4 | **Implemented** | Multi-turn with incremental updates, template questions, refinement rules |
| Business Router | F5 | **Implemented** | BusinessIntentRouter coordinates all three tiers + completeness |
| LLM Classifier | F6 | **Implemented** | Real LLM via LLMServiceProtocol with cache, evaluation, graceful degradation |

---

## 13. Findings and Observations

### Strengths

1. **Well-Architected Cascade**: The three-tier fallback is cleanly implemented with measurable latency targets.
2. **Real Infrastructure**: Not a toy — uses real embeddings, real LLM calls, real vector search.
3. **Bilingual Support**: Comprehensive Chinese + English pattern coverage for Taiwan/HK market.
4. **Graceful Degradation**: Each tier fails gracefully (no crash, returns UNKNOWN/no-match).
5. **Clean Contracts**: Sprint 116 L4a/L4b protocol split with proper ABCs.
6. **Incremental Dialog**: Smart design avoiding LLM re-calls on subsequent dialog turns.
7. **Extensibility**: YAML-driven patterns, configurable thresholds, pluggable LLM backends.

### Concerns

1. **Fixed Pattern Confidence**: PatternMatcher always returns 0.95. No match quality scoring based on pattern specificity or input length. A short generic match gets the same confidence as a precise long match.

2. **In-Memory State**: `ConversationContextManager` and `ClassificationCache` use in-memory dicts. No persistence across restarts. No distributed session support for multi-server deployments.

3. **Dual Semantic Router**: Two implementations (Aurelio-based vs Azure-based) with no clear switching mechanism in production wiring. `BusinessIntentRouter` is wired to original only.

4. **Keyword-Based Completeness**: Field "extraction" is keyword presence detection, not value extraction. Saying "系統很慢" marks `affected_system` as present, but the actual system name is not captured.

5. **Thread Safety**: `ClassificationCache` uses a plain dict without locks. Under concurrent async requests this could have race conditions (though Python's GIL mitigates most risks for dict operations).

6. **No Circuit Breaker**: If the LLM service is slow or failing, there's no circuit breaker pattern. Each request will wait up to the timeout before failing.

7. **Session ID Management**: `GuidedDialogEngine` requires external session ID management. No built-in session expiry or cleanup.

---

## Appendix: File Inventory

| File | LOC (approx) | Sprint | Purpose |
|------|-------------|--------|---------|
| `contracts.py` | 360 | S116 | L4a/L4b interface contracts |
| `__init__.py` | 206 | S91+ | 57 exports |
| `metrics.py` | 893 | S99 | OpenTelemetry metrics collector |
| `intent_router/router.py` | 623 | S93 | BusinessIntentRouter coordinator |
| `intent_router/models.py` | 450 | S91-92 | Core data models (7 dataclasses, 3 enums) |
| `intent_router/contracts.py` | 135 | S116 | L4b layer contracts |
| `intent_router/pattern_matcher/matcher.py` | ~350 | S91 | PatternMatcher with YAML loading |
| `intent_router/pattern_matcher/rules.yaml` | ~400 | S91 | 30+ regex rules (bilingual) |
| `intent_router/semantic_router/router.py` | ~370 | S92 | SemanticRouter (Aurelio-based) |
| `intent_router/semantic_router/routes.py` | ~300 | S92 | 15 route definitions |
| `intent_router/semantic_router/embedding_service.py` | ~260 | S115 | Azure OpenAI embedding with LRU cache |
| `intent_router/semantic_router/azure_semantic_router.py` | ~280 | S115 | Azure AI Search router |
| `intent_router/semantic_router/azure_search_client.py` | ~340 | S115 | Azure AI Search client wrapper |
| `intent_router/semantic_router/setup_index.py` | ~370 | S115 | Index creation script |
| `intent_router/semantic_router/route_manager.py` | ~550 | S115 | Route CRUD operations |
| `intent_router/semantic_router/migration.py` | ~310 | S115 | Route data migration script |
| `intent_router/llm_classifier/classifier.py` | ~280 | S92/S128 | LLMClassifier with LLMServiceProtocol |
| `intent_router/llm_classifier/prompts.py` | ~200 | S92 | Classification prompt templates |
| `intent_router/llm_classifier/cache.py` | ~250 | S128 | In-memory classification cache |
| `intent_router/llm_classifier/evaluation.py` | ~500 | S128 | Classifier evaluation suite |
| `intent_router/completeness/checker.py` | ~320 | S93 | Field completeness checker |
| `intent_router/completeness/rules.py` | ~660 | S93 | Field requirements per intent |
| `guided_dialog/engine.py` | 593 | S94 | GuidedDialogEngine |
| `guided_dialog/context_manager.py` | 1163 | S94 | ConversationContextManager |
| `guided_dialog/generator.py` | 1151 | S94/S97 | QuestionGenerator (template + LLM) |
| `guided_dialog/refinement_rules.py` | 622 | S94 | Sub-intent refinement rules |
| `input_gateway/gateway.py` | ~370 | S95 | InputGateway entry point |
| `input_gateway/models.py` | ~250 | S95 | IncomingRequest, SourceType |
| `input_gateway/schema_validator.py` | ~370 | S95 | JSON schema validation |
| `input_gateway/source_handlers/base_handler.py` | ~270 | S95 | BaseSourceHandler ABC |
| `input_gateway/source_handlers/servicenow_handler.py` | ~370 | S95 | ServiceNow webhook handler |
| `input_gateway/source_handlers/prometheus_handler.py` | ~390 | S95 | Prometheus alert handler |
| `input_gateway/source_handlers/user_input_handler.py` | ~240 | S95 | User text handler |
| `input/servicenow_webhook.py` | ~330 | S95 | ServiceNow webhook processor |
| `input/ritm_intent_mapper.py` | ~230 | S95 | RITM to intent mapping |
| `input/incident_handler.py` | ~430 | S95 | Incident processing |
| `input/contracts.py` | ~110 | S95 | Input module contracts |
| `input/ritm_mappings.yaml` | ~50 | S95 | RITM category mappings |
| `input/incident_rules.yaml` | ~350 | S95 | Incident classification rules |
