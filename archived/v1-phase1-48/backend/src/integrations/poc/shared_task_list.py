"""SharedTaskList — Central task pool for Agent Team collaboration.

Provides a shared state that Teammate Agents can interact with via tools:
- add_task: Team Lead adds tasks
- claim_task: Teammates self-assign pending tasks
- complete_task: Teammates report results
- get_status: View all task states
- add_message / get_messages: Inter-team communication log

Thread-safe for GroupChatBuilder (sequential rounds) but also safe
for ConcurrentBuilder (parallel execution) via simple locking.

V4 (Sprint 153): Added SharedTaskListProtocol and create_shared_task_list()
factory for Redis/in-memory backend selection.

PoC: Agent Team — poc/agent-team branch.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskItem:
    task_id: str
    description: str
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    claimed_by: str | None = None
    result: str | None = None
    claimed_at: float | None = None
    completed_at: float | None = None
    required_expertise: str = ""  # V2: keyword hints for task-agent matching
    retry_count: int = 0  # V4: number of times this task has been reassigned


@dataclass
class TeamMessage:
    from_agent: str
    content: str
    timestamp: float = field(default_factory=time.time)
    to_agent: str | None = None  # V2: None = broadcast, str = directed
    read_by: set[str] = field(default_factory=set)  # V2: unread tracking


class SharedTaskList:
    """Thread-safe shared task list for Agent Team collaboration.

    V2: Supports directed messaging (per-agent inboxes), unread tracking,
    required_expertise on tasks, and agent current-task lookup.

    Locking strategy (V2 parallel engine):
      - Uses threading.Lock (NOT asyncio.Lock) because MAF Agent.run()
        calls tools in ThreadPoolExecutor threads. threading.Lock is
        safe across both threads and the main asyncio event loop.
      - asyncio.Lock would NOT work here because tool functions run in
        real OS threads (via asyncio.to_thread), not coroutines.
    """

    def __init__(self):
        self._tasks: dict[str, TaskItem] = {}
        self._messages: list[TeamMessage] = []
        self._inboxes: dict[str, list[TeamMessage]] = {}  # V2: per-agent inbox
        self._lock = threading.Lock()
        self._last_progress_time: float = time.time()  # V2: no-progress detection

    def add_task(
        self, task_id: str, description: str, priority: int = 1,
        required_expertise: str = "",
    ) -> TaskItem:
        with self._lock:
            item = TaskItem(
                task_id=task_id, description=description,
                priority=priority, required_expertise=required_expertise,
            )
            self._tasks[task_id] = item
            return item

    def claim_task(self, agent_name: str) -> TaskItem | None:
        """Claim the highest-priority pending task."""
        with self._lock:
            pending = [
                t for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            ]
            if not pending:
                return None
            pending.sort(key=lambda t: t.priority)
            task = pending[0]
            task.status = TaskStatus.IN_PROGRESS
            task.claimed_by = agent_name
            task.claimed_at = time.time()
            return task

    def complete_task(self, task_id: str, result: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self._last_progress_time = time.time()  # V2: track progress
            return True

    def fail_task(self, task_id: str, error: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.FAILED
            task.result = f"FAILED: {error}"
            task.completed_at = time.time()
            self._last_progress_time = time.time()  # V2: track progress
            return True

    # ── V4: Error recovery (Sprint 157) ──

    def reassign_task(self, task_id: str) -> bool:
        """Reset a failed/in-progress task back to PENDING for reassignment.

        Increments retry_count. Returns False if task not found or max retries hit.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.claimed_by = None
            task.claimed_at = None
            task.result = None
            task.completed_at = None
            self._last_progress_time = time.time()
            return True

    def get_task_retry_count(self, task_id: str) -> int:
        """Get the number of times a task has been reassigned."""
        with self._lock:
            task = self._tasks.get(task_id)
            return task.retry_count if task else 0

    def add_message(
        self, from_agent: str, content: str, to_agent: str | None = None,
    ) -> None:
        """Add a team message. If to_agent is set, it's directed; otherwise broadcast."""
        with self._lock:
            msg = TeamMessage(
                from_agent=from_agent, content=content, to_agent=to_agent,
            )
            self._messages.append(msg)  # always in global log
            if to_agent:
                self._inboxes.setdefault(to_agent, []).append(msg)

    def get_status(self) -> str:
        with self._lock:
            if not self._tasks:
                return "No tasks in the list."
            lines = ["=== Task List Status ==="]
            for tid, t in self._tasks.items():
                claimed = f" (by: {t.claimed_by})" if t.claimed_by else ""
                result_preview = ""
                if t.result:
                    result_preview = f" -> {t.result[:80]}..."
                lines.append(f"[{t.status.value}] {tid}: {t.description}{claimed}{result_preview}")

            done = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
            total = len(self._tasks)
            lines.append(f"\nProgress: {done}/{total} completed")
            return "\n".join(lines)

    def get_messages(self, last_n: int = 10) -> str:
        with self._lock:
            if not self._messages:
                return "No team messages yet."
            recent = self._messages[-last_n:]
            lines = ["=== Recent Team Messages ==="]
            for msg in recent:
                lines.append(f"[{msg.from_agent}]: {msg.content}")
            return "\n".join(lines)

    def is_all_done(self) -> bool:
        with self._lock:
            if not self._tasks:
                return False
            return all(
                t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                for t in self._tasks.values()
            )

    # ── V2: Directed inbox + parallel support ──

    def get_inbox(self, agent_name: str, last_n: int = 10, unread_only: bool = False) -> str:
        """Get messages directed TO this agent. Marks them as read."""
        with self._lock:
            msgs = self._inboxes.get(agent_name, [])
            if unread_only:
                msgs = [m for m in msgs if agent_name not in m.read_by]
            msgs = msgs[-last_n:]
            for m in msgs:
                m.read_by.add(agent_name)
            if not msgs:
                return ""
            lines = [f"=== Messages for {agent_name} ==="]
            for m in msgs:
                lines.append(f"[{m.from_agent} → you]: {m.content}")
            return "\n".join(lines)

    def get_inbox_count(self, agent_name: str, unread_only: bool = False) -> int:
        """Count messages in an agent's inbox."""
        with self._lock:
            msgs = self._inboxes.get(agent_name, [])
            if unread_only:
                return sum(1 for m in msgs if agent_name not in m.read_by)
            return len(msgs)

    def get_agent_current_task(self, agent_name: str) -> TaskItem | None:
        """Get the IN_PROGRESS task claimed by this agent, if any."""
        with self._lock:
            for t in self._tasks.values():
                if t.claimed_by == agent_name and t.status == TaskStatus.IN_PROGRESS:
                    return t
            return None

    def seconds_since_last_progress(self) -> float:
        """Seconds since any task was completed/failed. For no-progress detection."""
        with self._lock:
            return time.time() - self._last_progress_time

    def task_count(self) -> int:
        """Return total number of tasks."""
        with self._lock:
            return len(self._tasks)

    def completed_count(self) -> int:
        """Return number of completed tasks."""
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)

    def message_count(self) -> int:
        """Return total number of messages."""
        with self._lock:
            return len(self._messages)

    def get_messages_since(self, offset: int) -> list[TeamMessage]:
        """Return messages added since offset index (for SSE emission)."""
        with self._lock:
            return list(self._messages[offset:])

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "description": t.description,
                        "priority": t.priority,
                        "status": t.status.value,
                        "claimed_by": t.claimed_by,
                        "result": t.result[:200] if t.result else None,
                    }
                    for t in self._tasks.values()
                ],
                "messages": [
                    {
                        "from": m.from_agent,
                        "to": m.to_agent,
                        "content": m.content,
                        "directed": m.to_agent is not None,
                    }
                    for m in self._messages
                ],
                "progress": {
                    "total": len(self._tasks),
                    "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
                    "in_progress": sum(1 for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS),
                    "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
                },
            }


# ---------------------------------------------------------------------------
# V4: Protocol + Factory (Sprint 153)
# ---------------------------------------------------------------------------

@runtime_checkable
class SharedTaskListProtocol(Protocol):
    """Protocol defining the SharedTaskList interface.

    Both SharedTaskList (in-memory) and RedisSharedTaskList implement this.
    """

    def add_task(self, task_id: str, description: str, priority: int = 1,
                 required_expertise: str = "") -> TaskItem: ...
    def claim_task(self, agent_name: str) -> Optional[TaskItem]: ...
    def complete_task(self, task_id: str, result: str) -> bool: ...
    def fail_task(self, task_id: str, error: str) -> bool: ...
    def add_message(self, from_agent: str, content: str,
                    to_agent: Optional[str] = None) -> None: ...
    def get_status(self) -> str: ...
    def get_messages(self, last_n: int = 10) -> str: ...
    def is_all_done(self) -> bool: ...
    def get_inbox(self, agent_name: str, last_n: int = 10,
                  unread_only: bool = False) -> str: ...
    def get_inbox_count(self, agent_name: str, unread_only: bool = False) -> int: ...
    def get_agent_current_task(self, agent_name: str) -> Optional[TaskItem]: ...
    def seconds_since_last_progress(self) -> float: ...
    def task_count(self) -> int: ...
    def completed_count(self) -> int: ...
    def message_count(self) -> int: ...
    def get_messages_since(self, offset: int) -> list[TeamMessage]: ...
    def reassign_task(self, task_id: str) -> bool: ...
    def get_task_retry_count(self, task_id: str) -> int: ...
    def to_dict(self) -> dict[str, Any]: ...


def create_shared_task_list(
    session_id: str = "",
    use_redis: bool = True,
) -> SharedTaskListProtocol:
    """Factory: returns RedisSharedTaskList if Redis available, else in-memory.

    Args:
        session_id: Unique session identifier for Redis key prefix.
        use_redis: Whether to attempt Redis backend. Falls back on failure.

    Returns:
        A SharedTaskListProtocol implementation.
    """
    if use_redis and session_id:
        try:
            import redis as redis_lib
            from src.core.config import get_settings

            settings = get_settings()
            if settings.redis_host:
                client = redis_lib.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=getattr(settings, "redis_password", None) or None,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=5,
                )
                client.ping()  # verify connectivity
                from src.integrations.poc.redis_task_list import RedisSharedTaskList
                logger.info(
                    f"Using RedisSharedTaskList for session {session_id} "
                    f"({settings.redis_host}:{settings.redis_port})"
                )
                return RedisSharedTaskList(session_id, client)
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-memory: {e}")

    logger.info("Using in-memory SharedTaskList")
    return SharedTaskList()
