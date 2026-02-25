# =============================================================================
# IPA Platform - Orchestrator Mediator Events
# =============================================================================
# Sprint 132: Internal event definitions for handler communication
# =============================================================================

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Event types for mediator pipeline communication."""

    ROUTING_STARTED = "routing.started"
    ROUTING_COMPLETED = "routing.completed"
    DIALOG_STARTED = "dialog.started"
    DIALOG_COMPLETED = "dialog.completed"
    DIALOG_PENDING = "dialog.pending"
    APPROVAL_STARTED = "approval.started"
    APPROVAL_COMPLETED = "approval.completed"
    APPROVAL_PENDING = "approval.pending"
    APPROVAL_REJECTED = "approval.rejected"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    CONTEXT_SYNCED = "context.synced"
    OBSERVABILITY_RECORDED = "observability.recorded"
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_ERROR = "pipeline.error"


@dataclass
class OrchestratorEvent:
    """Base event for mediator pipeline communication."""

    event_type: EventType
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    source_handler: Optional[str] = None


@dataclass
class RoutingEvent(OrchestratorEvent):
    """Event emitted by the RoutingHandler."""

    routing_decision: Optional[Any] = None
    framework_analysis: Optional[Any] = None
    needs_dialog: bool = False
    needs_approval: bool = False
    needs_swarm: bool = False


@dataclass
class DialogEvent(OrchestratorEvent):
    """Event emitted by the DialogHandler."""

    dialog_id: Optional[str] = None
    needs_more_info: bool = False
    questions: Optional[list] = None
    message: str = ""
    updated_routing: Optional[Any] = None


@dataclass
class ApprovalEvent(OrchestratorEvent):
    """Event emitted by the ApprovalHandler."""

    approval_id: Optional[str] = None
    risk_level: Optional[str] = None
    requires_approval: bool = False
    approval_status: Optional[str] = None
    comment: Optional[str] = None
    rejected_by: Optional[str] = None


@dataclass
class ExecutionEvent(OrchestratorEvent):
    """Event emitted by the ExecutionHandler."""

    framework_used: str = ""
    execution_mode: Optional[str] = None
    content: str = ""
    error: Optional[str] = None
    tokens_used: int = 0
    tool_results: list = field(default_factory=list)


@dataclass
class ObservabilityEvent(OrchestratorEvent):
    """Event emitted by the ObservabilityHandler."""

    metrics_recorded: bool = False
    execution_count: int = 0
    duration: float = 0.0
