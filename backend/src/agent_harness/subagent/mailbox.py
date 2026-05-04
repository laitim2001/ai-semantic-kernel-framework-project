"""
File: backend/src/agent_harness/subagent/mailbox.py
Purpose: MailboxStore — in-memory per-session pub/sub for Teammate-mode communication.
Category: 範疇 11 (Subagent Orchestration)
Scope: Sprint 54.2 US-3

Description:
    Teammate mode (per CC peer-pane pattern) needs a way for a subagent to
    send messages to its parent (or peer subagent) without sharing context
    (unlike Fork). This implementation uses in-memory asyncio.Queue per
    (session_id, recipient) pair.

    Per-request DI (NOT module-level singleton; AD-Test-1 53.6 lesson):
    AgentLoop creates a fresh MailboxStore per request. No state survives
    across requests.

    Cross-session isolation: each session_id has its own queue dict;
    message in session A is invisible to session B.

    Boundedness: queues are unbounded by default. Phase 55+ may add per-queue
    maxsize / TTL eviction if memory pressure becomes a concern.

    Receive timeout: caller-provided; default 5s. On timeout returns None
    (NOT raises) so caller can retry / give up cleanly.

Created: 2026-05-04 (Sprint 54.2)

Modification History:
    - 2026-05-04: Initial creation (Sprint 54.2 US-3)

Related:
    - subagent/modes/teammate.py — TeammateExecutor consumer
    - 01-eleven-categories-spec.md §範疇 11
    - feedback_kb_worktree_no_easy_merge.md — irrelevant; this is in-memory only
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import UUID

from agent_harness._contracts import Message


class MailboxStore:
    """In-memory per-session pub/sub for Teammate-mode subagent communication.

    Per AD-Test-1 (53.6): instantiate per-request; do NOT cache module-level.
    Each instance owns its own asyncio queues; no cross-instance leak.
    """

    def __init__(self) -> None:
        # session_id → recipient → asyncio.Queue[Message]
        self._queues: dict[UUID, dict[str, asyncio.Queue[Message]]] = defaultdict(dict)

    def _queue_for(self, session_id: UUID, recipient: str) -> asyncio.Queue[Message]:
        """Lazily create the queue for (session_id, recipient)."""
        return self._queues[session_id].setdefault(recipient, asyncio.Queue())

    async def send(
        self,
        session_id: UUID,
        sender: str,
        recipient: str,
        content: str,
    ) -> None:
        """Put a Message into the recipient's queue.

        The message role is "user" by convention so that the recipient's LLM
        sees it as input. Sender annotation is prepended into content.
        """
        msg = Message(role="user", content=f"[from {sender}] {content}")
        await self._queue_for(session_id, recipient).put(msg)

    async def receive(
        self,
        session_id: UUID,
        recipient: str,
        timeout_s: float = 5.0,
    ) -> Message | None:
        """Block until a message for `recipient` arrives or timeout elapses.

        Returns None on timeout (not raises) — callers expect optional polling.
        """
        try:
            return await asyncio.wait_for(
                self._queue_for(session_id, recipient).get(), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            return None

    def clear(self, session_id: UUID) -> None:
        """Drop all queues for a session (call at session close)."""
        self._queues.pop(session_id, None)

    def session_count(self) -> int:
        """Number of active sessions (for diagnostics / metrics)."""
        return len(self._queues)
