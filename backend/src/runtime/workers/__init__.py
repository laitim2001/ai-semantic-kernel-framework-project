"""runtime.workers — agent loop workers + queue backends.

Single-source map:
- AgentLoopWorker: agent_loop_worker.py (framework owner)
- QueueBackend ABC: queue_backend.py
- MockQueueBackend: queue_backend.py (test double)
"""

from runtime.workers.agent_loop_worker import (
    AgentLoopWorker,
    SseEmit,
    TaskHandler,
    WorkerConfig,
    build_agent_loop_handler,
    execute_loop_with_sse,
)
from runtime.workers.queue_backend import (
    MockQueueBackend,
    QueueBackend,
    TaskEnvelope,
    TaskResult,
    TaskStatus,
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
