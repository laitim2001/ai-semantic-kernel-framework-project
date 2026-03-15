# Phase 3c: Integration — Orchestration Part 2

> Agent C6 Analysis | Scope: hitl/, metrics.py, risk_assessor/, input_gateway/source_handlers/, audit/, input/, contracts.py

---

## 1. HITL Controller (hitl/)

### 1.1 Architecture Overview

The HITL subsystem provides a complete human-in-the-loop approval workflow for high-risk IT operations, implemented across three files (~2,213 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `controller.py` | ~833 | Core controller, enums, protocols, InMemoryStorage, factory |
| `approval_handler.py` | ~693 | RedisApprovalStorage, high-level ApprovalHandler |
| `notification.py` | ~732 | Teams webhook notifications, card builder |

### 1.2 Approval Flow

```
RiskAssessor.assess() → requires_approval=True
    ↓
HITLController.request_approval()
    ├── Creates ApprovalRequest (UUID, expiry, type)
    ├── Saves to ApprovalStorage (Redis or InMemory)
    ├── Sends TeamsNotificationService.send_approval_request()
    │     └── POSTs MessageCard with Approve/Reject buttons to webhook URL
    └── Returns ApprovalRequest (status=PENDING)
    ↓
User clicks Approve/Reject in Teams
    ↓
API calls HITLController.process_approval()
    ├── Validates request is still PENDING
    ├── Checks expiration
    ├── Updates status → APPROVED or REJECTED
    ├── Fires on_approved/on_rejected callbacks
    ├── Sends result notification via Teams
    └── Returns updated ApprovalRequest
```

**Status Lifecycle**: PENDING → APPROVED | REJECTED | EXPIRED | CANCELLED

**Approval Types**:
- `NONE`: No approval required (LOW/MEDIUM risk)
- `SINGLE`: One approver required (HIGH risk)
- `MULTI`: Multiple approvers required (CRITICAL risk)

**Timeout**: Default 30 minutes. Auto-expires on status check.

### 1.3 Storage Backends

#### InMemoryApprovalStorage (controller.py)
- Simple `Dict[str, ApprovalRequest]` storage
- Suitable for testing/development only
- No persistence across restarts
- Implements `ApprovalStorage` protocol (save, get, update, delete, list_pending)

#### RedisApprovalStorage (approval_handler.py)
- Full persistent storage using Redis async client
- **Key schema**:
  - `approval:{request_id}` → JSON serialized ApprovalRequest
  - `approval_history:{request_id}` → JSON serialized event history
  - `approval_pending` → Redis SET of pending request IDs
- **TTL management**:
  - Pending requests: 30 minutes (configurable)
  - Completed requests: 7 days (for audit trail)
- Handles deserialization of nested objects (RoutingDecision, RiskAssessment)
- Cleans stale IDs from pending set during list_pending()

#### Factory Selection Logic (`_create_default_storage`):
- `testing` env → InMemory directly
- `development` env → Redis preferred, InMemory fallback with WARNING
- `production` env → Redis required, raises `RuntimeError` if unavailable
- Sprint 119: Tries centralized Redis client first (`src.infrastructure.redis_client`)

### 1.4 ApprovalHandler (High-Level Wrapper)

Wraps ApprovalStorage with additional features:
- Input validation (empty request_id/approver checks)
- Approver authorization checks (if approvers list is set)
- Expiration auto-handling
- Audit logging via callback (`_default_audit_logger` logs JSON to standard logger)
- Returns `ApprovalResult` dataclass with success/error semantics
- `list_pending_by_approver()` filters pending requests by authorized user

### 1.5 Notification Service

#### TeamsNotificationService
- Sends Microsoft Teams MessageCard (Outlook Actionable Message format) via Incoming Webhook
- Uses `httpx.AsyncClient` for HTTP POST
- Cards include:
  - Risk-level-colored theme (Green/Orange/Red/DarkRed)
  - Request details (intent category, sub-intent, risk score, expiry)
  - Risk assessment reasoning
  - Approve/Reject action buttons (HttpPOST type with callback URLs)
  - "View Details" button (if `detail_url` in metadata)
- Traditional Chinese UI labels (e.g., "審批請求", "批准", "拒絕")
- Separate result notification card (approved/rejected outcome)

#### TeamsCardBuilder
- Fluent builder API for constructing MessageCards
- `RISK_COLORS` maps RiskLevel enum to hex colors
- Methods: `with_title()`, `add_section()`, `add_fact()`, `add_approve_button()`, `add_reject_button()`, `add_open_url_button()`, `build()`

#### EmailNotificationService
- **Placeholder only** — logs warning "not implemented"
- Stores SMTP config but both methods return `False`

#### CompositeNotificationService
- Fans out to multiple services using `asyncio.gather()`
- Returns `True` if at least one service succeeds

### 1.6 Protocol Verification

| Protocol | Defined In | Concrete Implementations |
|----------|-----------|-------------------------|
| `ApprovalStorage` | controller.py | `InMemoryApprovalStorage`, `RedisApprovalStorage` |
| `NotificationService` | controller.py | `TeamsNotificationService`, `EmailNotificationService` (stub), `CompositeNotificationService` |

**All protocols have concrete implementations.**

---

## 2. Metrics (metrics.py)

### 2.1 Overview

`OrchestrationMetricsCollector` (~893 LOC) provides comprehensive observability with **dual-mode support**:

- **OpenTelemetry mode**: When `opentelemetry` package is installed, creates real OTel instruments (Counter, Histogram, UpDownCounter) via `otel_metrics.get_meter("orchestration")`
- **Fallback mode**: In-memory metric implementations (FallbackCounter, FallbackHistogram, FallbackGauge) with full percentile calculation

### 2.2 Metric Categories

#### Routing Metrics (4 metrics)
| Metric Name | Type | Labels |
|-------------|------|--------|
| `orchestration_routing_requests_total` | Counter | intent_category, layer_used |
| `orchestration_routing_latency_seconds` | Histogram | layer_used |
| `orchestration_routing_confidence` | Histogram | intent_category |
| `orchestration_completeness_score` | Histogram | intent_category |

#### Dialog Metrics (4 metrics)
| Metric Name | Type | Labels |
|-------------|------|--------|
| `orchestration_dialog_rounds_total` | Counter | dialog_id, phase |
| `orchestration_dialog_completion_rate` | Gauge | — |
| `orchestration_dialog_duration_seconds` | Histogram | outcome |
| `orchestration_dialog_active_count` | Gauge | — |

#### HITL Metrics (4 metrics)
| Metric Name | Type | Labels |
|-------------|------|--------|
| `orchestration_hitl_requests_total` | Counter | risk_level, status |
| `orchestration_hitl_approval_time_seconds` | Histogram | risk_level |
| `orchestration_hitl_pending_count` | Gauge | — |
| `orchestration_hitl_approval_rate` | Gauge | risk_level |

#### System Source Metrics (3 metrics)
| Metric Name | Type | Labels |
|-------------|------|--------|
| `orchestration_system_source_requests_total` | Counter | source_type |
| `orchestration_system_source_latency_seconds` | Histogram | source_type |
| `orchestration_system_source_errors_total` | Counter | source_type, error_type |

### 2.3 Histogram Bucket Configuration

Smart bucket selection based on metric name:
- **HITL approval time**: [60, 300, 600, 1800, 3600] seconds (1min-1hr)
- **Routing latency**: [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0] seconds
- **Score/confidence**: [0.1, 0.2, ..., 1.0] (0.1 increments)

### 2.4 Additional Features

- **`routing_timer()` context manager**: Automatically records latency for routing operations
- **`track_routing_metrics` decorator**: Wraps async routing functions to auto-extract and record metrics from results
- **Global singleton**: `get_metrics_collector()` / `reset_metrics_collector()`
- **Export**: `get_metrics()` returns structured dict with counters, histograms (with p50/p95/p99), and gauges

### 2.5 OTel Gauge Issue

When OTel is available, gauge methods (`set_active_dialogs`, `set_dialog_completion_rate`, `set_hitl_pending_count`, `set_hitl_approval_rate`) have `pass` in the OTel branch — they use `UpDownCounter` as a substitute for `ObservableGauge`, but the actual value-setting logic is missing for OTel mode. **This is a known gap**: gauges work correctly only in fallback mode.

---

## 3. Risk Assessor (risk_assessor/)

### 3.1 Architecture

Two files (~1,350 LOC total):

| File | LOC | Purpose |
|------|-----|---------|
| `assessor.py` | ~639 | RiskAssessor engine, RiskFactor, AssessmentContext, RiskAssessment |
| `policies.py` | ~711 | RiskPolicies collection, 26 default policies, factory functions |

### 3.2 How Orchestration-Level Risk Differs from Hybrid-Level Risk

The **orchestration risk assessor** operates at the **IT intent routing level**, evaluating risk based on:

1. **IT Intent Category**: INCIDENT (0.8) > CHANGE (0.6) > UNKNOWN (0.5) > REQUEST (0.4) > QUERY (0.2)
2. **Sub-intent specificity**: e.g., `system_down` (0.5), `etl_failure` (0.4), `security_incident` (0.5), `access_request` (0.3)
3. **Contextual factors**: Production environment (+1 level), weekend (+1 level), urgent flag (+1 level), >3 affected systems (+1 level)
4. **Low routing confidence**: Penalty weight if confidence < 0.8
5. **Policy-based**: 26 pre-defined ITIL-aligned policies mapping intent+sub_intent to risk levels

**Contrast with hybrid-level risk** (in `integrations/hybrid/`):
- Hybrid risk assesses whether to use MAF vs Claude SDK at the framework switching level
- Orchestration risk assesses whether a **business operation** requires human approval at the workflow routing level
- Orchestration risk directly determines HITL approval requirements: HIGH → single approval, CRITICAL → multi approval

### 3.3 Assessment Pipeline

```
RiskAssessor.assess(routing_decision, context?)
    1. Get base policy → RiskPolicies.get_policy(category, sub_intent)
       Lookup order: exact match → category default (*) → global default
    2. Collect risk factors (7 dimensions)
    3. Apply context adjustments (production/weekend/urgent/multi-system)
       Each can elevate risk by one level (LOW→MEDIUM→HIGH→CRITICAL)
    4. Calculate numerical score (base_level_score + factor_adjustments, clamped 0-1)
    5. Determine approval requirements:
       - HIGH → requires_approval=True, approval_type="single"
       - CRITICAL → requires_approval=True, approval_type="multi"
       - LOW/MEDIUM → requires_approval=False, approval_type="none"
    6. Generate human-readable reasoning
    → Returns RiskAssessment
```

### 3.4 Default Policies (26 policies)

| Category | Count | Risk Levels |
|----------|-------|-------------|
| INCIDENT | 10 | CRITICAL (system_down, system_unavailable, security_incident), HIGH (etl_failure, database_issue, network_failure, hardware_failure), MEDIUM (performance_issue, software_issue, default) |
| REQUEST | 5 | HIGH (access_request), MEDIUM (account, software, hardware), LOW (default) |
| CHANGE | 7 | CRITICAL (emergency_change), HIGH (normal_change, release_deployment, database_change), MEDIUM (standard_change, configuration_update, default) |
| QUERY | 3 | LOW (all) |
| UNKNOWN | 1 | MEDIUM (default) |

### 3.5 Policy Variants

- `create_default_policies()` → Standard ITIL-aligned policies
- `create_strict_policies()` → All incidents/changes require single approval minimum
- `create_relaxed_policies()` → Changes auto-approved (for dev environments)
- `RiskPolicies.from_yaml()` → Load custom policies from YAML file

---

## 4. Input Gateway & Source Handlers (input_gateway/)

### 4.1 Architecture

```
InputGateway
├── _identify_source() — Header/field based source detection
├── source_handlers/
│   ├── ServiceNowHandler — Mapping table + PatternMatcher fallback
│   ├── PrometheusHandler — Alert name regex patterns
│   └── UserInputHandler — Delegates to full BusinessIntentRouter
├── SchemaValidator — JSON schema validation for webhooks
└── GatewayMetrics — Request counts, latency tracking
```

### 4.2 Source Identification Priority

1. Check `x-servicenow-webhook` header → ServiceNow
2. Check `x-prometheus-alertmanager` header → Prometheus
3. Check `x-webhook-source` header → Custom source
4. Use `source_type` field if set
5. Default to `"user"` (configurable)

### 4.3 Supported Input Sources

#### ServiceNowHandler
- **Mapping table**: 20+ entries mapping `category/subcategory` → `(ITIntentCategory, sub_intent)`
  - Incident: hardware, software, network, database, security, performance, application, infrastructure
  - Request: account, access, software, hardware, service, information
  - Change: standard, emergency, normal, deployment, configuration
- **Priority mapping**: ServiceNow priority 1-5 → critical/high/medium/low/low
- **Workflow mapping**: Per sub-intent (magentic for critical, sequential for standard, simple for queries)
- **Fallback**: PatternMatcher on `short_description` if no mapping match
- **Target latency**: < 10ms

#### PrometheusHandler
- **41 compiled regex patterns** matching alert names to incident sub-categories:
  - CPU/Performance, Memory, Disk/Storage, Service down, Latency, Error rate, Certificate, Network, Database, Queue/Messaging, Container/K8s
- **Severity mapping**: critical/warning/info/none → risk levels
- **Override**: Critical severity forces `magentic` workflow
- **Target latency**: < 10ms

#### UserInputHandler
- **Input normalization**: Whitespace collapsing, 10K char limit, fallback field extraction (content → data.description → data.message → data.text → data.query → data.input)
- **Full routing**: Delegates to `BusinessIntentRouter.route()` (Pattern → Semantic → LLM)
- **Metadata enhancement**: Adds handler_type, input_length, normalization flag

### 4.4 SchemaValidator

Pre-defined schemas for:
- **ServiceNow**: Required fields: number, category, short_description. Type checking on priority.
- **Prometheus**: Required fields: alerts. Nested validation on alert objects (alertname, status).
- **User input**: No required fields (very flexible).
- Supports strict mode (raise) vs warning mode (log).
- Custom schema registration via `register_schema()`.

### 4.5 GatewayMetrics

Tracks per-source request counts, validation errors, and latency (avg, p95). Keeps last 1000 measurements.

---

## 5. Input Processing Module (input/)

### 5.1 Overview

A **later-phase** (Sprint 114, 116, 126) evolution of input processing, separate from the Sprint 95 `input_gateway/`:

| File | Sprint | Purpose |
|------|--------|---------|
| `servicenow_webhook.py` | 114 | RITM webhook receiver with auth (shared secret, HMAC, IP whitelist) |
| `ritm_intent_mapper.py` | 114 | YAML-based RITM → IPA intent mapping |
| `contracts.py` | 116 | L4a input processing protocols (InputProcessorProtocol, InputValidatorProtocol) |
| `incident_handler.py` | 126 | INC webhook processor implementing InputProcessorProtocol |

### 5.2 ServiceNowWebhookReceiver

- **Authentication**: Shared secret (`X-ServiceNow-Secret` header) or HMAC-SHA256 body signature
- **IP whitelisting**: Supports individual IPs and CIDR ranges
- **Idempotency**: In-memory set of processed `sys_id` values (max 10,000, LRU eviction)
- **RITM parsing**: Pydantic model validation for ServiceNow RITM payloads

### 5.3 RITMIntentMapper

- Loads mappings from YAML file (`ritm_mappings.yaml`)
- Case-insensitive lookup on `cat_item_name`
- Variable extraction with dotted-path syntax (`variables.affected_user`)
- Fallback strategy: configurable (default: `semantic_router`)

### 5.4 IncidentHandler (Sprint 126)

- Implements `InputProcessorProtocol` from L4a contracts
- Parses ServiceNow INC webhooks into `RoutingRequest`
- Two-stage subcategory classification:
  1. Direct mapping from ServiceNow category field (9 categories)
  2. Regex fallback with 8 pattern groups (supports Traditional Chinese keywords)
- Maps ServiceNow priority to risk level

---

## 6. Orchestration Contracts (contracts.py)

### 6.1 L4a/L4b Interface Definitions (Sprint 116)

Defines clean separation between Input Processing (L4a) and Decision Engine (L4b):

| Contract | Type | Purpose |
|----------|------|---------|
| `InputSource` | Enum | 7 source types (WEBHOOK_SERVICENOW, WEBHOOK_PROMETHEUS, HTTP_API, SSE_STREAM, USER_CHAT, RITM, UNKNOWN) |
| `RoutingRequest` | Dataclass | L4a output: normalized query, intent_hint, context, source, priority |
| `RoutingResult` | Dataclass | L4b output: intent, sub_intent, confidence, matched_layer, workflow_type, risk_level, completeness |
| `InputGatewayProtocol` | ABC | L4a interface: `receive()`, `validate()` |
| `RouterProtocol` | ABC | L4b interface: `route()`, `get_available_layers()` |

### 6.2 Adapter Functions

Bridge functions between Sprint 93 models and Sprint 116 contracts:
- `incoming_request_to_routing_request()`: Converts `IncomingRequest` → `RoutingRequest`
- `routing_decision_to_routing_result()`: Converts `RoutingDecision` → `RoutingResult`

### 6.3 Protocol Implementation Verification

| Protocol | Defined In | Implementations |
|----------|-----------|-----------------|
| `InputGatewayProtocol` | contracts.py | **No concrete implementation found** — InputGateway (gateway.py) predates this protocol and does NOT extend it |
| `RouterProtocol` | contracts.py | **No concrete implementation found** — BusinessIntentRouter predates this protocol and does NOT extend it |
| `InputProcessorProtocol` | input/contracts.py | `IncidentHandler` (input/incident_handler.py) |
| `InputValidatorProtocol` | input/contracts.py | **No concrete implementation found** |

**Gap**: `InputGatewayProtocol` and `RouterProtocol` from Sprint 116 define clean interfaces, but the existing Sprint 95 implementations (InputGateway, BusinessIntentRouter) do not implement them. They are structurally compatible but not formally linked.

---

## 7. Audit Logger (audit/)

### 7.1 Overview (~281 LOC)

Structured JSON audit logging for routing decisions with:
- **Correlation IDs**: UUID-based request tracing
- **Privacy**: User input truncated to 500 chars
- **JSON format**: Structured for log aggregation (ELK, Splunk)
- **Event types**: `routing_decision`, `pattern_match`, `layer_escalation`, `error`
- Returns `AuditEntry` dataclass with `to_json()` for serialization

---

## 8. Cross-Reference: Features B6-B7

### B6: HITL Controller

| Feature | Status | Notes |
|---------|--------|-------|
| Approval request creation | Implemented | UUID-based, with expiry |
| Status tracking | Implemented | Auto-expire on check |
| Approval/rejection processing | Implemented | With authorization checks |
| Cancellation | Implemented | By requester |
| Callback system | Implemented | on_approved/on_rejected/on_expired |
| Storage backends | Implemented | InMemory + Redis |
| Timeout handling | Implemented | Default 30 min, configurable |

### B7: Approval Routes (API layer)

The HITL controller provides the business logic. API routes would be in `api/v1/orchestration/` (outside this agent's scope but referenced by the controller's callback URLs).

---

## 9. Issues & Observations

### 9.1 Known Gaps

1. **OTel Gauge incomplete**: `set_active_dialogs()`, `set_dialog_completion_rate()`, `set_hitl_pending_count()`, `set_hitl_approval_rate()` have `pass` in OTel mode — gauges only work in fallback mode.

2. **EmailNotificationService is a stub**: Logs warning and returns `False`. Not production-ready.

3. **Sprint 116 Protocols unimplemented**: `InputGatewayProtocol`, `RouterProtocol`, and `InputValidatorProtocol` have no concrete classes that formally implement them. The existing classes are structurally compatible but don't extend the ABCs.

4. **Dual input processing systems**: `input_gateway/` (Sprint 95) and `input/` (Sprint 114/116/126) coexist with overlapping ServiceNow handling. `input_gateway/ServiceNowHandler` uses mapping tables while `input/IncidentHandler` uses regex classification. No clear migration path documented.

5. **HITL multi-approval not enforced**: `ApprovalType.MULTI` is set but the controller processes approval from a single approver. Quorum logic (require N of M approvers) is not implemented.

### 9.2 Strengths

1. **Well-structured protocol-first design**: All major components have Protocol/ABC definitions with clear method contracts.
2. **Environment-aware storage selection**: Production requires Redis, development falls back gracefully.
3. **Comprehensive risk policy system**: 26 ITIL-aligned policies with 3 configurable variants (default/strict/relaxed) plus YAML loading.
4. **Dual-mode metrics**: Seamless OTel integration when available, functional fallback otherwise.
5. **Traditional Chinese UI**: Teams notification cards properly localized for target market.
6. **Source handler extensibility**: `register_handler()` / `unregister_handler()` for dynamic source registration.

---

## 10. File Inventory

| File | Lines | Sprint |
|------|-------|--------|
| `hitl/__init__.py` | 91 | 97 |
| `hitl/controller.py` | 833 | 97 |
| `hitl/approval_handler.py` | 693 | 97 |
| `hitl/notification.py` | 732 | 97 |
| `metrics.py` | 893 | 99 |
| `risk_assessor/__init__.py` | 31 | 96 |
| `risk_assessor/assessor.py` | 639 | 96 |
| `risk_assessor/policies.py` | 711 | 96 |
| `input_gateway/__init__.py` | 95 | 95 |
| `input_gateway/models.py` | 278 | 95 |
| `input_gateway/gateway.py` | 370 | 95 |
| `input_gateway/schema_validator.py` | 415 | 95 |
| `input_gateway/source_handlers/__init__.py` | 38 | 95 |
| `input_gateway/source_handlers/base_handler.py` | 296 | 95 |
| `input_gateway/source_handlers/servicenow_handler.py` | 347 | 95 |
| `input_gateway/source_handlers/prometheus_handler.py` | 365 | 95 |
| `input_gateway/source_handlers/user_input_handler.py` | 255 | 95 |
| `audit/__init__.py` | 13 | 91 |
| `audit/logger.py` | 270 | 91 |
| `input/__init__.py` | 55 | 114/116/126 |
| `input/servicenow_webhook.py` | 376 | 114 |
| `input/ritm_intent_mapper.py` | 258 | 114 |
| `input/contracts.py` | 138 | 116 |
| `input/incident_handler.py` | 452 | 126 |
| `contracts.py` | 359 | 116 |
| `__init__.py` | 206 | 91-99/116 |
| **Total** | **~8,608** | |
