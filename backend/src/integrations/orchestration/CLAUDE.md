# Orchestration — Three-tier Intent Routing

> Phase 28, Sprints 91-99 | 21 Python files, ~16,000 LOC | Intelligent IT intent routing system

---

## Directory Structure

```
orchestration/
├── __init__.py                     # 57 exports organized by component
├── metrics.py                      # OrchestrationMetricsCollector (893 LOC, OpenTelemetry)
│
├── intent_router/                  # Three-layer routing (3,815 LOC)
│   ├── router.py                   # BusinessIntentRouter (639 LOC) — Coordinator
│   ├── models.py                   # ITIntentCategory, RoutingDecision, RiskLevel, WorkflowType
│   ├── pattern_matcher/
│   │   └── matcher.py              # PatternMatcher — Regex rules from YAML (<10ms)
│   ├── semantic_router/
│   │   ├── router.py               # SemanticRouter — Vector similarity (<100ms)
│   │   └── routes.py               # Route definitions
│   ├── llm_classifier/
│   │   ├── classifier.py           # LLMClassifier — Claude Haiku fallback (<2s)
│   │   └── prompts.py              # Prompt templates
│   └── completeness/
│       ├── checker.py              # CompletenessChecker — Field validation
│       └── rules.py                # Field requirement rules per intent
│
├── guided_dialog/                  # Multi-turn dialog (3,530 LOC)
│   ├── engine.py                   # GuidedDialogEngine (593 LOC)
│   ├── context_manager.py          # ConversationContextManager (1,163 LOC)
│   ├── generator.py                # QuestionGenerator (1,151 LOC)
│   └── refinement_rules.py         # Sub-intent refinement (622 LOC)
│
├── input_gateway/                  # Source-aware routing (2,302 LOC)
│   ├── gateway.py                  # InputGateway — Main entry point
│   ├── models.py                   # IncomingRequest, SourceType
│   ├── schema_validator.py         # JSON schema validation
│   └── source_handlers/
│       ├── base_handler.py         # BaseSourceHandler (abstract)
│       ├── servicenow_handler.py   # ServiceNow ticket mapping
│       ├── prometheus_handler.py   # Prometheus alert mapping
│       └── user_input_handler.py   # User text → full routing
│
├── hitl/                           # Human-in-the-loop (2,213 LOC)
│   ├── controller.py               # HITLController (788 LOC) — Approval workflow
│   ├── approval_handler.py         # ApprovalHandler (693 LOC) — Operations + persistence
│   └── notification.py             # TeamsNotificationService (732 LOC) — Adaptive cards
│
├── risk_assessor/                  # Risk evaluation (1,350 LOC)
│   ├── assessor.py                 # RiskAssessor (639 LOC)
│   └── policies.py                 # RiskPolicies — Configurable per intent
│
└── audit/                          # Audit logging (281 LOC)
    └── logger.py                   # AuditLogger — Structured JSON logging
```

---

## Three-tier Routing Architecture

```
INPUT: User text / ServiceNow / Prometheus alert
    ↓
InputGateway → SourceType detection
    ↓
┌──────────────────────────────────────────────────┐
│ Layer 1: PatternMatcher (< 10ms)                 │
│   Regex rules from YAML, confidence ≥ 0.90       │
├──────────────────────────────────────────────────┤
│ Layer 2: SemanticRouter (< 100ms)                │
│   Vector similarity, threshold ≥ 0.85            │
├──────────────────────────────────────────────────┤
│ Layer 3: LLMClassifier (< 2000ms)               │
│   Claude Haiku, fallback for ambiguous cases     │
└──────────────────────────────────────────────────┘
    ↓
RoutingDecision
    ├── intent_category: INCIDENT | REQUEST | CHANGE | QUERY | UNKNOWN
    ├── sub_intent: specific category
    ├── risk_level: CRITICAL | HIGH | MEDIUM | LOW
    ├── workflow_type: MAGENTIC | HANDOFF | CONCURRENT | SEQUENTIAL | SIMPLE
    ├── confidence_score
    └── routing_layer (which tier matched)
    ↓
CompletenessChecker → Missing fields?
    ↓ (if incomplete)
GuidedDialogEngine → Multi-turn question generation
    ↓ (if complete)
RiskAssessor → Risk evaluation
    ↓ (if HIGH/CRITICAL)
HITLController → Approval workflow → Teams notification
```

---

## Key Classes

| Class | File | LOC | Purpose |
|-------|------|-----|---------|
| **BusinessIntentRouter** | intent_router/router.py | 639 | Three-layer routing coordinator |
| **GuidedDialogEngine** | guided_dialog/engine.py | 593 | Multi-turn dialog orchestration |
| **ConversationContextManager** | guided_dialog/context_manager.py | 1,163 | Dialog state tracking |
| **QuestionGenerator** | guided_dialog/generator.py | 1,151 | Template-based question generation |
| **OrchestrationMetricsCollector** | metrics.py | 893 | OpenTelemetry metrics |
| **HITLController** | hitl/controller.py | 788 | Approval workflow manager |
| **TeamsNotificationService** | hitl/notification.py | 732 | Teams adaptive cards |
| **RiskAssessor** | risk_assessor/assessor.py | 639 | Context-aware risk evaluation |

---

## Quick Usage

```python
from src.integrations.orchestration import (
    BusinessIntentRouter,
    create_mock_router,
    ITIntentCategory,
    RoutingDecision,
)

# Create router (mock for testing)
router = create_mock_router()

# Route user input
decision = await router.route("ETL Pipeline failed")
print(decision.intent_category)  # ITIntentCategory.INCIDENT
print(decision.routing_layer)    # "pattern"
print(decision.risk_level)       # RiskLevel.HIGH
```

---

## IT Intent Categories

| Category | Description | Example |
|----------|-------------|---------|
| INCIDENT | System failures, outages | "Database is down" |
| REQUEST | Service requests | "Need new VM provisioned" |
| CHANGE | Configuration changes | "Update firewall rules" |
| QUERY | Information queries | "What's the server status?" |
| UNKNOWN | Unclassifiable | Ambiguous or off-topic |

---

## Sprint History

| Sprint | Component | Focus |
|--------|-----------|-------|
| S91 | PatternMatcher | Regex rules, YAML config |
| S92 | SemanticRouter + LLMClassifier | Vector similarity + LLM fallback |
| S93 | BusinessIntentRouter | Three-layer coordinator + CompletenessChecker |
| S94 | GuidedDialogEngine | Multi-turn dialog, incremental updates |
| S95 | InputGateway | Source routing (ServiceNow, Prometheus) |
| S96 | RiskAssessor | Risk policies, context-aware scoring |
| S97 | HITL System | Approval workflows, Teams notifications |
| S99 | Metrics + Tests | OpenTelemetry, E2E test suite |

---

**Last Updated**: 2026-02-09
