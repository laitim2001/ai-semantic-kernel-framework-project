# =============================================================================
# IPA Platform - Orchestrator Mediator Package
# =============================================================================
# Sprint 132: HybridOrchestratorV2 Mediator Pattern Refactoring
#
# Decomposes the God Object (1,332 LOC) into:
#   - OrchestratorMediator: Event dispatch and flow coordination (<300 LOC)
#   - RoutingHandler: InputGateway + BusinessIntentRouter + FrameworkSelector
#   - DialogHandler: GuidedDialogEngine
#   - ApprovalHandler: RiskAssessor + HITLController
#   - ExecutionHandler: MAF / Claude / Swarm framework dispatch
#   - ContextHandler: ContextBridge sync
#   - ObservabilityHandler: OrchestratorMetrics
# =============================================================================

from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
    OrchestratorResponse,
)
from src.integrations.hybrid.orchestrator.events import (
    EventType,
    OrchestratorEvent,
    RoutingEvent,
    DialogEvent,
    ApprovalEvent,
    ExecutionEvent,
    ObservabilityEvent,
)
from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator

__all__ = [
    # Contracts
    "Handler",
    "HandlerResult",
    "HandlerType",
    "OrchestratorRequest",
    "OrchestratorResponse",
    # Events
    "EventType",
    "OrchestratorEvent",
    "RoutingEvent",
    "DialogEvent",
    "ApprovalEvent",
    "ExecutionEvent",
    "ObservabilityEvent",
    # Mediator
    "OrchestratorMediator",
]
