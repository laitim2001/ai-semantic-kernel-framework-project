"""Approval Gate — Event-driven HITL checkpoint for agent team tool calls.

CC-equivalent design: Agent awaits an asyncio.Event (= CC's Promise),
which is resolved by the API endpoint when the user clicks Approve/Reject.
Zero CPU wait, zero event loop contention — single uvicorn worker sufficient.

CC architecture mapping:
  CC new Promise()         → asyncio.Event()
  CC await permissionDecision → await event.wait()
  CC resolve(decision)     → event.set()
  CC claim() guard         → asyncio.Lock + is_set() check

Risk classification is a simple tool-name whitelist (PoC-level).

PoC: Agent Team V4 — Sprint 154 (rewritten from polling to event-driven).
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Risk classification (PoC — tool-name whitelist)
# ---------------------------------------------------------------------------

class ToolRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


HIGH_RISK_TOOLS: set[str] = {
    "run_diagnostic_command",
    "query_database",
}

MEDIUM_RISK_TOOLS: set[str] = {
    "search_knowledge_base",
}


def assess_tool_risk(tool_name: str) -> ToolRiskLevel:
    """Classify a tool call's risk level by name."""
    if tool_name in HIGH_RISK_TOOLS:
        return ToolRiskLevel.HIGH
    if tool_name in MEDIUM_RISK_TOOLS:
        return ToolRiskLevel.MEDIUM
    return ToolRiskLevel.LOW


def requires_approval(tool_name: str) -> bool:
    """Return True if this tool requires human approval before execution."""
    return assess_tool_risk(tool_name) == ToolRiskLevel.HIGH


# ---------------------------------------------------------------------------
# PendingApproval — one per approval request
# ---------------------------------------------------------------------------

@dataclass
class PendingApproval:
    """A pending approval request with an asyncio.Event for zero-CPU wait.

    Equivalent to CC's PermissionDecision Promise.
    """
    approval_id: str
    agent_name: str
    tool_name: str
    tool_args: dict[str, Any]
    session_id: str
    event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: Optional[str] = None  # "approved" | "rejected" | None
    decided_by: str = ""
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# TeamApprovalManager — event-driven, CC PermissionDecision equivalent
# ---------------------------------------------------------------------------

class TeamApprovalManager:
    """Event-driven approval manager for agent team HITL.

    CC equivalent: PermissionDecision + claim() guard + resolve().

    Agent side:  await manager.wait_for_decision(id) → zero CPU wait
    API side:    await manager.resolve(id, "approved") → agent resumes instantly

    Single uvicorn worker sufficient — asyncio.Event.wait() yields to
    the event loop, allowing SSE streams and API requests to proceed.
    """

    def __init__(self):
        self._pending: dict[str, PendingApproval] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        approval_id: str,
        agent_name: str,
        tool_name: str,
        tool_args: dict[str, Any],
        session_id: str,
    ) -> PendingApproval:
        """Register a new pending approval with an asyncio.Event."""
        async with self._lock:
            pending = PendingApproval(
                approval_id=approval_id,
                agent_name=agent_name,
                tool_name=tool_name,
                tool_args=tool_args,
                session_id=session_id,
            )
            self._pending[approval_id] = pending
            logger.info(
                f"Approval registered: {approval_id} "
                f"(agent={agent_name}, tool={tool_name})"
            )
            return pending

    async def wait_for_decision(
        self,
        approval_id: str,
        timeout: float = 300.0,
    ) -> str:
        """Wait for human decision — zero CPU, yields to event loop.

        Equivalent to CC's ``await permissionDecision``.
        The agent coroutine suspends here, allowing the event loop to
        freely process other agents, SSE events, and API requests.

        Returns: "approved", "rejected", or "expired".
        """
        pending = self._pending.get(approval_id)
        if not pending:
            return "expired"

        try:
            await asyncio.wait_for(pending.event.wait(), timeout=timeout)
            return pending.decision or "expired"
        except asyncio.TimeoutError:
            logger.warning(f"Approval {approval_id} timed out after {timeout}s")
            return "expired"
        finally:
            # Cleanup after resolution or timeout
            async with self._lock:
                self._pending.pop(approval_id, None)

    async def resolve(
        self,
        approval_id: str,
        decision: str,
        decided_by: str = "",
    ) -> bool:
        """Resolve a pending approval — agent wakes immediately.

        Equivalent to CC's ``resolve(decision)`` with atomic claim() guard.
        Only the first resolve() call takes effect; subsequent calls return False.

        Returns: True if resolved, False if already resolved or not found.
        """
        async with self._lock:
            pending = self._pending.get(approval_id)
            if not pending:
                logger.warning(f"Approval {approval_id} not found")
                return False
            if pending.event.is_set():
                logger.warning(f"Approval {approval_id} already resolved")
                return False  # CC claim() guard — only first resolver wins

            pending.decision = decision
            pending.decided_by = decided_by
            pending.event.set()  # Agent wakes up immediately!

            logger.info(
                f"Approval {approval_id} resolved: {decision} by {decided_by}"
            )
            return True

    async def list_pending(self) -> list[dict[str, Any]]:
        """List all pending (unresolved) approvals."""
        async with self._lock:
            return [
                {
                    "approval_id": p.approval_id,
                    "agent_name": p.agent_name,
                    "tool_name": p.tool_name,
                    "session_id": p.session_id,
                    "waiting_seconds": round(time.time() - p.created_at, 1),
                }
                for p in self._pending.values()
                if not p.event.is_set()
            ]

    def clear(self) -> None:
        """Clear all pending approvals (called on team execution end)."""
        for p in self._pending.values():
            if not p.event.is_set():
                p.decision = "expired"
                p.event.set()
        self._pending.clear()
        self._tool_approvals.clear()

    # ── Per-tool-call permission (CC 9-step cascade equivalent) ──

    _tool_approvals: dict[str, set[str]] = {}  # tool_name → {approved agent names}

    def approve_tool_for_agent(self, agent_name: str, tool_name: str) -> None:
        """Mark a tool as approved for a specific agent (after user approves)."""
        self._tool_approvals.setdefault(tool_name, set()).add(agent_name)

    def is_tool_approved(self, agent_name: str, tool_name: str) -> bool:
        """Check if an agent has approval to use a specific tool."""
        return agent_name in self._tool_approvals.get(tool_name, set())


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: Optional[TeamApprovalManager] = None


def get_approval_manager() -> Optional[TeamApprovalManager]:
    """Get the active TeamApprovalManager (shared between work loop + API)."""
    return _manager


def create_approval_manager() -> TeamApprovalManager:
    """Create and register a new TeamApprovalManager for a team execution."""
    global _manager
    # Clear previous manager if exists
    if _manager:
        _manager.clear()
    _manager = TeamApprovalManager()
    return _manager


# ---------------------------------------------------------------------------
# Convenience: request + await (used by agent work loop)
# ---------------------------------------------------------------------------

async def request_and_await_approval(
    agent_name: str,
    tool_name: str,
    tool_args: dict[str, Any],
    session_id: str,
    emitter,
    manager: TeamApprovalManager,
    timeout_seconds: float = 300.0,
) -> str:
    """Request approval and await decision — event-driven, zero CPU.

    1. Emit APPROVAL_REQUIRED SSE event
    2. Register with TeamApprovalManager (creates asyncio.Event)
    3. await event.wait() — yields to event loop, zero CPU
    4. API endpoint calls manager.resolve() → agent resumes instantly

    Returns: "approved", "rejected", or "expired".
    """
    approval_id = str(uuid.uuid4())

    # 1. Emit APPROVAL_REQUIRED SSE event
    if emitter and hasattr(emitter, "emit_event"):
        await emitter.emit_event("APPROVAL_REQUIRED", {
            "approval_id": approval_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "arguments": _safe_args(tool_args),
            "risk_level": "high",
            "session_id": session_id,
            "message": (
                f"Agent '{agent_name}' wants to execute '{tool_name}'. "
                f"Approve or reject?"
            ),
        })

    # 2. Register with manager (creates asyncio.Event)
    await manager.register(
        approval_id=approval_id,
        agent_name=agent_name,
        tool_name=tool_name,
        tool_args=_safe_args(tool_args),
        session_id=session_id,
    )

    logger.info(
        f"Agent {agent_name}: awaiting approval for '{tool_name}' "
        f"(id={approval_id}, timeout={timeout_seconds}s)"
    )

    # 3. Wait — zero CPU, event loop free for SSE + API
    decision = await manager.wait_for_decision(approval_id, timeout=timeout_seconds)

    logger.info(f"Agent {agent_name}: tool '{tool_name}' → {decision}")
    return decision


# ---------------------------------------------------------------------------
# Per-tool-call permission check (called from tool functions in OS threads)
# ---------------------------------------------------------------------------

# Thread-local storage to track which agent is currently executing
import threading
_current_agent = threading.local()


def set_current_agent(name: str) -> None:
    """Set the agent name for the current OS thread (called before agent.run)."""
    _current_agent.name = name


def get_current_agent() -> str:
    """Get the agent name for the current OS thread."""
    return getattr(_current_agent, "name", "")


def check_tool_permission(tool_name: str) -> Optional[str]:
    """Check if the current agent has permission to use this tool.

    Called from inside tool functions (which run in OS threads).
    Returns None if allowed, or a BLOCKED message string if not.

    This is the CC 9-step cascade equivalent for server-side:
    - LOW risk tools → always allowed
    - HIGH risk tools → require explicit approval via TeamApprovalManager
    """
    if not requires_approval(tool_name):
        return None  # LOW/MEDIUM risk — always allowed

    agent_name = get_current_agent()
    if not agent_name:
        return None  # No agent context — allow (non-team execution)

    manager = get_approval_manager()
    if manager is None:
        return None  # No approval manager active — allow

    if manager.is_tool_approved(agent_name, tool_name):
        return None  # Already approved — allow

    return (
        f"BLOCKED: Tool '{tool_name}' requires human approval. "
        f"An approval request has been sent. Please wait for the operator to approve, "
        f"then try again."
    )


def _safe_args(args: dict[str, Any], max_len: int = 500) -> dict[str, str]:
    """Truncate tool args for safe SSE/storage."""
    result = {}
    for k, v in (args or {}).items():
        s = str(v)
        result[k] = s[:max_len] if len(s) > max_len else s
    return result
