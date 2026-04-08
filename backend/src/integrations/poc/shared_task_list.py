"""SharedTaskList — Central task pool for Agent Team collaboration.

Provides a shared state that Teammate Agents can interact with via tools:
- add_task: Team Lead adds tasks
- claim_task: Teammates self-assign pending tasks
- complete_task: Teammates report results
- get_status: View all task states
- add_message / get_messages: Inter-team communication log

Thread-safe for GroupChatBuilder (sequential rounds) but also safe
for ConcurrentBuilder (parallel execution) via simple locking.

PoC: Agent Team — poc/agent-team branch.
"""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    Threading.Lock retained for GroupChat backward compat; async callers
    can safely use these from coroutines (single-thread asyncio).
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
