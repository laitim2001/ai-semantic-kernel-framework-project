# V9 Module Deep-Dive: Integration Batch 2 (10 Smaller Modules, 9 Sections)

> **Scope**: patrol, correlation, rootcause, incident, audit, learning, a2a, n8n, contracts, shared
> **Analyst**: Claude Opus 4.6 | **Date**: 2026-03-29
> **Method**: Full source reading of key files per module specification

---

## Table of Contents

1. [patrol/](#module-patrol)
2. [correlation/](#module-correlation)
3. [rootcause/](#module-rootcause)
4. [incident/](#module-incident)
5. [audit/](#module-audit)
6. [learning/](#module-learning)
7. [a2a/](#module-a2a)
8. [n8n/](#module-n8n)
9. [contracts/ + shared/](#module-contracts--shared)
10. [Cross-Module Dependency Graph](#cross-module-dependency-graph)
11. [Consolidated Issues](#consolidated-issues)

---

### 事件處理與智能分析管線總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Integration Batch 2 — 事件處理管線                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────── 主動巡邏 (Proactive) ──────────────────────┐         │
│  │                                                                │         │
│  │  Cron 排程 ──→ PatrolAgent ──→ 健康檢查 ──→ 風險評分          │         │
│  │  (APScheduler)    │              (5 check types)  │            │         │
│  │                   ↓                               ↓            │         │
│  │              Claude 分析報告              PatrolReport          │         │
│  │                                                                │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────── 事件關聯 (Reactive) ───────────────────────┐         │
│  │                                                                │         │
│  │  系統事件 ──→ CorrelationAnalyzer ──→ 時間窗口聚合            │         │
│  │  (多來源)       │                       │                      │         │
│  │                 ↓                       ↓                      │         │
│  │          RootCauseAnalyzer ──→ 因果推理 + 置信度評分           │         │
│  │                 │                                              │         │
│  │                 ↓                                              │         │
│  │          IncidentAnalyzer ──→ 事件分類 + 優先級排序            │         │
│  │                 │                                              │         │
│  │                 ↓                                              │         │
│  │          ActionRecommender ──→ 修復建議 + ITIL SOP 匹配       │         │
│  │                                                                │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                               │                                             │
│                               ↓                                             │
│  ┌─────────────────── 學習反饋 (Learning) ───────────────────────┐         │
│  │                                                                │         │
│  │  Case 提取 ──→ 相似度計算 ──→ Few-shot 範例庫 ──→ 決策改善   │         │
│  │  (歷史案例)    (向量匹配)      (動態選擇)        (提升準確率) │         │
│  │                                                                │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                             │
│  ┌─────────────────── 稽核與互操作 ─────────────────────────────┐         │
│  │  audit/ ── 全程操作日誌    a2a/ ── Agent 間通訊協議           │         │
│  │  n8n/ ── 外部工作流整合    contracts/ + shared/ ── 共用型別   │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module: patrol

- **Path**: `backend/src/integrations/patrol/`
- **Files**: 11 (types.py, agent.py, scheduler.py, __init__.py + checks/: __init__.py, base.py, service_health.py, api_response.py, resource_usage.py, log_analysis.py, security_scan.py) | **Phase**: 23 (Sprint 82)
- **Purpose**: Proactive system health patrol — scheduled checks with risk scoring and Claude-powered analysis

### Public API

| Class / Function | File | Description |
|---|---|---|
| `PatrolAgent` | agent.py | Orchestrates patrol execution: runs registered checks, assesses risk, generates Claude-analyzed reports |
| `PatrolAgent.register_check(check_type, check_class)` | agent.py | Register a `PatrolCheck` subclass for a given `CheckType` |
| `PatrolAgent.execute_patrol(config, execution_id?) -> PatrolReport` | agent.py | Execute all checks for a config, return full report |
| `PatrolCheck` | agent.py | Inline abstract base class with `execute()` and `_create_result()` helper; **note**: concrete checks in `checks/` inherit from `BaseCheck` (checks/base.py), not `PatrolCheck` |
| `BaseCheck(ABC)` | checks/base.py | ABC base class for 5 concrete check implementations (ServiceHealthCheck, APIResponseCheck, ResourceUsageCheck, LogAnalysisCheck, SecurityScanCheck) |
| `PatrolScheduler` | scheduler.py | Cron-based scheduling via APScheduler (optional dep); supports manual trigger |
| `PatrolScheduler.schedule_patrol(config, callback) -> job_id` | scheduler.py | Register a patrol with cron expression |
| `PatrolScheduler.trigger_patrol(patrol_id, priority?) -> execution_id` | scheduler.py | Manual trigger of a registered patrol |
| `PatrolScheduler.cancel_patrol(patrol_id) -> bool` | scheduler.py | Remove a scheduled patrol |
| `PatrolScheduler.update_schedule(patrol_id, cron?, enabled?) -> bool` | scheduler.py | Reschedule or pause/resume |
| `calculate_risk_score(checks) -> float` | types.py | Sum-based risk score: HEALTHY=0, WARNING=20, CRITICAL=50, UNKNOWN=10; capped at 100 |
| `determine_overall_status(checks) -> PatrolStatus` | types.py | Worst-status aggregation |

**Key Data Types**: `PatrolConfig`, `CheckResult`, `RiskAssessment`, `PatrolReport`, `ScheduledPatrol`, `PatrolHistory`, `PatrolTriggerRequest/Response`

**Enums**: `PatrolStatus` (healthy/warning/critical/unknown), `CheckType` (5 types: service_health, api_response, resource_usage, log_analysis, security_scan), `ScheduleFrequency` (7 cron presets), `PatrolPriority` (low-critical)

**Constants**: `CHECK_DEFAULT_CONFIG` — default thresholds per CheckType (CPU 70/90%, memory 75/95%, disk 80/95%, etc.)

### Dependencies (imports from)

- Standard library only (asyncio, logging, datetime, uuid, typing)
- Optional: `apscheduler` (gracefully degrades to manual-only mode if not installed)

### Dependents (imported by)

- `integrations/hybrid/orchestrator/observability_bridge.py` — lazy imports `PatrolEngine` (not `PatrolAgent`; possible naming mismatch)
- `api/v1/patrol/` — API routes (assumed from module structure)

### Configuration

- `PatrolConfig` dataclass: patrol_id, name, check_types, cron_expression, enabled, priority, timeout_seconds (300), retry_count (3), notify_on_failure
- APScheduler: timezone=UTC, coalesce=True, max_instances=1, misfire_grace_time=60

### Test Coverage

- **No dedicated test files found** (`backend/tests/**/test_*patrol*` returned 0 results)

### Known Issues

| ID | Severity | Description |
|---|---|---|
| PAT-1 | MEDIUM | `observability_bridge.py` imports `PatrolEngine` but the module only defines `PatrolAgent` — likely naming mismatch or missing wrapper |
| PAT-2 | ~~MEDIUM~~ RESOLVED | ~~No concrete `PatrolCheck` implementations exist~~ — `checks/` subdirectory contains 5 concrete implementations: `ServiceHealthCheck`, `APIResponseCheck`, `ResourceUsageCheck`, `LogAnalysisCheck`, `SecurityScanCheck` (exported via `__init__.py`) |
| PAT-3 | LOW | `datetime.utcnow()` used throughout (deprecated in Python 3.12+) |
| PAT-4 | HIGH | Zero test coverage for this module |
| PAT-5 | LOW | `_running_patrols` is a plain dict without lock protection — concurrent executions could have race conditions |

---

## Module: correlation

- **Path**: `backend/src/integrations/correlation/`
- **Files**: 6 (types.py, analyzer.py, data_source.py, event_collector.py, graph.py, __init__.py) | **Phase**: 23 (Sprint 82) — **Sprint 130**: real data source migration
- **Purpose**: Multi-dimensional event correlation analysis (time, dependency, semantic) with graph visualization

### Public API

| Class / Function | File | Description |
|---|---|---|
| `CorrelationAnalyzer` | analyzer.py | Core analyzer: parallel execution of time/dependency/semantic correlation |
| `CorrelationAnalyzer.find_correlations(event, time_window?, types?, min_score?, max_results?) -> List[Correlation]` | analyzer.py | Find correlated events via 3 strategies |
| `CorrelationAnalyzer.analyze(query: DiscoveryQuery) -> CorrelationResult` | analyzer.py | Full analysis: correlations + graph + summary |
| `calculate_combined_score(time, dep, semantic) -> float` | types.py | Weighted: time=0.40, dependency=0.35, semantic=0.25 |
| `CorrelationGraph` | types.py | In-memory graph with add_node/add_edge/get_neighbors |
| `GraphBuilder` | graph.py | Builds `CorrelationGraph` from correlation lists; provides graph analysis and traversal |

**Key Data Types**: `Event`, `Correlation`, `GraphNode`, `GraphEdge`, `CorrelationGraph`, `DiscoveryQuery`, `CorrelationResult`

**Enums**: `CorrelationType` (time/dependency/semantic/causal), `EventSeverity` (info-critical), `EventType` (7 types: alert, incident, change, deployment, metric_anomaly, log_pattern, security)

**Scoring Weights** (CORRELATION_WEIGHTS): TIME=0.40, DEPENDENCY=0.35, SEMANTIC=0.25

### Dependencies (imports from)

- `.data_source` — `AzureMonitorConfig`, `EventDataSource` (Sprint 130)
- `.event_collector` — `CollectionConfig`, `EventCollector` (Sprint 130)
- Standard library only

### Dependents (imported by)

- `integrations/rootcause/analyzer.py` — imports `Correlation`, `CorrelationAnalyzer`, `CorrelationGraph`, `Event`
- `integrations/rootcause/case_matcher.py` — imports `Event`, `EventSeverity`
- `integrations/incident/analyzer.py` — imports `CorrelationAnalyzer`, `Correlation`, `Event`, `EventSeverity`, `EventType`
- `integrations/hybrid/orchestrator/observability_bridge.py` — lazy imports `CorrelationEngine`

### Configuration

- `_time_decay_factor = 0.1` — time proximity decay
- `_semantic_threshold = 0.6` — minimum semantic similarity

### Test Coverage

- `tests/unit/integrations/correlation/test_correlation_data_source.py` — unit test for data source
- `tests/unit/integrations/correlation/test_event_collector.py` — unit test for event collector
- `tests/integration/correlation/test_correlation_real.py` — integration test with real data

### Known Issues

| ID | Severity | Description |
|---|---|---|
| COR-1 | MEDIUM | `observability_bridge.py` imports `CorrelationEngine` but module defines `CorrelationAnalyzer` — naming mismatch |
| COR-2 | LOW | `CorrelationGraph` is fully in-memory with linear scan for neighbors — O(E) per query |
| COR-3 | INFO | Sprint 130 successfully removed all fake data; graceful fallback to empty results when no data source configured |

### Sprint 130 Changes

The Sprint 130 refactoring was a significant data integrity improvement:
- **Removed**: All hardcoded/fake event generation in `_get_event()`, `_get_events_in_range()`, `_get_dependencies()`, `_get_events_for_component()`, `_search_similar_events()`
- **Added**: Integration with `EventDataSource` and `EventCollector` abstractions
- **Behavior change**: Methods now return `None` or empty lists when no data source is configured (instead of fabricated data)
- **New files**: `data_source.py`, `event_collector.py` added in Sprint 130

---

## Module: rootcause

- **Path**: `backend/src/integrations/rootcause/`
- **Files**: 5 (types.py, analyzer.py, case_repository.py, case_matcher.py, __init__.py) | **Phase**: 23 (Sprint 82) — **Sprint 130**: real case repository
- **Purpose**: AI-driven root cause analysis with hypothesis generation, Claude reasoning, and historical case matching

### Public API

| Class / Function | File | Description |
|---|---|---|
| `RootCauseAnalyzer` | analyzer.py | 6-step analysis pipeline: context → history → hypotheses → Claude → factors → recommendations |
| `RootCauseAnalyzer.analyze_root_cause(event, correlations, graph?) -> RootCauseAnalysis` | analyzer.py | Full RCA pipeline execution |
| `RootCauseAnalyzer.get_similar_patterns(event, max_results?) -> List[HistoricalCase]` | analyzer.py | Historical case lookup via CaseMatcher |
| `calculate_overall_confidence(hypotheses) -> float` | types.py | Formula: `(max_confidence * 0.7 + evidence_factor * 0.3) - contradiction_penalty` |

**Key Data Types**: `RootCauseAnalysis`, `RootCauseHypothesis`, `Evidence`, `Recommendation`, `HistoricalCase`, `AnalysisContext`, `AnalysisRequest`

**Enums**: `AnalysisStatus` (pending/analyzing/completed/failed), `EvidenceType` (6 types: log, metric, trace, correlation, pattern, expert), `RecommendationType` (immediate/short_term/long_term/preventive)

**Analysis Depth Config**: quick (10 correlations, 30s), standard (50 correlations, 120s), deep (100 correlations, 300s)

### Hypothesis Generation Algorithm

1. Extract high-score correlations (>= 0.7), create hypotheses with `confidence = score * 0.8`
2. Match historical cases (>= 0.3 similarity), create hypotheses with `confidence = similarity * 0.7`
3. Sort by confidence descending, cap at 5 hypotheses

### Confidence Formula

```
overall = (max_hypothesis_confidence * 0.7 + evidence_factor * 0.3) - contradiction_penalty
evidence_factor = min(1.0, evidence_count / 5)
contradiction_penalty = min(0.3, contradicting_events_count * 0.1)
```

### Dependencies (imports from)

- `integrations/correlation` — `Correlation`, `CorrelationAnalyzer`, `CorrelationGraph`, `Event`
- `.case_matcher` — `CaseMatcher` (Sprint 130)
- `.case_repository` — `CaseRepository` (Sprint 130)

### Dependents (imported by)

- `integrations/incident/analyzer.py` — imports `RootCauseAnalyzer`, `RootCauseAnalysis`
- `integrations/hybrid/orchestrator/observability_bridge.py` — lazy imports `RootCauseAnalyzer`

### Configuration

- `_default_depth = "standard"` (50 max correlations, 120s timeout)

### Test Coverage

- `tests/unit/integrations/rootcause/test_case_matcher.py` — unit test for case matcher
- `tests/unit/integrations/rootcause/test_case_repository.py` — unit test for case repository
- `tests/integration/rootcause/test_rootcause_real.py` — integration test

### Known Issues

| ID | Severity | Description |
|---|---|---|
| RCA-1 | LOW | If no Claude client and no hypotheses, returns "Unable to determine root cause" with 0.0 confidence |
| RCA-2 | INFO | Sprint 130 successfully removed hardcoded historical cases; empty list when no case repository |
| RCA-3 | LOW | `_parse_claude_response()` uses simple line-based parsing — fragile if Claude response format varies |

---

## Module: incident

- **Path**: `backend/src/integrations/incident/`
- **Files**: 6 (types.py, analyzer.py, recommender.py, prompts.py, executor.py, __init__.py) | **Phase**: 34 (Sprint 126)
- **Purpose**: End-to-end IT incident handling pipeline: analysis, root cause, remediation recommendation, execution

### Public API

| Class / Function | File | Description |
|---|---|---|
| `IncidentAnalyzer` | analyzer.py | 5-step pipeline: event conversion → correlation → RCA → LLM enhancement → merge |
| `IncidentAnalyzer.analyze(context: IncidentContext) -> IncidentAnalysis` | analyzer.py | Full incident analysis with optional LLM enhancement |
| `ActionRecommender` | recommender.py | 2-tier remediation: rule templates + optional LLM augmentation |
| `ActionRecommender.recommend(analysis, context) -> List[RemediationAction]` | recommender.py | Generate sorted remediation actions |
| `IncidentExecutor` | executor.py | Risk-based execution routing: auto-execute (low risk), HITL approval (medium/high risk), MCP dispatch, ServiceNow writeback |
| `IncidentExecutor.execute(analysis, context, actions) -> List[ExecutionResult]` | executor.py | Execute remediation actions with risk-based routing |

**Key Data Types**: `IncidentContext`, `IncidentAnalysis`, `RemediationAction`, `ExecutionResult`

**Enums**: `IncidentSeverity` (P1-P4 mapping to ServiceNow), `IncidentCategory` (9 categories: network, server, application, database, security, storage, performance, authentication, other), `RemediationRisk` (auto/low/medium/high/critical), `RemediationActionType` (10 types), `ExecutionStatus` (8 states)

### Analysis Pipeline (5 steps)

```
IncidentContext → Event conversion → CorrelationAnalyzer.find_correlations()
    → RootCauseAnalyzer.analyze_root_cause() → LLM enhancement (optional)
    → Merge results → IncidentAnalysis with RemediationActions
```

### Confidence Merge Formula

When LLM enhancement is available:
- **Root cause**: Prefer LLM summary if non-empty
- **Confidence**: `rca_confidence * 0.4 + llm_confidence * 0.6` (LLM weighted higher)
- **Factors**: Deduplicated union of both, capped at 15

### Remediation Template Coverage

| Category | Action Type | Risk | Confidence | MCP Tool |
|---|---|---|---|---|
| STORAGE | clear_disk_space | AUTO | 0.85 | shell:run_command |
| APPLICATION | restart_service | LOW | 0.75 | shell:run_command |
| AUTHENTICATION | ad_account_unlock | AUTO | 0.90 | ldap:ad_operations |
| SERVER | scale_resource | MEDIUM | 0.70 | (none) |
| NETWORK | network_acl_change | HIGH | 0.60 | (none) |
| SECURITY | firewall_rule_change | CRITICAL | 0.55 | (none) |
| DATABASE | restart_database | MEDIUM | 0.65 | shell:run_command |
| PERFORMANCE | clear_cache | LOW | 0.70 | shell:run_command |

### Severity Confidence Boost

| Severity | Boost |
|---|---|
| P1 (Critical) | +0.10 |
| P2 (High) | +0.05 |
| P3 (Medium) | +0.00 |
| P4 (Low) | -0.05 |

### Dependencies (imports from)

- `integrations/correlation` — `CorrelationAnalyzer`, `Correlation`, `Event`, `EventSeverity`, `EventType`
- `integrations/rootcause` — `RootCauseAnalyzer`, `RootCauseAnalysis`
- `.prompts` — `INCIDENT_ANALYSIS_PROMPT`, `REMEDIATION_SUGGESTION_PROMPT`

### Dependents (imported by)

- `api/v1/incident/` — API routes (assumed)
- `tests/e2e/test_incident_pipeline.py` — E2E pipeline test
- `tests/e2e/test_incident_e2e_verification.py` — E2E verification

### Configuration

- `RemediationAction.confidence` validates range [0.0, 1.0] in `__post_init__`
- LLM calls use `temperature=0.3`, `max_tokens=1000-1500`

### Test Coverage

- `tests/unit/integrations/incident/test_analyzer.py` — unit test for incident analyzer
- `tests/unit/integrations/incident/test_executor.py` — unit test for incident executor
- `tests/unit/integrations/incident/test_recommender.py` — unit test for recommender
- `tests/unit/integrations/incident/test_types.py` — unit test for types
- `tests/unit/integrations/orchestration/test_incident_handler.py` — unit test for incident handler
- `tests/e2e/test_incident_pipeline.py` — E2E pipeline test
- `tests/e2e/test_incident_e2e_verification.py` — E2E verification

### Known Issues

| ID | Severity | Description |
|---|---|---|
| INC-1 | MEDIUM | 3 categories (SERVER, NETWORK, SECURITY) have no `mcp_tool` configured — cannot auto-execute |
| INC-2 | LOW | `_is_duplicate()` only checks title equality — actions with different titles but same effect pass through |
| INC-3 | INFO | Severity boost applied after LLM generation — LLM actions get boosted without LLM awareness of the boost |

---

## Module: audit

- **Path**: `backend/src/integrations/audit/`
- **Files**: 4 (types.py, decision_tracker.py, report_generator.py, __init__.py) | **Phase**: 23 (Sprint 80)
- **Purpose**: Decision audit trail — records AI decisions with full context, thinking process, alternatives, and quality scoring

### Public API

| Class / Function | File | Description |
|---|---|---|
| `DecisionTracker` | decision_tracker.py | Core tracker: record, update, query decisions with Redis cache + in-memory fallback |
| `DecisionTracker.record_decision(type, action, details, confidence, context?, thinking?, alternatives?) -> DecisionAudit` | decision_tracker.py | Create audit record |
| `DecisionTracker.update_outcome(decision_id, outcome, details?) -> DecisionAudit?` | decision_tracker.py | Update with auto quality scoring |
| `DecisionTracker.add_feedback(decision_id, feedback, quality_score?) -> DecisionAudit?` | decision_tracker.py | Manual feedback/scoring |
| `DecisionTracker.query_decisions(query: AuditQuery) -> List[DecisionAudit]` | decision_tracker.py | Multi-criteria query |
| `DecisionTracker.get_statistics(user_id?, start?, end?) -> Dict` | decision_tracker.py | Aggregate stats: by_type, by_outcome, avg_confidence, avg_quality, success_rate |
| `AuditReportGenerator` | report_generator.py | Generates human-readable audit reports from DecisionAudit records |
| `AuditReportGenerator.generate_report(audit) -> AuditReport` | report_generator.py | Single decision report with title, summary, explanation, risk analysis, recommendations |
| `AuditReportGenerator.generate_summary_report(audits, title?, ...) -> AuditReport` | report_generator.py | Aggregate summary report across multiple decisions |

**Key Data Types**: `DecisionAudit`, `DecisionContext`, `ThinkingProcess`, `AlternativeConsidered`, `AuditReport`, `AuditQuery`, `AuditConfig`

**Enums**: `DecisionType` (7 types: plan_generation, step_execution, tool_selection, fallback_selection, risk_assessment, approval_request, other), `DecisionOutcome` (5 states), `QualityRating` (5 levels: excellent >= 0.9, good >= 0.7, acceptable >= 0.5, poor >= 0.3, unacceptable < 0.3)

### Quality Score Formula

```python
base_score = 0.5
+ outcome_factor:  SUCCESS=+0.3, PARTIAL=+0.15, FAILURE=-0.2, CANCELLED=-0.1
+ confidence_alignment:  SUCCESS → +confidence*0.1,  FAILURE → -confidence*0.1
+ alternatives_bonus:  +0.05 if alternatives were considered
+ thinking_bonus:  +0.05 if thinking process documented
= clamp(0.0, 1.0)
```

**Score range**: [0.15, 0.95] in practice
- Best case: SUCCESS + high confidence + alternatives + thinking = 0.5 + 0.3 + 0.1 + 0.05 + 0.05 = 1.0
- Worst case: FAILURE + high confidence = 0.5 - 0.2 - 0.1 = 0.2

### Dependencies (imports from)

- `redis.asyncio` (optional, graceful fallback to in-memory)
- Standard library only

### Dependents (imported by)

- `api/v1/audit/decision_routes.py` — API routes for decision audit

### Configuration

`AuditConfig` dataclass:
| Setting | Default | Description |
|---|---|---|
| `enable_redis_cache` | True | Use Redis for persistence |
| `cache_ttl_seconds` | 3600 | Redis key expiry (1 hour) |
| `archive_after_days` | 90 | Days before archiving |
| `log_thinking_process` | True | Store extended thinking |
| `log_alternatives` | True | Store alternatives considered |
| `max_thinking_length` | 10000 | Max chars for thinking text |
| `auto_score_outcomes` | True | Auto-calculate quality on outcome update |
| `require_manual_review_below` | 0.5 | Threshold for manual review flag |

### Test Coverage

- `tests/unit/test_audit.py` — unit test for audit module

### Known Issues

| ID | Severity | Description |
|---|---|---|
| AUD-1 | HIGH | Primary storage is in-memory dict `_decisions` — data lost on restart. Redis is cache-only (TTL expires) |
| AUD-2 | MEDIUM | `query_decisions()` scans all in-memory decisions linearly — O(N) with no indexing |
| AUD-3 | MEDIUM | Redis connection uses `os.getenv()` instead of pydantic Settings (violates project convention) |
| AUD-4 | LOW | `get_statistics()` uses `limit=10000` as a cap — large datasets truncated silently |

---

## Module: learning

- **Path**: `backend/src/integrations/learning/`
- **Files**: 5 (types.py, few_shot.py, similarity.py, case_extractor.py, __init__.py) | **Phase**: 4 (Sprint 80)
- **Purpose**: Few-shot learning system — enhances AI prompts with relevant historical case examples

### Public API

| Class / Function | File | Description |
|---|---|---|
| `FewShotLearner` | few_shot.py | Core learner: find similar cases, enhance prompts, track effectiveness |
| `FewShotLearner.get_similar_cases(description, systems, category?, top_k?) -> List[SimilarityResult]` | few_shot.py | Semantic + structural similarity search |
| `FewShotLearner.enhance_prompt(base_prompt, description, systems, category?) -> LearningResult` | few_shot.py | Inject relevant case examples into a prompt |
| `FewShotLearner.track_effectiveness(enhancement_id, decision_id, success, improvement?, feedback?) -> LearningEffectiveness` | few_shot.py | Record outcome and update case quality scores |
| `FewShotLearner.store_successful_resolution(...) -> Case` | few_shot.py | Store a new case from a successful resolution |
| `FewShotLearner.get_effectiveness_stats() -> Dict` | few_shot.py | Aggregate effectiveness metrics |

**Key Data Types**: `Case`, `CaseMetadata`, `SimilarityResult` (semantic_score + structural_score + combined_score), `LearningResult`, `LearningEffectiveness`, `LearningConfig`

**Enums**: `CaseOutcome` (success/partial_success/failure/unknown), `CaseCategory` (8 categories: incident_resolution, performance_optimization, security_response, deployment_issue, configuration_change, user_support, system_maintenance, other)

### Case Matching Algorithm

1. Generate embedding for query description
2. Extract cases from memory (query text + optional category filter)
3. Generate embeddings for cases missing them
4. Rank via `SimilarityCalculator.rank_cases()` using weighted combination:
   - `combined_score = semantic_weight(0.7) * cosine_similarity + structural_weight(0.3) * jaccard_similarity`

### Quality Score Update

- On successful resolution: `quality_score += 0.05` (capped at 1.0)
- On failed resolution: `quality_score -= 0.02` (floored at 0.0)
- Asymmetric: success boosts 2.5x more than failure penalizes

### Dependencies (imports from)

- `.case_extractor` — `CaseExtractor`
- `.similarity` — `SimilarityCalculator`
- External: Requires `embedding_service` and `memory_manager` (injected at `initialize()`)

### Dependents (imported by)

- No direct production imports found (used via dependency injection)

### Configuration

`LearningConfig` dataclass:
| Setting | Default | Description |
|---|---|---|
| `top_k_cases` | 3 | Number of cases to retrieve |
| `min_quality_score` | 0.6 | Minimum case quality for selection |
| `min_similarity_score` | 0.5 | Minimum combined similarity |
| `semantic_weight` | 0.7 | Weight for embedding similarity |
| `structural_weight` | 0.3 | Weight for system-set Jaccard |
| `max_examples_in_prompt` | 3 | Max cases injected into prompt |
| `include_lessons_learned` | True | Include lessons in prompt |
| `include_resolution_steps` | True | Include resolution steps |
| `max_cases_per_category` | 100 | Category cap for case library |
| `case_expiry_days` | 365 | Case expiry period |

### Test Coverage

- `tests/unit/test_learning.py` — unit test

### Known Issues

| ID | Severity | Description |
|---|---|---|
| LRN-1 | MEDIUM | `_update_case_quality()` directly accesses `self._case_extractor._case_cache` — violates encapsulation |
| LRN-2 | LOW | `get_effectiveness_stats()` creates empty `LearningResult` for missing enhancement_ids — wasteful |
| LRN-3 | LOW | All state (history, effectiveness records) is in-memory — lost on restart |

---

## Module: a2a

- **Path**: `backend/src/integrations/a2a/`
- **Files**: 4 (protocol.py, discovery.py, router.py, __init__.py) | **Phase**: 23 (Sprint 81)
- **Purpose**: Agent-to-Agent communication protocol with message routing, capability discovery, and delivery tracking

### Public API

| Class / Function | File | Description |
|---|---|---|
| `A2AMessage` | protocol.py | Standard message format with TTL, priority, retry, correlation tracking |
| `A2AMessage.create(from, to, type, payload, ...) -> A2AMessage` | protocol.py | Factory method with auto-generated ID |
| `AgentCapability` | protocol.py | Agent declaration: capabilities, skills (proficiency map), availability score |
| `AgentCapability.can_handle(required) -> bool` | protocol.py | Check capability coverage |
| `AgentCapability.availability_score -> float` | protocol.py | `1.0 - (current_load / max_concurrent_tasks)` |
| `MessageRouter` | router.py | In-memory message routing with handler registration, queuing, retry, callbacks |
| `MessageRouter.register_handler(agent_id, handler)` | router.py | Register async/sync message handler |
| `MessageRouter.route_message(message, timeout?) -> bool` | router.py | Route to handler or queue if offline |
| `MessageRouter.process_queue(agent_id) -> int` | router.py | Drain queued messages for newly-online agent |
| `MessageRouter.get_conversation_messages(correlation_id) -> List` | router.py | Get all messages in a conversation chain |
| `MessageRouter.cleanup_expired() -> int` | router.py | Remove expired messages from tracking and queues |
| `AgentDiscoveryService` | discovery.py | Agent registration, discovery, heartbeat tracking, and stale-agent cleanup |
| `DiscoveryQuery` / `DiscoveryResult` | protocol.py | Agent discovery by capabilities, tags, availability |

**Enums**: `MessageType` (12 types across task/status/discovery/error categories), `MessagePriority` (low/normal/high/urgent), `MessageStatus` (6 states), `A2AAgentStatus` (online/busy/offline/maintenance)

### Message Routing Flow

```
route_message(msg) → handler registered?
    YES → execute handler (async or sync, with timeout) → DELIVERED
    NO  → queue_message() → PENDING (drained when handler registers + process_queue called)
    FAIL → retry_count < max_retries? → re-queue : FAILED
```

### Dependencies (imports from)

- Standard library only (asyncio, collections, datetime, uuid, typing)

### Dependents (imported by)

- `api/v1/a2a/routes.py` — A2A API endpoints

### Configuration

| Setting | Default | Description |
|---|---|---|
| `max_queue_size` | 1000 | Per-agent queue size limit |
| `default_timeout_seconds` | 30 | Handler execution timeout |
| `A2AMessage.ttl_seconds` | 300 | Message time-to-live |
| `A2AMessage.max_retries` | 3 | Maximum delivery retries |
| `AgentCapability.max_concurrent_tasks` | 5 | Agent concurrency limit |

### Test Coverage

- **No dedicated test files found** (`test_*a2a*` returned 0 results)

### Known Issues

| ID | Severity | Description |
|---|---|---|
| A2A-1 | HIGH | Zero test coverage |
| A2A-2 | MEDIUM | All state (messages, queues, handlers) is in-memory — no persistence |
| A2A-3 | LOW | `process_queue()` uses `queue.pop(0)` — O(N) operation; should use `collections.deque` |
| A2A-4 | LOW | Priority is stored on messages but not used in queue ordering — FIFO regardless of priority |
| A2A-5 | ~~INFO~~ RESOLVED | ~~No `DiscoveryService` implementation exists~~ — `AgentDiscoveryService` class exists in `discovery.py` with full registration, discovery, heartbeat tracking, and cleanup functionality |

---

## Module: n8n

- **Path**: `backend/src/integrations/n8n/`
- **Files**: 3 (orchestrator.py, monitor.py, __init__.py) | **Phase**: 38 (Sprint 125+)
- **Purpose**: Bidirectional IPA-n8n orchestration — IPA reasoning + n8n workflow execution + monitoring

### Public API

| Class / Function | File | Description |
|---|---|---|
| `N8nOrchestrator` | orchestrator.py | Full lifecycle orchestrator: reasoning → translation → execution → monitoring → consolidation |
| `N8nOrchestrator.orchestrate(request) -> OrchestrationResult` | orchestrator.py | Execute 6-phase flow |
| `N8nOrchestrator.set_reasoning_fn(fn)` | orchestrator.py | Inject custom reasoning function |
| `N8nOrchestrator.register_progress_callback(request_id, callback)` | orchestrator.py | Subscribe to progress updates |
| `N8nOrchestrator.handle_callback(request_id, data) -> bool` | orchestrator.py | Handle n8n webhook callbacks |
| `N8nOrchestrator.get_status(request_id) -> OrchestrationStatus?` | orchestrator.py | Query active orchestration status |

**Key Data Types**: `OrchestrationRequest`, `ReasoningResult`, `OrchestrationResult`

**Enum**: `OrchestrationStatus` (9 states: pending/reasoning/translating/executing/monitoring/completed/failed/timeout/cancelled)

### 6-Phase Orchestration Flow

```
Phase 1: IPA Reasoning (capped at 60s)
    → Intent classification, risk assessment, workflow recommendation
Phase 2: HITL Check
    → Auto-approve low/medium risk; block high/critical (returns PENDING)
Phase 3: Translation
    → Build n8n workflow input from reasoning + request context
Phase 4: Execute n8n Workflow
    → Call N8nApiClient.execute_workflow()
Phase 5: Monitor Execution
    → Poll via ExecutionMonitor.wait_for_completion() with progress callbacks
Phase 6: Consolidate Result
    → Build OrchestrationResult with full progress history
```

### Default Reasoning Function

Simple keyword-based classification (placeholder for production router):
- "reset/password/account/access" → REQUEST (medium risk)
- "down/error/fail/crash/outage" → INCIDENT (high risk, requires approval)
- "update/change/modify/config" → CHANGE (medium risk)
- "status/info/what/how/check" → QUERY (low risk)
- Everything else → UNKNOWN (low risk)
- Default confidence: 0.75

### Dependencies (imports from)

- `integrations/mcp/servers/n8n/client` — `N8nApiClient`, `N8nConfig`, error classes, `ExecutionStatus`
- `.monitor` — `ExecutionMonitor`, `ExecutionProgress`, `ExecutionState`, `MonitorConfig`

### Dependents (imported by)

- API routes (assumed from test structure)

### Configuration

- `N8nConfig` (from mcp/servers/n8n): base_url, api_key from env vars
- `MonitorConfig`: polling configuration
- `OrchestrationRequest.timeout`: overall timeout (default 300s)
- Reasoning timeout: capped at min(request.timeout, 60s)

### Test Coverage

- `tests/unit/integrations/n8n/test_n8n_orchestrator.py` — unit test
- `tests/unit/integrations/n8n/test_n8n_monitor.py` — unit test
- `tests/integration/n8n/test_n8n_integration.py` — integration test
- `tests/integration/n8n/test_n8n_mode3.py` — mode 3 integration test
- `tests/e2e/test_n8n_integration.py` — E2E test
- `tests/e2e/test_n8n_e2e_verification.py` — E2E verification

**Best test coverage among all 9 modules.**

### Known Issues

| ID | Severity | Description |
|---|---|---|
| N8N-1 | LOW | Default reasoning function is a simple keyword classifier — must be replaced with `BusinessIntentRouter` in production |
| N8N-2 | LOW | `_callback_results` dict is populated by `handle_callback()` but never consumed by the orchestration flow |
| N8N-3 | INFO | Supports async context manager (`async with N8nOrchestrator(config) as orch:`) |

---

## Module: contracts + shared

- **Path**: `backend/src/integrations/contracts/` + `backend/src/integrations/shared/`
- **Files**: 4 total (contracts: pipeline.py, __init__.py; shared: protocols.py, __init__.py) | **Phase**: 35 (Sprint 108) + 36 (Sprint 116)
- **Purpose**: Cross-module DTOs and Protocol interfaces for loose coupling between L5 (orchestration) and L6 (execution)

### contracts/pipeline.py — Pipeline DTOs

| Class | Base | Description |
|---|---|---|
| `PipelineRequest` | Pydantic BaseModel | Input to orchestration pipeline |
| `PipelineResponse` | Pydantic BaseModel | Output from orchestration pipeline |
| `PipelineSource` | Enum | user / servicenow / prometheus / api |

**PipelineRequest fields**:
- `content: str` — user input text
- `source: PipelineSource` — input source (default: USER)
- `mode: Optional[str]` — Sprint 144: user-selected mode (chat/workflow/swarm)
- `user_id, session_id: Optional[str]`
- `metadata: Dict[str, Any]`
- `timestamp: datetime`

**PipelineResponse fields**:
- `content: str` — response text
- `intent_category, confidence, risk_level, routing_layer: Optional` — routing metadata
- `execution_mode: Optional[str]` — Sprint 144: actual execution mode
- `suggested_mode: Optional[str]` — Sprint 144: routing suggestion
- `framework_used: str` — default "orchestrator_agent"
- `is_complete: bool` — default True
- `task_id: Optional[str]`
- `tool_calls: Optional[List[Dict]]` — Sprint 144: function calling results
- `processing_time_ms: Optional[float]`

### shared/protocols.py — Protocol Interfaces

| Protocol | Purpose | Methods |
|---|---|---|
| `ToolCallbackProtocol` | L5 receives tool events from L6 | `on_tool_call(event) -> Dict`, `on_tool_result(event) -> None` |
| `ExecutionEngineProtocol` | L6 provides execution to L5 | `execute(request) -> ExecutionResult`, `is_available() -> bool` |
| `OrchestrationCallbackProtocol` | L5 receives lifecycle events from L6 | `on_execution_started()`, `on_execution_completed()`, `on_execution_error()` |
| `SwarmCallbackProtocol` | L5 receives swarm events from L6 | `on_swarm_event(event) -> None` |

**Shared DTOs**:
- `ToolCallEvent` — tool invocation data (name, id, params, is_mcp, worker_id)
- `ToolResultEvent` — tool result data (status, result, error, duration_ms)
- `ExecutionRequest` — task execution request (intent, context, tools, max_tokens, timeout)
- `ExecutionResult` — execution outcome (success, content, framework_used, tool_calls, tokens_used)
- `SwarmEvent` — swarm coordination event (event_type, swarm_id, worker_id, data)

**Utility**: `check_protocol_compliance(instance, protocol) -> Dict` — runtime protocol validation

### Dependencies (imports from)

- `contracts/pipeline.py`: pydantic BaseModel, standard library
- `shared/protocols.py`: typing.Protocol (runtime_checkable), standard library only

### Dependents (imported by)

**contracts/pipeline.py**:
- `api/v1/orchestrator/routes.py` — imports `PipelineRequest`, `PipelineResponse`

**shared/protocols.py**:
- **No production consumers yet** — protocols defined but not imported by orchestration or claude_sdk modules
- `tests/unit/integrations/shared/test_protocols.py` — unit test exists

### Test Coverage

- `tests/unit/integrations/shared/test_protocols.py` — protocol tests
- `tests/e2e/test_incident_pipeline.py` — pipeline E2E (uses PipelineRequest indirectly)

### Known Issues

| ID | Severity | Description |
|---|---|---|
| CTR-1 | HIGH | `shared/protocols.py` defines 4 Protocol interfaces but **no production code imports them** — dead code risk |
| CTR-2 | INFO | `PipelineResponse` uses `execution_mode` and `suggested_mode` (Sprint 144) — mode switching design |
| CTR-3 | INFO | All 4 protocols are `@runtime_checkable` — enables `isinstance()` checks at runtime |

---

## Cross-Module Dependency Graph

```
                  contracts/pipeline
                       │
                       ▼
              api/v1/orchestrator/routes
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
  hybrid/         orchestration/      ag_ui/mediator
    │                                     │
    ▼                                     │
  observability_bridge ───────────────────┘
    │         │          │
    ▼         ▼          ▼
  patrol   correlation → rootcause
              │              │
              └──────┬───────┘
                     ▼
                 incident
                     │
                     ├── correlation (analyzer + types)
                     └── rootcause (analyzer + types)

  audit ←── api/v1/audit/decision_routes
  learning (standalone — injected via DI)
  a2a ←── api/v1/a2a/routes
  n8n ←── mcp/servers/n8n/client

  shared/protocols (UNUSED — 0 production imports)
```

### Dependency Chain Depth

- **Deepest**: `api → hybrid → observability_bridge → correlation → (data_source, event_collector)`
- **Incident aggregates**: correlation + rootcause (both transitive deps)
- **Isolated**: audit, learning, a2a (no cross-integration deps)

---

## Consolidated Issues

### By Severity

| Severity | Count | IDs |
|---|---|---|
| HIGH | 4 | PAT-4, AUD-1, A2A-1, CTR-1 |
| MEDIUM | 5 | PAT-1, ~~PAT-2 (RESOLVED)~~, COR-1, AUD-2, AUD-3, LRN-1 |
| LOW | 14 | PAT-3, PAT-5, COR-2, RCA-1, RCA-3, INC-2, INC-3, AUD-4, LRN-2, LRN-3, A2A-3, A2A-4, N8N-1, N8N-2 |
| INFO | 5 | COR-3, RCA-2, ~~A2A-5 (RESOLVED)~~, CTR-2, CTR-3, N8N-3 |

### Top Priority Actions

1. **Test coverage gaps** (PAT-4, A2A-1): patrol and a2a have zero dedicated tests
2. **Data persistence** (AUD-1): DecisionTracker uses volatile in-memory dict; Redis TTL expires data
3. **Dead protocols** (CTR-1): shared/protocols.py protocols are not imported by any production code
4. **Naming mismatches** (PAT-1, COR-1): observability_bridge imports `PatrolEngine` and `CorrelationEngine` but modules define `PatrolAgent` and `CorrelationAnalyzer`
5. ~~**No concrete PatrolCheck implementations** (PAT-2)~~: RESOLVED — `checks/` subdirectory has 5 implementations
6. **Priority queue not implemented** (A2A-4): messages have priority field but routing is FIFO

### Module Maturity Summary

| Module | Files | Tests | Data Source | Production Ready? |
|---|---|---|---|---|
| patrol | 11 | 0 | N/A (5 concrete checks) | Partial — has check implementations, but no tests |
| correlation | 6 | 3 | Sprint 130 real | Partial — needs data source config |
| rootcause | 5 | 3 | Sprint 130 real | Partial — needs case repo + Claude |
| incident | 6 | 7 | Via correlation/rootcause | Best in batch — full pipeline |
| audit | 4 | 1 | In-memory + Redis cache | No — volatile storage |
| learning | 5 | 1 | Via memory_manager DI | Partial — needs embedding service |
| a2a | 4 | 0 | In-memory only | No — no tests, no persistence (but has AgentDiscoveryService) |
| n8n | 3 | 6+ | Via n8n API client | Yes — best tested |
| contracts+shared | 4 | 1 | N/A (interfaces) | Partial — protocols unused |
