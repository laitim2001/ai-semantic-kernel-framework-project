# V9 Dependency Analysis — Deep Semantic Verification Report

> **Date**: 2026-03-31
> **Method**: Manual grep-based import chain tracing for all 11 circular dependencies
> **Source**: `docs/07-analysis/V9/06-cross-cutting/dependency-analysis.md`
> **Score**: 50/50 pts

---

## CRITICAL Severity (C1-C2): 10/10 pts

### C1: agent_framework <-> hybrid (CRITICAL) — VERIFIED ✅

| Direction | File | Import Statement | Status |
|-----------|------|------------------|--------|
| agent_framework -> hybrid | `builders/concurrent.py:75` | `from src.integrations.hybrid.execution import MAFToolCallback` | ✅ EXISTS |
| agent_framework -> hybrid | `builders/groupchat.py:72` | `from src.integrations.hybrid.execution import MAFToolCallback` | ✅ EXISTS |
| agent_framework -> hybrid | `builders/handoff.py:47` | `from src.integrations.hybrid.execution import MAFToolCallback` | ✅ EXISTS |
| hybrid -> agent_framework | `orchestrator/dispatch_handlers.py:160` | `from src.integrations.agent_framework.builders.workflow_executor import ...` | ✅ EXISTS |
| hybrid -> agent_framework | `orchestrator/bootstrap.py:441` | `from src.integrations.agent_framework.builders.workflow_executor import ...` | ✅ EXISTS |

**P1-P5: 5/5** — Bidirectional cycle confirmed. All lazy imports (inside functions/methods).

### C2: agent_framework <-> domain/workflows (CRITICAL) — VERIFIED ✅

| Direction | File | Import Statement | Status |
|-----------|------|------------------|--------|
| agent_framework -> domain/workflows | `core/workflow.py:44` | `from src.domain.workflows.models import ...` | ✅ EXISTS (top-level) |
| agent_framework -> domain/workflows | `core/edge.py:32` | `from src.domain.workflows.models import WorkflowEdge` | ✅ EXISTS (top-level) |
| agent_framework -> domain/workflows | `core/executor.py:41` | `from src.domain.workflows.models import WorkflowNode, NodeType` | ✅ EXISTS (top-level) |
| agent_framework -> domain/workflows | `core/context.py:31` | `from src.domain.workflows.models import WorkflowContext` | ✅ EXISTS (top-level) |
| domain/workflows -> agent_framework | `service.py:28` | `from src.integrations.agent_framework.core.executor import ...` | ✅ EXISTS (top-level) |
| domain/workflows -> agent_framework | `service.py:34` | `from src.integrations.agent_framework.core.execution import ...` | ✅ EXISTS (top-level) |
| domain/workflows -> agent_framework | `service.py:39` | `from src.integrations.agent_framework.core.events import ...` | ✅ EXISTS (top-level) |
| domain/workflows -> agent_framework | `service.py:44` | `from src.integrations.agent_framework.core.state_machine import ...` | ✅ EXISTS (top-level) |

**P6-P10: 5/5** — Bidirectional cycle confirmed. Mix of top-level and lazy imports. Cross-layer violation (domain -> integration).

---

## HIGH Severity (C3-C6): 16/16 pts

### C3: hybrid <-> infrastructure/storage (HIGH) — VERIFIED ✅

| Direction | File | Import Statement | Status |
|-----------|------|------------------|--------|
| hybrid -> storage | `orchestrator/bootstrap.py:162` | `from src.infrastructure.storage.task_store import TaskStore` | ✅ EXISTS |
| hybrid -> storage | `orchestrator/bootstrap.py:203` | `from src.infrastructure.storage.conversation_state import ...` | ✅ EXISTS |
| hybrid -> storage | `orchestrator/e2e_validator.py:128,134,140` | Multiple storage imports | ✅ EXISTS |
| hybrid -> storage | `orchestrator/mediator.py:92` | `from src.infrastructure.storage.conversation_state import ...` | ✅ EXISTS |
| storage -> hybrid | `storage_factories.py:233` | `from src.integrations.hybrid.switching.switcher import InMemoryCheckpointStorage` | ✅ EXISTS |
| storage -> hybrid | `storage_factories.py:243` | `from src.integrations.hybrid.switching.redis_checkpoint import ...` | ✅ EXISTS |

**P11-P15: 4/4** — Layer violation confirmed (infrastructure importing from integration).

### C4: ag_ui <-> swarm (HIGH) — VERIFIED ✅

| Direction | File | Import Statement | Status |
|-----------|------|------------------|--------|
| ag_ui -> swarm | `bridge.py:50` | `from src.integrations.swarm.events import SwarmEventEmitter` | ✅ EXISTS |
| ag_ui -> swarm | `bridge.py:227` | `from src.integrations.swarm.events import create_swarm_emitter` | ✅ EXISTS |
| swarm -> ag_ui | `events/emitter.py:28` | `from src.integrations.ag_ui.events import CustomEvent` | ✅ EXISTS (top-level) |

**P16-P20: 4/4** — Bidirectional cycle confirmed. Shared event type dependency.

### C5: agent_framework -> domain/workflows -> domain/checkpoints -> agent_framework (HIGH) — VERIFIED ✅

| Edge | File | Import Statement | Status |
|------|------|------------------|--------|
| agent_framework -> domain/workflows | (see C2 above) | Multiple files | ✅ EXISTS |
| domain/workflows -> domain/checkpoints | `resume_service.py:21` | `from src.domain.checkpoints import CheckpointService, ...` | ✅ EXISTS |
| domain/workflows -> domain/checkpoints | `executors/approval.py:23` | `from src.domain.checkpoints import CheckpointService, ...` | ✅ EXISTS |
| domain/checkpoints -> agent_framework | `service.py:36` | `from src.integrations.agent_framework.core.approval import ...` | ✅ EXISTS |
| domain/checkpoints -> agent_framework | `service.py:179` | `from src.integrations.agent_framework.core import ...` | ✅ EXISTS |
| domain/checkpoints -> agent_framework | `service.py:573` | `from src.integrations.agent_framework.core.approval import ...` | ✅ EXISTS |

**P21-P24: 4/4** — Three-node triangular cycle confirmed.

### C6: domain/agents -> agent_framework -> domain/workflows -> domain/agents (HIGH) — VERIFIED ✅

| Edge | File | Import Statement | Status |
|------|------|------------------|--------|
| domain/agents -> agent_framework | `service.py:24` | `from src.integrations.agent_framework.builders import ...` | ✅ EXISTS (top-level) |
| agent_framework -> domain/workflows | (see C2 above) | Multiple files | ✅ EXISTS |
| domain/workflows -> domain/agents | `service.py:19` | `from src.domain.agents.service import AgentConfig, AgentService, get_agent_service` | ✅ EXISTS (top-level) |

**P25-P28: 4/4** — Three-node triangular cycle confirmed through integration layer.

---

## MEDIUM Severity (C7-C11): 22/22 pts

### C7: hybrid -> infrastructure/storage -> ag_ui -> hybrid (MEDIUM) — VERIFIED ✅

| Edge | File | Import Statement | Status |
|------|------|------------------|--------|
| hybrid -> storage | (see C3) | Multiple files | ✅ EXISTS |
| storage -> ag_ui | `storage_factories.py:148` | `from src.integrations.ag_ui.thread.storage import InMemoryThreadRepository` | ✅ EXISTS |
| storage -> ag_ui | `storage_factories.py:158` | `from src.integrations.ag_ui.thread.redis_storage import RedisThreadRepository` | ✅ EXISTS |
| storage -> ag_ui | `storage_factories.py:173,183` | Cache backend imports | ✅ EXISTS |
| ag_ui -> hybrid | `converters.py:43-44` | `from src.integrations.hybrid.orchestrator_v2 import ...` | ✅ EXISTS |
| ag_ui -> hybrid | `bridge.py:48-49` | `from src.integrations.hybrid.orchestrator_v2 import ...` | ✅ EXISTS |
| ag_ui -> hybrid | `features/human_in_loop.py:33-34` | `from src.integrations.hybrid.risk import ...` | ✅ EXISTS |
| ag_ui -> hybrid | `features/generative_ui.py:33,41` | `from src.integrations.hybrid.switching.models import ...` | ✅ EXISTS |

**P29-P32: 4/4** — Three-module cycle via storage confirmed.

### C8: infrastructure/storage -> ag_ui -> orchestration -> infrastructure/storage (MEDIUM) — VERIFIED ✅

| Edge | File | Import Statement | Status |
|------|------|------------------|--------|
| storage -> ag_ui | (see C7) | `storage_factories.py` | ✅ EXISTS |
| ag_ui -> orchestration | `features/approval_delegate.py:39` | `from src.integrations.orchestration.hitl.unified_manager import ...` | ✅ EXISTS |
| orchestration -> storage | `hitl/unified_manager.py:36` | `from src.infrastructure.storage.approval_store import ...` | ✅ EXISTS |

**P33-P36: 4/4** — Three-module cycle confirmed.

### C9: hybrid -> infrastructure/storage -> ag_ui -> swarm -> hybrid (MEDIUM) — VERIFIED ✅

| Edge | Evidence | Status |
|------|----------|--------|
| hybrid -> storage | C3 evidence | ✅ EXISTS |
| storage -> ag_ui | C7 evidence | ✅ EXISTS |
| ag_ui -> swarm | C4 evidence (bridge.py) | ✅ EXISTS |
| swarm -> hybrid | `worker_executor.py:387`: `from src.integrations.hybrid.orchestrator.sse_events import SSEEventType` | ✅ EXISTS |

**P37-P40: 4/4** — Four-module long cycle confirmed.

### C10: agent_framework -> hybrid -> infrastructure/storage -> agent_framework (MEDIUM) — VERIFIED ✅

| Edge | Evidence | Status |
|------|----------|--------|
| agent_framework -> hybrid | C1 evidence | ✅ EXISTS |
| hybrid -> storage | C3 evidence | ✅ EXISTS |
| storage -> agent_framework | `storage_factories.py:318`: `from src.integrations.agent_framework.multiturn.checkpoint_storage import ...` | ✅ EXISTS |

**P41-P44: 4/4** — Three-module cycle via infrastructure confirmed.

### C11: agent_framework -> hybrid -> infrastructure/workers -> agent_framework (MEDIUM) — VERIFIED ✅

| Edge | Evidence | Status |
|------|----------|--------|
| agent_framework -> hybrid | C1 evidence | ✅ EXISTS |
| hybrid -> workers | `orchestrator/dispatch_handlers.py:442`: `from src.infrastructure.workers.arq_client import get_arq_client` | ✅ EXISTS |
| workers -> agent_framework | `task_functions.py:48`: `from src.integrations.agent_framework.builders.workflow_executor import ...` | ✅ EXISTS |

**P45-P48: 4/4** — Three-module cycle via workers confirmed.

---

## Summary (P49-P50): 2/2 pts

### P49: Are All Circular Dependencies Still Present?

**YES — All 11 circular dependencies are confirmed to still exist** as of 2026-03-31 on branch `feature/phase-42-deep-integration`. No cycles have been fixed in subsequent sprints. Most imports use lazy loading (inside functions/methods) which prevents runtime ImportError but does not eliminate the architectural coupling.

Notable observations:
- **C1, C3, C10, C11** use exclusively lazy imports — runtime-safe but architecturally problematic
- **C2** has top-level imports in BOTH directions — highest runtime risk
- **C4** has a top-level import on the swarm side (`emitter.py:28`) — partial runtime risk
- **C6** has top-level imports in all three edges — high runtime risk

### P50: Are the Recommended Fixes Feasible?

**YES — All 5 recommended fixes are architecturally sound and feasible:**

| Recommendation | Feasibility | Assessment |
|---------------|-------------|------------|
| 7.1 Decompose hybrid/ | **Feasible, HIGH effort** | Correct identification of God Module. Extracting risk/, context/, checkpoint/ is clean. 3-sprint estimate is realistic. |
| 7.2 Fix infrastructure layer violations | **Feasible, MEDIUM effort** | Moving factory resolution to DI/registry is the standard pattern. 2-sprint estimate is realistic. |
| 7.3 Introduce domain interface layer | **Feasible, MEDIUM effort** | Protocol-based abstractions with DI is the correct Python pattern. 2-sprint estimate is realistic. |
| 7.4 Unify event type system | **Feasible, LOW effort** | Creating shared `integrations/events/` is straightforward. 1-sprint estimate is realistic. |
| 7.5 Fix domain/files -> api/v1 | **Feasible, LOW effort** | Moving schemas from api to domain is a simple refactor. 1-sprint estimate is realistic. `domain/files/service.py:17` imports `from src.api.v1.files.schemas` — verified. |

**Overall roadmap assessment**: The 9-sprint total is realistic. The phased approach (A→E) correctly prioritizes quick wins (V14 fix) before structural changes (hybrid decomposition).

---

## Corrections to Document

**No factual errors found.** All 11 circular dependencies, their severity classifications, import chains, and the severity distribution table (CRITICAL: 2, HIGH: 4, MEDIUM: 5) are accurate. The recommendations section is well-reasoned and feasible.

**Minor observation**: The document correctly notes that `storage_factories.py` is the primary infrastructure-layer offender, acting as a service locator with 6 layer violations. This was confirmed by finding it imports from ag_ui, hybrid, agent_framework, mcp, and orchestration.

---

## Final Score: 50/50

| Category | Points | Score |
|----------|--------|-------|
| C1-C2 (CRITICAL) | 10 | 10/10 |
| C3-C6 (HIGH) | 16 | 16/16 |
| C7-C11 (MEDIUM) | 22 | 22/22 |
| P49: Still present? | 1 | 1/1 |
| P50: Fixes feasible? | 1 | 1/1 |
| **Total** | **50** | **50/50** |
