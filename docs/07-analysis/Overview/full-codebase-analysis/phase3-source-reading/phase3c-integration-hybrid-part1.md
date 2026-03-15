# Phase 3C Analysis: Hybrid Integration Layer (Part 1)

> **Agent**: C3 | **Scope**: `backend/src/integrations/hybrid/` | **Files Analyzed**: 69 Python files
> **Features**: E4 (Hybrid Orchestration), F2 (Intent Router), B3 (Risk Assessment)

---

## 1. Executive Summary

The hybrid integration layer is the **central nervous system** of the IPA Platform, bridging Microsoft Agent Framework (MAF) and Claude Agent SDK into a unified orchestration layer. It spans ~21,000 LOC across 69 files organized into 8 subsystems: intent classification, context bridging, risk assessment, execution, switching, checkpoint, hooks, and the main orchestrator.

**Key Finding**: The original `HybridOrchestratorV2` (1,254 LOC) was identified as a God Object in Sprint 132 and has been **deprecated in favor of `OrchestratorMediator`** which decomposes responsibilities into 6 specialized handlers. However, `HybridOrchestratorV2` still exists as a backward-compatibility facade that delegates internally to the mediator, meaning both classes coexist in the codebase.

---

## 2. Architecture Overview

### 2.1 Subsystem Map

```
hybrid/
├── intent/          # Framework selection (1,223 LOC)
│   ├── router.py           → FrameworkSelector (main entry)
│   ├── models.py            → ExecutionMode, IntentAnalysis, SessionContext
│   ├── classifiers/
│   │   ├── base.py          → BaseClassifier (ABC)
│   │   └── rule_based.py    → RuleBasedClassifier (keyword patterns)
│   └── analyzers/
│       ├── complexity.py    → ComplexityAnalyzer (step/dependency scoring)
│       └── multi_agent.py   → MultiAgentDetector (collaboration detection)
│
├── context/         # Cross-framework sync (3,080 LOC)
│   ├── bridge.py            → ContextBridge (932 LOC, bidirectional sync)
│   ├── models.py            → MAFContext, ClaudeContext, HybridContext
│   ├── mappers/
│   │   ├── maf_mapper.py    → MAF → Claude state transformation
│   │   └── claude_mapper.py → Claude → MAF state transformation
│   └── sync/
│       ├── synchronizer.py  → ContextSynchronizer (629 LOC, distributed locks)
│       ├── conflict.py      → ConflictResolver
│       └── events.py        → SyncEventPublisher
│
├── risk/            # Risk assessment (2,422 LOC)
│   ├── engine.py            → RiskAssessmentEngine (560 LOC)
│   ├── models.py            → RiskLevel, RiskFactor, RiskConfig
│   ├── analyzers/
│   │   ├── operation_analyzer.py → Tool/command risk
│   │   ├── context_evaluator.py  → Session behavioral context
│   │   └── pattern_detector.py   → Historical pattern anomalies
│   └── scoring/
│       └── scorer.py        → RiskScorer (3 strategies)
│
├── orchestrator/    # Mediator Pattern (Sprint 132)
│   ├── mediator.py          → OrchestratorMediator (replacement for V2)
│   ├── contracts.py         → Handler ABC, HandlerType, OrchestratorRequest
│   ├── events.py            → OrchestratorEvent, EventType
│   └── handlers/
│       ├── routing.py       → RoutingHandler
│       ├── dialog.py        → DialogHandler
│       ├── approval.py      → ApprovalHandler
│       ├── execution.py     → ExecutionHandler
│       ├── context.py       → ContextHandler
│       └── observability.py → ObservabilityHandler
│
├── orchestrator_v2.py  # DEPRECATED God Object (1,254 LOC) → delegates to Mediator
├── claude_maf_fusion.py # Claude decisions in MAF workflows (892 LOC)
└── swarm_mode.py        # Swarm execution mode (Sprint 116)
```

### 2.2 Dependency Graph

```
orchestrator_v2.py (facade)
    ├── OrchestratorMediator (Sprint 132 replacement)
    │   ├── RoutingHandler → BusinessIntentRouter, FrameworkSelector
    │   ├── DialogHandler → GuidedDialogEngine
    │   ├── ApprovalHandler → HITLController, RiskAssessor
    │   ├── ExecutionHandler → UnifiedToolExecutor, claude_executor, maf_executor
    │   ├── ContextHandler → ContextBridge
    │   └── ObservabilityHandler → metrics, logging
    │
    ├── Phase 28 (orchestration/) components:
    │   ├── InputGateway
    │   ├── BusinessIntentRouter
    │   ├── GuidedDialogEngine
    │   ├── RiskAssessor
    │   └── HITLController
    │
    ├── Phase 13 (hybrid/) components:
    │   ├── FrameworkSelector (intent/router.py)
    │   ├── ContextBridge (context/bridge.py)
    │   ├── UnifiedToolExecutor (execution/)
    │   └── MAFToolCallback (execution/)
    │
    └── Sprint 116:
        └── SwarmModeHandler (swarm_mode.py)
```

---

## 3. Context Bridge: MAF <-> Claude Context Sync

### 3.1 Architecture

The `ContextBridge` (932 LOC) provides **bidirectional context synchronization** between MAF workflows and Claude sessions.

**Data Flow**:
```
MAF Context                          Claude Context
─────────────                        ──────────────
workflow_id          ──────►         session metadata
checkpoint_data      ──────►         context_variables
execution_history    ──────►         conversation_history (summarized)
pending_approvals    ──────►         tool_call_history (pending)
agent_states         ──────►         system_prompt (appended)

                     ◄──────         context_variables → checkpoint_data
                     ◄──────         conversation_history → execution_history
                     ◄──────         tool_call_history → checkpoint updates
```

**Key Methods**:
- `sync_to_claude(maf_context)` — Maps MAF state to Claude session
- `sync_to_maf(claude_context)` — Maps Claude session back to MAF
- `merge_contexts()` — Creates unified `HybridContext` from both
- `sync_bidirectional()` — Full bidirectional sync with conflict detection
- `sync_after_execution()` — Post-execution state update

### 3.2 Mapper Layer

Two mappers handle state transformation:

- **MAFMapper** (`mappers/maf_mapper.py`): Converts MAF checkpoints to Claude context variables, MAF execution records to Claude message history, agent states to system prompt additions
- **ClaudeMapper** (`mappers/claude_mapper.py`): Converts Claude context variables back to MAF checkpoints, Claude conversation to MAF execution records

Both mappers are injected via Protocol (structural typing), with default fallback implementations built into `ContextBridge`.

### 3.3 Race Condition Analysis

**ContextSynchronizer** (`sync/synchronizer.py`, 629 LOC):

The V2 analysis flagged a thread-safety concern. After reading the code, the situation is:

1. **Sprint 119 merged** the hybrid and claude_sdk synchronizer implementations into a single module
2. The synchronizer uses **distributed locking** with Redis as primary and asyncio.Lock as fallback
3. Uses **optimistic locking** via version control — each sync increments version, conflicts detected via version mismatch
4. The `_sessions` dict stores session state, protected by `_sync_locks` (per-session asyncio locks when Redis unavailable)

**Verdict**: The synchronizer is **mostly race-condition safe** for single-process deployments. It uses per-session asyncio locks and version-based optimistic locking. However:

- **Risk**: The `ContextBridge._context_cache` (a plain `Dict[str, HybridContext]`) in `bridge.py` has **NO locking**. Multiple concurrent async operations on the same session could corrupt cache state.
- **Risk**: The fallback asyncio.Lock is per-process only — multi-worker deployments without Redis would have race conditions across workers.
- **Mitigation**: Redis distributed locks are available but require Redis to be configured.

### 3.4 Conflict Resolution

`ConflictResolver` (`sync/conflict.py`) handles merge conflicts when both MAF and Claude contexts have been modified since last sync:
- **Detection**: Compares `last_updated` timestamps vs `last_sync` timestamps
- **Resolution Strategies**: `MAF_PRIMARY`, `CLAUDE_PRIMARY`, `MERGE` (configurable)
- **Threshold**: Conflicts flagged when time difference > 60 seconds and both sides modified

---

## 4. Intent Classification System

### 4.1 Framework Selection Pipeline

```
User Input
    │
    ▼
FrameworkSelector (router.py)
    │
    ├── RuleBasedClassifier (fast, deterministic)
    ├── ComplexityAnalyzer (step/dependency scoring)
    ├── MultiAgentDetector (collaboration patterns)
    └── [LLM Classifier] (fallback, not yet implemented)
    │
    ▼
Weighted Voting Aggregation
    │
    ▼
ExecutionMode Decision
    ├── WORKFLOW_MODE → MAF (structured multi-step)
    ├── CHAT_MODE → Claude (conversational)
    └── HYBRID_MODE → Dynamic switching
```

### 4.2 Classifiers Detail

#### RuleBasedClassifier (`classifiers/rule_based.py`)

**Bilingual keyword matching** (English + Traditional Chinese) with three pattern categories:

| Category | Example Keywords | Maps To |
|----------|-----------------|---------|
| **WORKFLOW_KEYWORDS** | "workflow", "pipeline", "multi-step", "automate", "orchestrate", "工作流程", "自動化", "多步驟" | `WORKFLOW_MODE` |
| **CHAT_KEYWORDS** | "help", "explain", "what is", "tell me", "解釋", "說明", "什麼是" | `CHAT_MODE` |
| **HYBRID_KEYWORDS** | "analyze and then", "first check then", "先分析再" | `HYBRID_MODE` |

**Scoring**: Each keyword match increments the mode score. Confidence = `matches / (matches + 1)` with a max cap. Supports context boosting (if session has active workflow, boost WORKFLOW score).

#### ComplexityAnalyzer (`analyzers/complexity.py`)

Scores task complexity across 6 dimensions:

| Dimension | Detection Method | Weight |
|-----------|-----------------|--------|
| **Step Count** | Regex patterns ("3 steps", "第三步") | High |
| **Sequential Indicators** | "first...then...finally" patterns | Medium |
| **Resource Dependencies** | "database", "API", "file system" keywords | Medium |
| **Time Requirements** | "schedule", "periodic", "daily" keywords | Medium |
| **Persistence Needs** | "save", "checkpoint", "resume" keywords | High |
| **Batch Processing** | "all files", "entire database" patterns | Medium |

**Threshold**: Complexity score > 0.6 triggers `WORKFLOW_MODE` recommendation.

#### MultiAgentDetector (`analyzers/multi_agent.py`)

Detects collaboration requirements via:
- **Explicit keywords**: "multiple agents", "multi-agent", "多代理"
- **Skill domain counting**: If input references 3+ distinct domains (coding, data analysis, design, etc.)
- **Collaboration indicators**: "handoff", "coordinate", "分工合作"
- **Role references**: "analyst", "developer", "reviewer" patterns

**Result**: If multi-agent signals detected, recommends `WORKFLOW_MODE` for MAF orchestration.

### 4.3 Aggregation

`FrameworkSelector._aggregate_results()` uses **weighted voting**:
1. Each classifier produces `(mode, confidence, weight)`
2. Raw weighted scores aggregated per mode: `score += confidence * weight`
3. Best mode selected by highest aggregate score
4. Final confidence = weighted average of winning mode's confidences
5. If confidence < threshold (default 0.7), falls back to `CHAT_MODE`

### 4.4 Framework Mapping

Once mode is determined:
- `WORKFLOW_MODE` → `SuggestedFramework.MAF`
- `CHAT_MODE` → `SuggestedFramework.CLAUDE`
- `HYBRID_MODE` → Check session context; if workflow active → MAF, else → HYBRID

---

## 5. Risk Assessment Engine

### 5.1 Architecture

```
OperationContext (tool_name, command, environment, session_id)
    │
    ▼
RiskAssessmentEngine.assess()
    │
    ├── OperationAnalyzer → tool/command risk factors
    ├── ContextEvaluator → session behavioral context
    ├── PatternDetector → historical anomaly detection
    └── [History Analysis] → frequency/escalation patterns
    │
    ▼
RiskScorer.calculate() → ScoringResult
    │
    ▼
Context Adjustment (environment multiplier)
    │
    ▼
RiskLevel.from_score() → RiskAssessment
    ├── requires_approval?
    └── approval_reason
```

### 5.2 Risk Factor Types

```python
class RiskFactorType(Enum):
    OPERATION   # Tool/action type risk (Read=0.1, Bash=0.6)
    CONTEXT     # Session behavioral context
    PATTERN     # Behavioral patterns and anomalies
    PATH        # File path sensitivity
    COMMAND     # Command execution risk (rm, chmod, etc.)
    FREQUENCY   # High operation frequency
    ESCALATION  # Risk escalation pattern detected
```

### 5.3 Risk Level Thresholds

From `RiskConfig`:

| Level | Score Range | Approval Required | Description |
|-------|------------|-------------------|-------------|
| **LOW** | 0.0 - 0.3 | No | Auto-approved, minimal risk |
| **MEDIUM** | 0.3 - 0.6 | No | Auto-approved with logging |
| **HIGH** | 0.6 - 0.85 | **Yes** | Requires human approval |
| **CRITICAL** | 0.85 - 1.0 | **Yes** | Immediate attention required |

**Dangerous command override**: Commands classified as "dangerous" or "critical" bypass environment multiplier and enforce minimum scores (0.75 for dangerous, 0.92 for critical) to guarantee HIGH/CRITICAL classification.

### 5.4 Scoring Strategies

`RiskScorer` supports 3 strategies:

| Strategy | Formula | Use Case |
|----------|---------|----------|
| **WEIGHTED_AVERAGE** | `sum(score * weight) / sum(weight)` | Standard balanced assessment |
| **MAX_WEIGHTED** | `max(score * weight)` | Conservative, single-threat focused |
| **HYBRID** | `0.6 * avg + 0.4 * max` | Balanced with high-risk sensitivity |

### 5.5 Base Tool Risk Scores

When no analyzers are registered, base risk by tool type:

| Tool | Base Risk | Rationale |
|------|-----------|-----------|
| Read, Glob, Grep | 0.1 | Read-only operations |
| Task | 0.3 | Sub-agent delegation |
| Write, Edit | 0.4 | File modification |
| MultiEdit | 0.5 | Batch file modification |
| Bash | 0.6 | Shell command execution |

### 5.6 History-Based Risk Factors

The engine maintains an `AssessmentHistory` (sliding window, max 100 entries):
- **Frequency analysis**: >10 operations in window → adds frequency risk factor (score up to 0.5)
- **Escalation detection**: 3 consecutive assessments with increasing scores → adds 0.4 escalation factor

---

## 6. HybridOrchestratorV2: God Object Analysis

### 6.1 Dependency Count

The constructor accepts **13 injectable dependencies** (plus 1 backward-compat alias):

```python
def __init__(self, *,
    config: Optional[OrchestratorConfig],
    # Phase 28 (5 dependencies)
    input_gateway: Optional[InputGateway],
    business_router: Optional[BusinessIntentRouter],
    guided_dialog: Optional[GuidedDialogEngine],
    risk_assessor: Optional[RiskAssessor],
    hitl_controller: Optional[HITLController],
    # Sprint 116 (1 dependency)
    swarm_handler: Optional[SwarmModeHandler],
    # Phase 13 (5 dependencies)
    framework_selector: Optional[FrameworkSelector],
    context_bridge: Optional[ContextBridge],
    unified_executor: Optional[UnifiedToolExecutor],
    maf_callback: Optional[MAFToolCallback],
    claude_executor: Optional[Callable],
    maf_executor: Optional[Callable],
    # Backward compat (1 alias)
    intent_router: Optional[FrameworkSelector],
)
```

### 6.2 Responsibilities (Pre-Sprint 132)

The class originally handled **all of the following** directly:

| # | Responsibility | Method(s) |
|---|---------------|-----------|
| 1 | Request processing entry | `process_request()`, `execute_with_routing()` |
| 2 | Input gateway processing | `_process_input_gateway()` |
| 3 | Intent/routing classification | `_classify_intent()`, `_analyze_intent()` |
| 4 | Guided dialog management | `_handle_guided_dialog()` |
| 5 | Risk assessment | `_assess_risk()` |
| 6 | HITL approval flow | `_handle_hitl_approval()` |
| 7 | Swarm mode detection/execution | `_handle_swarm_mode()` |
| 8 | Framework selection | `_select_framework()` |
| 9 | Context preparation | `_prepare_hybrid_context()` |
| 10 | Chat mode execution | `_execute_chat_mode()` |
| 11 | Workflow mode execution | `_execute_workflow_mode()` |
| 12 | Hybrid mode execution | `_execute_hybrid_mode()` |
| 13 | Post-execution sync | `_sync_after_execution()` |
| 14 | Metrics tracking | `_update_metrics()`, `get_metrics()` |
| 15 | Error handling/fallback | `_handle_error()`, `_fallback_to_chat()` |

**Verdict: YES, this is a God Object** — 15+ distinct responsibilities, 13 dependencies, 1,254 LOC. It violates Single Responsibility Principle comprehensively.

### 6.3 Sprint 132 Mediator Refactoring

Sprint 132 introduced `OrchestratorMediator` to decompose the God Object:

```python
class OrchestratorMediator:
    """Sprint 132: Central coordinator replacing HybridOrchestratorV2 God Object."""

    def __init__(self, *,
        context_bridge: ContextBridge,
        tool_executor: UnifiedToolExecutor,
        handlers: Dict[HandlerType, Handler]  # 6 specialized handlers
    )
```

**Handler Chain** (6 handlers, executed in sequence):

| Order | Handler | Extracted From | Responsibility |
|-------|---------|---------------|----------------|
| 1 | `RoutingHandler` | `_classify_intent()`, `_analyze_intent()` | Intent classification, routing decision |
| 2 | `DialogHandler` | `_handle_guided_dialog()` | Missing info gathering |
| 3 | `ApprovalHandler` | `_assess_risk()`, `_handle_hitl_approval()` | Risk assessment + HITL approval |
| 4 | `ExecutionHandler` | `_execute_*_mode()` | Framework execution dispatch |
| 5 | `ContextHandler` | `_prepare_hybrid_context()`, `_sync_after_execution()` | Context lifecycle |
| 6 | `ObservabilityHandler` | `_update_metrics()` | Metrics and logging |

**Contract**:
```python
class Handler(ABC):
    @property
    def handler_type(self) -> HandlerType: ...
    def can_handle(self, request, context) -> bool: ...
    async def handle(self, request, context) -> HandlerResult: ...
```

Each handler receives an `OrchestratorRequest` and shared context dict, returning a `HandlerResult` with `should_continue` flag to control pipeline flow.

### 6.4 Current State: Facade Pattern

`HybridOrchestratorV2` is now marked `@deprecated` but preserved as a **facade**:
- All public methods (`process_request()`, `execute_with_routing()`) still work
- Internally delegates to `OrchestratorMediator` for new-style processing
- Backward compatibility maintained for existing API routes and callers
- New code should use `OrchestratorMediator` directly

---

## 7. Execution Flow: End-to-End

### 7.1 Full Pipeline (Phase 28 + Sprint 116)

```
User Request (prompt, session_id)
    │
    ▼
[1] InputGateway.process()
    │   - Source identification (API, CLI, webhook, etc.)
    │   - Request normalization
    │
    ▼
[2] BusinessIntentRouter.route() (Phase 28 Three-tier)
    │   - Layer 1: PatternMatcher (<10ms)
    │   - Layer 2: SemanticRouter (<100ms)
    │   - Layer 3: LLMClassifier (<2000ms)
    │   → RoutingDecision (intent_category, completeness)
    │
    ▼
[3] Check completeness.is_sufficient
    │   ├── No → GuidedDialogEngine.generate_response()
    │   │        → Return dialog prompt to user
    │   └── Yes → Continue
    │
    ▼
[4] RiskAssessor.assess()
    │   → RiskAssessment (level, requires_approval)
    │
    ▼
[5] HITLController (if requires_approval)
    │   ├── Approved → Continue
    │   ├── Rejected → Return rejection
    │   └── Pending → Return pending status
    │
    ▼
[5.5] SwarmModeHandler.should_use_swarm() (Sprint 116)
    │   ├── Yes → Execute swarm, return result
    │   └── No → Continue to framework selection
    │
    ▼
[6] FrameworkSelector.select_framework()
    │   - RuleBasedClassifier
    │   - ComplexityAnalyzer
    │   - MultiAgentDetector
    │   → IntentAnalysis (mode, confidence, suggested_framework)
    │
    ▼
[7] ContextBridge.get_or_create_hybrid()
    │   → HybridContext (MAF + Claude state)
    │
    ▼
[8] Execute based on mode:
    │   ├── WORKFLOW_MODE → maf_executor(prompt, context)
    │   ├── CHAT_MODE → claude_executor(prompt, context)
    │   └── HYBRID_MODE → claude_executor with MAF fallback
    │
    ▼
[9] ContextBridge.sync_after_execution()
    │   → Update HybridContext with result
    │
    ▼
[10] Return HybridResultV2
     (content, framework_used, execution_mode, intent_analysis, metrics)
```

### 7.2 Dual Router Distinction

The system has **two distinct routing layers**:

| Router | Location | Purpose | Speed |
|--------|----------|---------|-------|
| **BusinessIntentRouter** | `orchestration/intent_router/` | Classifies IT intent category (Incident, Service Request, Change, etc.) | Three-tier: <10ms / <100ms / <2s |
| **FrameworkSelector** | `hybrid/intent/router.py` | Selects execution framework (MAF vs Claude vs Hybrid) | Single-pass: <50ms |

These are **complementary, not competing**: BusinessIntentRouter determines *what* the request is about; FrameworkSelector determines *how* to execute it.

---

## 8. ClaudeMAFFusion

`ClaudeMAFFusion` (892 LOC) is a **separate integration path** from `HybridOrchestratorV2`:

- **Purpose**: Enables Claude to make decisions *within* MAF workflow steps
- **Use Case**: When a MAF workflow step requires Claude intelligence (reasoning, classification, generation)
- **Difference from HybridOrchestratorV2**: V2 selects *between* frameworks; Fusion uses Claude *inside* MAF workflows
- Contains `ClaudeDecisionEngine` for step-level Claude invocations and `DynamicWorkflow` for Claude-modified workflow definitions

---

## 9. Cross-Reference: Feature Coverage

| Feature | Status | Location | Notes |
|---------|--------|----------|-------|
| **E4 (Hybrid Orchestration)** | Implemented + Refactored | `orchestrator_v2.py` + `orchestrator/mediator.py` | God Object decomposed via Mediator Pattern in Sprint 132 |
| **F2 (Intent Router)** | Implemented | `intent/router.py` (FrameworkSelector) + `orchestration/intent_router/` (BusinessIntentRouter) | Two-layer routing: IT intent + framework selection |
| **B3 (Risk Assessment)** | Implemented | `risk/engine.py` + `risk/analyzers/` + `risk/scoring/` | 7 factor types, 3 scoring strategies, 4 risk levels |

---

## 10. Issues and Recommendations

### 10.1 Critical Issues

| # | Issue | Severity | Location | Description |
|---|-------|----------|----------|-------------|
| 1 | **ContextBridge cache not thread-safe** | HIGH | `context/bridge.py:157` | `_context_cache: Dict[str, HybridContext]` has no locking. Concurrent async operations on same session can corrupt state. |
| 2 | **God Object facade still primary entry** | MEDIUM | `orchestrator_v2.py` | Despite deprecation, `HybridOrchestratorV2` remains the primary API entry point. Migration to `OrchestratorMediator` incomplete. |
| 3 | **Memory checkpoint in production** | MEDIUM | `checkpoint/backends/memory.py` | `MemoryCheckpointStorage` used as default. Data lost on restart. Should default to PostgreSQL. |

### 10.2 Architectural Observations

| # | Observation | Impact |
|---|-------------|--------|
| 1 | Two routing systems (BusinessIntentRouter + FrameworkSelector) are well-separated but could confuse developers | Documentation should emphasize their complementary nature |
| 2 | All Phase 28 dependencies in orchestrator_v2 are Optional with None defaults | Graceful degradation works but masks missing configuration at runtime |
| 3 | Risk engine hooks (pre_assess, post_assess, on_high_risk) are synchronous | Could block event loop if hooks perform I/O |
| 4 | Sprint 132 Mediator decomposition is clean and well-structured | Good application of Mediator + Chain of Responsibility patterns |
| 5 | Bilingual keyword support (EN + ZH-TW) throughout classifiers | Well-implemented for target market (Taiwan/Hong Kong) |

### 10.3 Metrics

| Metric | Value |
|--------|-------|
| Total files in scope | 69 |
| Total estimated LOC | ~21,000 |
| Largest file | `orchestrator_v2.py` (1,254 LOC) |
| Dependencies of orchestrator_v2 | 13 injectable + 8 imports |
| Handler types in Mediator | 6 |
| Risk factor types | 7 |
| Risk scoring strategies | 3 |
| Classifier types | 3 (rule-based, complexity, multi-agent) + 1 planned (LLM) |
| Context sync directions | 3 (MAF→Claude, Claude→MAF, Bidirectional) |
| Checkpoint backends | 4 (Memory, Redis, PostgreSQL, Filesystem) |

---

*Analysis completed by Agent C3. All 69 Python files in `backend/src/integrations/hybrid/` read and analyzed.*
