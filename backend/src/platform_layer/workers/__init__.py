"""platform_layer.workers — re-export shim pointing to runtime.workers.

Sprint 52.5 Day 10 P1 #7 (W2-2 audit) consolidates the two parallel
worker module locations:

- ``runtime.workers``   — actual home (since 49.4); contains
  AgentLoopWorker / QueueBackend / MockQueueBackend implementations
  + tests; this is where production code currently imports from.
- ``platform_layer.workers`` — V2 spec category-boundaries.md home,
  but pre-52.5 was an empty namespace doc-only package.

Rather than physically move the source files (which would require
updating ~6 test files + the git history would obscure 49.4 origin),
this module re-exports everything from ``runtime.workers``. Both
import paths therefore resolve to the same objects:

    from runtime.workers import AgentLoopWorker          # legacy
    from platform_layer.workers import AgentLoopWorker   # spec-aligned

Future direction: Phase 53.1 lands TemporalQueueBackend; that's the
natural moment to physically move the source under platform_layer/
and turn this shim around (runtime.workers re-exports from
platform_layer.workers, then deprecate). The shim direction is
deliberately reversible.

Per Phase 49.4 worker-queue-decision: Temporal won over Celery.
"""

from runtime.workers import (
    AgentLoopWorker,
    MockQueueBackend,
    QueueBackend,
    SseEmit,
    TaskEnvelope,
    TaskHandler,
    TaskResult,
    TaskStatus,
    WorkerConfig,
    build_agent_loop_handler,
    execute_loop_with_sse,
)

__all__ = [
    "AgentLoopWorker",
    "MockQueueBackend",
    "QueueBackend",
    "SseEmit",
    "TaskEnvelope",
    "TaskHandler",
    "TaskResult",
    "TaskStatus",
    "WorkerConfig",
    "build_agent_loop_handler",
    "execute_loop_with_sse",
]
