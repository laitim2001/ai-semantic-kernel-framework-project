"""runtime.workers — agent loop workers + queue backends.

Single-source map:
- AgentLoopWorker: agent_loop_worker.py (framework owner)
- QueueBackend ABC: queue_backend.py
- MockQueueBackend: queue_backend.py (test double)
"""

from runtime.workers.agent_loop_worker import AgentLoopWorker, TaskHandler, WorkerConfig
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
    "TaskEnvelope",
    "TaskHandler",
    "TaskResult",
    "TaskStatus",
    "WorkerConfig",
]
