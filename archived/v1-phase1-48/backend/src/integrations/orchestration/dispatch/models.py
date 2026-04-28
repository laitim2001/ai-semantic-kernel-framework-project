"""
Dispatch Models — Request/Result types for execution dispatch.

Phase 45: Orchestration Core (Sprint 155)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionRoute(str, Enum):
    """Available execution routes."""

    DIRECT_ANSWER = "direct_answer"
    SUBAGENT = "subagent"
    TEAM = "team"

    @classmethod
    def from_string(cls, value: str) -> "ExecutionRoute":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.TEAM


@dataclass
class DispatchRequest:
    """Request payload for dispatch execution.

    Attributes:
        route: The selected execution route.
        task: The original user task.
        user_id: User identifier.
        session_id: Session identifier.
        memory_text: Token-budgeted memory context.
        knowledge_text: Knowledge base search results.
        intent_summary: Intent analysis summary string.
        risk_level: Risk level string.
        route_reasoning: LLM's reasoning for route selection.
        metadata: Additional context for executor.
    """

    route: ExecutionRoute
    task: str
    user_id: str
    session_id: str
    memory_text: str = ""
    knowledge_text: str = ""
    intent_summary: str = ""
    risk_level: str = "low"
    route_reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from a single agent execution.

    Attributes:
        agent_name: Name of the agent.
        role: Agent's role description.
        output: Agent's text output.
        tool_calls: List of tool calls made.
        duration_ms: Execution time in milliseconds.
        status: "completed" | "failed" | "timeout".
    """

    agent_name: str
    role: str = ""
    output: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    status: str = "completed"


@dataclass
class DispatchResult:
    """Result from dispatch execution.

    Attributes:
        route: The execution route used.
        response_text: Final response text for the user.
        agent_results: Individual agent results (for subagent/team modes).
        synthesis: Synthesized summary (for multi-agent modes).
        duration_ms: Total dispatch execution time.
        status: "completed" | "failed" | "not_implemented".
        metadata: Additional result metadata.
    """

    route: ExecutionRoute
    response_text: str = ""
    agent_results: List[AgentResult] = field(default_factory=list)
    synthesis: str = ""
    duration_ms: float = 0.0
    status: str = "completed"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route.value,
            "response_text": self.response_text[:500],
            "agent_count": len(self.agent_results),
            "synthesis_preview": self.synthesis[:200],
            "duration_ms": round(self.duration_ms, 1),
            "status": self.status,
        }
