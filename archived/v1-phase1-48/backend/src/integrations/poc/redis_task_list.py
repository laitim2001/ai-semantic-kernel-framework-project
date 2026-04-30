"""RedisSharedTaskList — Redis-backed drop-in replacement for SharedTaskList.

Persists tasks, messages, and directed inboxes in Redis for crash-safe
inter-agent communication.  Matches CC's file-based mailbox semantics
(append-only, ordered, survives process restart).

Redis structures (all keys prefixed ``ipa:team:{session_id}:``):
  - tasks       → Hash  (field=task_id, value=JSON)
  - messages    → Stream (global broadcast log)
  - inbox:{name}→ Stream (per-agent directed inbox)
  - last_progress → String (unix timestamp)

Sync Redis client is used because MAF Agent.run() invokes tools inside
OS threads (asyncio.to_thread / ThreadPoolExecutor).  asyncio-based
Redis would deadlock in that context.

PoC: Agent Team V4 — Sprint 153.
"""

import json
import logging
import threading
import time
from typing import Any, Optional

import redis

from src.integrations.poc.shared_task_list import TaskItem, TaskStatus, TeamMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_to_json(task: TaskItem) -> str:
    """Serialize a TaskItem to JSON string for Redis storage."""
    return json.dumps({
        "task_id": task.task_id,
        "description": task.description,
        "priority": task.priority,
        "status": task.status.value,
        "claimed_by": task.claimed_by,
        "result": task.result,
        "claimed_at": task.claimed_at,
        "completed_at": task.completed_at,
        "required_expertise": task.required_expertise,
        "retry_count": task.retry_count,
    })


def _json_to_task(data: str) -> TaskItem:
    """Deserialize a TaskItem from JSON string."""
    d = json.loads(data)
    return TaskItem(
        task_id=d["task_id"],
        description=d["description"],
        priority=d.get("priority", 1),
        status=TaskStatus(d["status"]),
        claimed_by=d.get("claimed_by"),
        result=d.get("result"),
        claimed_at=d.get("claimed_at"),
        completed_at=d.get("completed_at"),
        required_expertise=d.get("required_expertise", ""),
        retry_count=d.get("retry_count", 0),
    )


def _msg_to_fields(msg: TeamMessage) -> dict:
    """Convert a TeamMessage to Redis Stream fields."""
    return {
        "from_agent": msg.from_agent,
        "content": msg.content,
        "to_agent": msg.to_agent or "",
        "timestamp": str(msg.timestamp),
    }


def _fields_to_msg(fields: dict) -> TeamMessage:
    """Convert Redis Stream fields back to a TeamMessage."""
    return TeamMessage(
        from_agent=fields.get("from_agent", "?"),
        content=fields.get("content", ""),
        to_agent=fields.get("to_agent") or None,
        timestamp=float(fields.get("timestamp", time.time())),
    )


# ---------------------------------------------------------------------------
# Key prefix
# ---------------------------------------------------------------------------

_KEY_TTL = 3600  # 1 hour


def _key(session_id: str, suffix: str) -> str:
    return f"ipa:team:{session_id}:{suffix}"


# ---------------------------------------------------------------------------
# RedisSharedTaskList
# ---------------------------------------------------------------------------

class RedisSharedTaskList:
    """Thread-safe, Redis-backed shared task list.

    Drop-in replacement for ``SharedTaskList`` with identical public API.
    Uses sync ``redis.Redis`` because tool functions execute in OS threads.
    """

    def __init__(self, session_id: str, redis_client: "redis.Redis"):
        self._sid = session_id
        self._r: redis.Redis = redis_client
        self._lock = threading.Lock()
        # Per-agent cursor for XRANGE-based unread tracking
        self._inbox_cursors: dict[str, str] = {}  # agent_name → last_read stream_id

    # ── Task operations ──────────────────────────────────────────────────

    def add_task(
        self,
        task_id: str,
        description: str,
        priority: int = 1,
        required_expertise: str = "",
    ) -> TaskItem:
        item = TaskItem(
            task_id=task_id,
            description=description,
            priority=priority,
            required_expertise=required_expertise,
        )
        with self._lock:
            key = _key(self._sid, "tasks")
            self._r.hset(key, task_id, _task_to_json(item))
            self._r.expire(key, _KEY_TTL)
        return item

    def claim_task(self, agent_name: str) -> Optional[TaskItem]:
        """Claim the highest-priority PENDING task (atomic via lock)."""
        with self._lock:
            key = _key(self._sid, "tasks")
            all_raw = self._r.hgetall(key)
            pending = []
            for raw in all_raw.values():
                t = _json_to_task(raw)
                if t.status == TaskStatus.PENDING:
                    pending.append(t)
            if not pending:
                return None
            pending.sort(key=lambda t: t.priority)
            task = pending[0]
            task.status = TaskStatus.IN_PROGRESS
            task.claimed_by = agent_name
            task.claimed_at = time.time()
            self._r.hset(key, task.task_id, _task_to_json(task))
            return task

    def complete_task(self, task_id: str, result: str) -> bool:
        with self._lock:
            key = _key(self._sid, "tasks")
            raw = self._r.hget(key, task_id)
            if not raw:
                return False
            task = _json_to_task(raw)
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self._r.hset(key, task_id, _task_to_json(task))
            # Update progress timestamp
            self._r.set(_key(self._sid, "last_progress"), str(time.time()))
            self._r.expire(_key(self._sid, "last_progress"), _KEY_TTL)
            return True

    def fail_task(self, task_id: str, error: str) -> bool:
        with self._lock:
            key = _key(self._sid, "tasks")
            raw = self._r.hget(key, task_id)
            if not raw:
                return False
            task = _json_to_task(raw)
            task.status = TaskStatus.FAILED
            task.result = f"FAILED: {error}"
            task.completed_at = time.time()
            self._r.hset(key, task_id, _task_to_json(task))
            self._r.set(_key(self._sid, "last_progress"), str(time.time()))
            self._r.expire(_key(self._sid, "last_progress"), _KEY_TTL)
            return True

    def reassign_task(self, task_id: str) -> bool:
        """Reset task to PENDING for reassignment. Increments retry_count."""
        with self._lock:
            key = _key(self._sid, "tasks")
            raw = self._r.hget(key, task_id)
            if not raw:
                return False
            task = _json_to_task(raw)
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.claimed_by = None
            task.claimed_at = None
            task.result = None
            task.completed_at = None
            self._r.hset(key, task_id, _task_to_json(task))
            self._r.set(_key(self._sid, "last_progress"), str(time.time()))
            self._r.expire(_key(self._sid, "last_progress"), _KEY_TTL)
            return True

    def get_task_retry_count(self, task_id: str) -> int:
        with self._lock:
            key = _key(self._sid, "tasks")
            raw = self._r.hget(key, task_id)
            if not raw:
                return 0
            task = _json_to_task(raw)
            return task.retry_count

    # ── Message operations ───────────────────────────────────────────────

    def add_message(
        self,
        from_agent: str,
        content: str,
        to_agent: Optional[str] = None,
    ) -> None:
        """Add message to global stream + directed inbox if to_agent set."""
        msg = TeamMessage(
            from_agent=from_agent,
            content=content,
            to_agent=to_agent,
        )
        fields = _msg_to_fields(msg)
        with self._lock:
            # Global message stream
            gkey = _key(self._sid, "messages")
            self._r.xadd(gkey, fields)
            self._r.expire(gkey, _KEY_TTL)
            # Directed inbox
            if to_agent:
                ikey = _key(self._sid, f"inbox:{to_agent}")
                self._r.xadd(ikey, fields)
                self._r.expire(ikey, _KEY_TTL)

    def get_status(self) -> str:
        with self._lock:
            tasks = self._get_all_tasks_locked()
        if not tasks:
            return "No tasks in the list."
        lines = ["=== Task List Status ==="]
        for t in tasks.values():
            claimed = f" (by: {t.claimed_by})" if t.claimed_by else ""
            result_preview = ""
            if t.result:
                result_preview = f" -> {t.result[:80]}..."
            lines.append(
                f"[{t.status.value}] {t.task_id}: {t.description}{claimed}{result_preview}"
            )
        done = sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED)
        lines.append(f"\nProgress: {done}/{len(tasks)} completed")
        return "\n".join(lines)

    def get_messages(self, last_n: int = 10) -> str:
        with self._lock:
            gkey = _key(self._sid, "messages")
            entries = self._r.xrevrange(gkey, count=last_n)
        if not entries:
            return "No team messages yet."
        lines = ["=== Recent Team Messages ==="]
        for _stream_id, fields in reversed(entries):
            msg = _fields_to_msg(fields)
            lines.append(f"[{msg.from_agent}]: {msg.content}")
        return "\n".join(lines)

    def is_all_done(self) -> bool:
        with self._lock:
            tasks = self._get_all_tasks_locked()
        if not tasks:
            return False
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in tasks.values()
        )

    # ── V2: Directed inbox + parallel support ────────────────────────────

    def get_inbox(
        self,
        agent_name: str,
        last_n: int = 10,
        unread_only: bool = False,
    ) -> str:
        """Get messages directed TO this agent. Advances cursor for unread."""
        with self._lock:
            ikey = _key(self._sid, f"inbox:{agent_name}")
            if unread_only:
                cursor = self._inbox_cursors.get(agent_name, "0-0")
                entries = self._r.xrange(ikey, min=f"({cursor}", count=last_n)
            else:
                entries = self._r.xrevrange(ikey, count=last_n)
                entries = list(reversed(entries))

            if not entries:
                return ""

            # Advance cursor to latest read
            if unread_only and entries:
                self._inbox_cursors[agent_name] = entries[-1][0]

            lines = [f"=== Messages for {agent_name} ==="]
            for _sid, fields in entries:
                msg = _fields_to_msg(fields)
                lines.append(f"[{msg.from_agent} → you]: {msg.content}")
            return "\n".join(lines)

    def get_inbox_count(
        self,
        agent_name: str,
        unread_only: bool = False,
    ) -> int:
        """Count messages in an agent's inbox."""
        with self._lock:
            ikey = _key(self._sid, f"inbox:{agent_name}")
            if not unread_only:
                try:
                    return self._r.xlen(ikey)
                except Exception:
                    return 0
            # Unread = entries after cursor
            cursor = self._inbox_cursors.get(agent_name, "0-0")
            entries = self._r.xrange(ikey, min=f"({cursor}")
            return len(entries)

    def get_agent_current_task(self, agent_name: str) -> Optional[TaskItem]:
        """Get the IN_PROGRESS task claimed by this agent."""
        with self._lock:
            tasks = self._get_all_tasks_locked()
        for t in tasks.values():
            if t.claimed_by == agent_name and t.status == TaskStatus.IN_PROGRESS:
                return t
        return None

    def seconds_since_last_progress(self) -> float:
        """Seconds since any task was completed/failed."""
        with self._lock:
            raw = self._r.get(_key(self._sid, "last_progress"))
        if raw:
            return time.time() - float(raw)
        return 0.0  # No progress recorded yet — treat as fresh

    def task_count(self) -> int:
        """Return total number of tasks."""
        with self._lock:
            return self._r.hlen(_key(self._sid, "tasks"))

    def completed_count(self) -> int:
        """Return number of completed tasks."""
        with self._lock:
            tasks = self._get_all_tasks_locked()
        return sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED)

    def message_count(self) -> int:
        """Return total number of messages in the global stream."""
        with self._lock:
            try:
                return self._r.xlen(_key(self._sid, "messages"))
            except Exception:
                return 0

    def get_messages_since(self, offset: int) -> list:
        """Return messages added since offset (approximation via stream index).

        For Redis, offset is mapped to stream entries. Returns TeamMessage-like
        objects with from_agent, content, to_agent attributes.
        """
        with self._lock:
            gkey = _key(self._sid, "messages")
            all_entries = self._r.xrange(gkey)
            if offset >= len(all_entries):
                return []
            new_entries = all_entries[offset:]
            return [_fields_to_msg(fields) for _sid, fields in new_entries]

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            tasks = self._get_all_tasks_locked()
            gkey = _key(self._sid, "messages")
            msg_entries = self._r.xrange(gkey) or []

        task_list = []
        for t in tasks.values():
            task_list.append({
                "task_id": t.task_id,
                "description": t.description,
                "priority": t.priority,
                "status": t.status.value,
                "claimed_by": t.claimed_by,
                "result": t.result[:200] if t.result else None,
            })

        messages = []
        for _sid, fields in msg_entries:
            msg = _fields_to_msg(fields)
            messages.append({
                "from": msg.from_agent,
                "to": msg.to_agent,
                "content": msg.content,
                "directed": msg.to_agent is not None,
            })

        completed = sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for t in tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in tasks.values() if t.status == TaskStatus.PENDING)

        return {
            "tasks": task_list,
            "messages": messages,
            "progress": {
                "total": len(tasks),
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending,
            },
        }

    # ── Cleanup ──────────────────────────────────────────────────────────

    def cleanup(self) -> int:
        """Delete all Redis keys for this session. Returns number of keys deleted."""
        pattern = _key(self._sid, "*")
        keys = self._r.keys(pattern)
        if keys:
            return self._r.delete(*keys)
        return 0

    # ── Internal helpers ─────────────────────────────────────────────────

    def _get_all_tasks_locked(self) -> dict[str, TaskItem]:
        """Get all tasks from Redis Hash. Caller must hold self._lock."""
        key = _key(self._sid, "tasks")
        all_raw = self._r.hgetall(key)
        return {tid: _json_to_task(raw) for tid, raw in all_raw.items()}
