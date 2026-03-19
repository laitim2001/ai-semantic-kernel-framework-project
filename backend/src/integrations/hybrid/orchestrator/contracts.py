# =============================================================================
# IPA Platform - Orchestrator Mediator Contracts
# =============================================================================
# Sprint 132: Handler interfaces and shared types for Mediator Pattern
# =============================================================================

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.integrations.hybrid.intent import (
    ExecutionMode,
    IntentAnalysis,
    SessionContext,
)
from src.integrations.hybrid.context import HybridContext, SyncResult
from src.integrations.hybrid.execution import ToolExecutionResult, ToolSource


class HandlerType(str, Enum):
    """Handler type identifiers."""

    ROUTING = "routing"
    DIALOG = "dialog"
    APPROVAL = "approval"
    AGENT = "agent"
    EXECUTION = "execution"
    CONTEXT = "context"
    OBSERVABILITY = "observability"


@dataclass
class OrchestratorRequest:
    """Unified request for the mediator pipeline.

    Encapsulates all information needed to process a request through
    the mediator's handler chain.
    """

    content: str
    session_id: Optional[str] = None
    requester: str = "system"
    force_mode: Optional[ExecutionMode] = None
    tools: Optional[List[Dict[str, Any]]] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    # Source request (for Phase 28 routing flow)
    source_request: Optional[Any] = None
    # Populated during pipeline
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


@dataclass
class HandlerResult:
    """Result from a single handler execution.

    Each handler in the pipeline returns a HandlerResult to communicate
    its outcome and any data for downstream handlers.
    """

    success: bool
    handler_type: HandlerType
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    should_short_circuit: bool = False
    short_circuit_response: Optional[Any] = None


@dataclass
class OrchestratorResponse:
    """Unified response from the mediator pipeline.

    Aggregates results from all handlers into a single response.
    """

    success: bool
    content: str = ""
    error: Optional[str] = None
    framework_used: str = ""
    execution_mode: ExecutionMode = ExecutionMode.CHAT_MODE
    session_id: Optional[str] = None
    intent_analysis: Optional[IntentAnalysis] = None
    tool_results: List[ToolExecutionResult] = field(default_factory=list)
    sync_result: Optional[SyncResult] = None
    duration: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    handler_results: Dict[str, HandlerResult] = field(default_factory=dict)


class Handler(ABC):
    """Abstract base class for all mediator handlers.

    Each handler encapsulates a specific responsibility that was
    previously embedded in HybridOrchestratorV2.
    """

    @property
    @abstractmethod
    def handler_type(self) -> HandlerType:
        """Return the handler's type identifier."""
        ...

    @abstractmethod
    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Execute handler logic.

        Args:
            request: The orchestrator request being processed.
            context: Shared pipeline context for inter-handler communication.

        Returns:
            HandlerResult with the outcome of this handler's processing.
        """
        ...

    def can_handle(self, request: OrchestratorRequest, context: Dict[str, Any]) -> bool:
        """Check if this handler should process the given request.

        Default returns True. Override for conditional handlers.
        """
        return True
