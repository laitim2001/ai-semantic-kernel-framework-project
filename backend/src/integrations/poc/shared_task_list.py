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


@dataclass
class TeamMessage:
    from_agent: str
    content: str
    timestamp: float = field(default_factory=time.time)


class SharedTaskList:
    """Thread-safe shared task list for Agent Team collaboration."""

    def __init__(self):
        self._tasks: dict[str, TaskItem] = {}
        self._messages: list[TeamMessage] = []
        self._lock = threading.Lock()

    def add_task(self, task_id: str, description: str, priority: int = 1) -> TaskItem:
        with self._lock:
            item = TaskItem(task_id=task_id, description=description, priority=priority)
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
            return True

    def fail_task(self, task_id: str, error: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            task.status = TaskStatus.FAILED
            task.result = f"FAILED: {error}"
            task.completed_at = time.time()
            return True

    def add_message(self, from_agent: str, content: str) -> None:
        with self._lock:
            self._messages.append(TeamMessage(from_agent=from_agent, content=content))

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
                    {"from": m.from_agent, "content": m.content}
                    for m in self._messages
                ],
                "progress": {
                    "total": len(self._tasks),
                    "completed": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
                    "in_progress": sum(1 for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS),
                    "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
                },
            }
