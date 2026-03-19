"""L3 Agent Execution State — PostgreSQL-backed execution context persistence.

Stores durable agent execution data:
  - Agent context snapshots
  - Tool call history with inputs/outputs
  - Intermediate results from multi-step executions

This is the most durable layer of the three-layer checkpoint system.

Sprint 115 — Phase 37 E2E Assembly B.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.infrastructure.storage.backends.base import StorageBackendABC
from src.infrastructure.storage.backends.factory import StorageFactory

logger = logging.getLogger(__name__)

_KEY_PREFIX = "exec:"


class ToolCallRecord(BaseModel):
    """Record of a single tool invocation."""

    tool_name: str
    tool_id: str = ""
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    success: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentExecutionState(BaseModel):
    """Execution state for an agent within a session.

    Captures everything needed to resume an agent's execution from
    its last known state.
    """

    session_id: str
    execution_id: str
    agent_id: Optional[str] = None
    agent_type: str = "orchestrator"  # orchestrator / maf / claude / swarm

    # Context snapshot
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = "chat"  # chat / workflow / hybrid / swarm

    # Tool call history
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)

    # Intermediate results
    intermediate_results: List[Dict[str, Any]] = Field(default_factory=list)

    # State
    status: str = "active"  # active / paused / completed / failed
    progress: float = 0.0
    error: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_tool_call(self, record: ToolCallRecord) -> None:
        """Append a tool call record."""
        self.tool_calls.append(record)
        self.updated_at = datetime.utcnow()

    def add_intermediate_result(self, result: Dict[str, Any]) -> None:
        """Append an intermediate result."""
        self.intermediate_results.append(result)
        self.updated_at = datetime.utcnow()


class ExecutionStateStore:
    """L3 Agent Execution State store.

    Uses PostgreSQL for permanent persistence (no TTL).

    Args:
        backend: Storage backend (PostgreSQL preferred).
    """

    def __init__(self, backend: Optional[StorageBackendABC] = None) -> None:
        self._backend = backend

    async def _ensure_backend(self) -> StorageBackendABC:
        if self._backend is None:
            self._backend = await StorageFactory.create(
                name="execution_state",
                backend_type="auto",
            )
            logger.info(
                "ExecutionStateStore: backend=%s",
                type(self._backend).__name__,
            )
        return self._backend

    def _key(self, execution_id: str) -> str:
        return f"{_KEY_PREFIX}{execution_id}"

    def _session_key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}session:{session_id}"

    async def save(self, state: AgentExecutionState) -> None:
        """Persist execution state (no TTL — permanent)."""
        backend = await self._ensure_backend()
        state.updated_at = datetime.utcnow()
        data = state.model_dump(mode="json")
        # Save by execution_id
        await backend.set(self._key(state.execution_id), data)
        # Also index by session_id for session-level queries
        session_index = await backend.get(self._session_key(state.session_id))
        if session_index is None:
            session_index = {"execution_ids": []}
        if state.execution_id not in session_index["execution_ids"]:
            session_index["execution_ids"].append(state.execution_id)
        await backend.set(self._session_key(state.session_id), session_index)

    async def load(self, execution_id: str) -> Optional[AgentExecutionState]:
        """Load execution state by ID."""
        backend = await self._ensure_backend()
        data = await backend.get(self._key(execution_id))
        if data is None:
            return None
        return AgentExecutionState.model_validate(data)

    async def load_by_session(self, session_id: str) -> List[AgentExecutionState]:
        """Load all execution states for a session."""
        backend = await self._ensure_backend()
        session_index = await backend.get(self._session_key(session_id))
        if session_index is None:
            return []

        states: List[AgentExecutionState] = []
        for exec_id in session_index.get("execution_ids", []):
            state = await self.load(exec_id)
            if state:
                states.append(state)
        return states

    async def delete(self, execution_id: str) -> None:
        """Remove an execution state."""
        backend = await self._ensure_backend()
        await backend.delete(self._key(execution_id))

    async def update_progress(
        self, execution_id: str, progress: float, status: Optional[str] = None
    ) -> Optional[AgentExecutionState]:
        """Update execution progress and optional status."""
        state = await self.load(execution_id)
        if state is None:
            return None
        state.progress = min(max(progress, 0.0), 1.0)
        if status:
            state.status = status
        await self.save(state)
        return state
