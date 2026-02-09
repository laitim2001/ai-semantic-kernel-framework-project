# Hybrid Integration — MAF + Claude SDK Bridge

> Phase 13-14 | ~60 Python files, ~21,000 LOC | Bidirectional framework bridging

---

## Directory Structure

```
hybrid/
├── __init__.py                 # 49 exports organized by Sprint
├── orchestrator_v2.py          # HybridOrchestratorV2 (1,254 LOC) — Main orchestrator
├── claude_maf_fusion.py        # ClaudeMAFFusion (892 LOC) — Sprint 81 fusion layer
│
├── intent/                     # Framework selection (1,223 LOC)
│   ├── router.py               # FrameworkSelector → ExecutionMode
│   ├── models.py               # ExecutionMode, IntentAnalysis, FrameworkAnalysis
│   ├── analyzers/
│   │   ├── complexity.py       # ComplexityAnalyzer
│   │   └── multi_agent.py      # MultiAgentDetector
│   └── classifiers/
│       ├── base.py             # BaseClassifier
│       └── rule_based.py       # RuleBasedClassifier
│
├── context/                    # Cross-framework context sync (3,080 LOC)
│   ├── bridge.py               # ContextBridge (932 LOC) — Bidirectional sync
│   ├── models.py               # MAFContext, ClaudeContext, HybridContext
│   ├── mappers/
│   │   ├── claude_mapper.py    # Claude → MAF mapping
│   │   └── maf_mapper.py       # MAF → Claude mapping
│   └── sync/
│       ├── synchronizer.py     # ContextSynchronizer (629 LOC)
│       ├── conflict.py         # ConflictResolver
│       └── events.py           # SyncEventPublisher
│
├── execution/                  # Unified tool execution (2,232 LOC)
│   ├── unified_executor.py     # UnifiedToolExecutor (797 LOC)
│   ├── tool_router.py          # ToolRouter — routes by source
│   ├── result_handler.py       # ResultHandler
│   └── tool_callback.py        # MAFToolCallback
│
├── checkpoint/                 # State persistence (4,341 LOC)
│   ├── models.py               # HybridCheckpoint
│   ├── storage.py              # UnifiedCheckpointStorage
│   ├── serialization.py        # CheckpointSerializer (compression)
│   ├── version.py              # CheckpointVersionMigrator
│   └── backends/
│       ├── memory.py           # MemoryCheckpointStorage (dev)
│       ├── redis.py            # RedisCheckpointStorage
│       ├── postgres.py         # PostgresCheckpointStorage
│       └── filesystem.py       # FilesystemCheckpointStorage
│
├── switching/                  # Dynamic mode switching (2,854 LOC)
│   ├── switcher.py             # ModeSwitcher (829 LOC)
│   ├── models.py               # SwitchTrigger, SwitchResult
│   ├── migration/
│   │   └── state_migrator.py   # StateMigrator (MAF↔Claude)
│   └── triggers/
│       ├── complexity.py       # ComplexityTriggerDetector
│       ├── failure.py          # FailureTriggerDetector
│       ├── resource.py         # ResourceTriggerDetector
│       └── user.py             # UserRequestTriggerDetector
│
├── risk/                       # Risk assessment (2,422 LOC)
│   ├── engine.py               # RiskAssessmentEngine (560 LOC)
│   ├── models.py               # RiskLevel, RiskAssessment
│   ├── analyzers/
│   │   ├── operation_analyzer.py
│   │   ├── context_evaluator.py
│   │   └── pattern_detector.py
│   └── scoring/
│       └── scorer.py           # RiskScorer
│
└── hooks/                      # HITL approval (439 LOC)
    └── approval_hook.py        # ApprovalHook
```

---

## Execution Flow

```
User Input
    ↓
FrameworkSelector → ExecutionMode (WORKFLOW / CHAT / HYBRID)
    ↓
HybridOrchestratorV2
    ├── ContextBridge — sync state MAF ↔ Claude
    ├── RiskAssessmentEngine — evaluate risk
    ├── UnifiedToolExecutor — execute tool calls
    ├── ApprovalHook — HITL approval
    └── UnifiedCheckpointStorage — persist state
    ↓
ModeSwitcher (if mode change detected)
    ├── ComplexityTrigger / FailureTrigger / ResourceTrigger
    └── StateMigrator — migrate state between modes
```

---

## Key Classes

| Class | File | LOC | Purpose |
|-------|------|-----|---------|
| **HybridOrchestratorV2** | orchestrator_v2.py | 1,254 | Main orchestration coordinator |
| **ContextBridge** | context/bridge.py | 932 | Bidirectional MAF↔Claude sync |
| **ClaudeMAFFusion** | claude_maf_fusion.py | 892 | Claude decisions in MAF workflows |
| **ModeSwitcher** | switching/switcher.py | 829 | Dynamic mode change detection |
| **UnifiedToolExecutor** | execution/unified_executor.py | 797 | Central tool execution with hooks |
| **ContextSynchronizer** | context/sync/synchronizer.py | 629 | Sync lifecycle & versioning |
| **RiskAssessmentEngine** | risk/engine.py | 560 | Multi-dimensional risk scoring |

---

## Sprint History

| Sprint | Component | Focus |
|--------|-----------|-------|
| S52 | FrameworkSelector | Framework selection, mode detection |
| S53 | ContextBridge | Cross-framework context sync |
| S54 | HybridOrchestratorV2 | Unified orchestration, tool execution |
| S55 | RiskAssessmentEngine | Multi-dimensional risk scoring |
| S56 | ModeSwitcher | Dynamic mode switching, triggers |
| S57 | UnifiedCheckpointStorage | State persistence (4 backends) |
| S81 | ClaudeMAFFusion | Claude decisions in MAF workflows |
| S98 | FrameworkSelector rename | Avoid confusion with BusinessIntentRouter |

---

## Known Issues

- **ContextSynchronizer**: Uses in-memory dict without locks (thread-safety risk)
- **MemoryCheckpointStorage**: Used as production default (should be PostgreSQL)

---

**Last Updated**: 2026-02-09
