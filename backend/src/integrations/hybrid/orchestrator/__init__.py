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
from src.integrations.hybrid.orchestrator.tools import (
    OrchestratorToolRegistry,
    ToolDefinition,
    ToolResult,
    ToolType,
)
from src.integrations.hybrid.orchestrator.session_factory import (
    OrchestratorSessionFactory,
)
from src.integrations.hybrid.orchestrator.dispatch_handlers import (
    DispatchHandlers,
)

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
    # Tools (Sprint 112)
    "OrchestratorToolRegistry",
    "ToolDefinition",
    "ToolResult",
    "ToolType",
    # Session Factory (Sprint 112)
    "OrchestratorSessionFactory",
    # Dispatch Handlers (Sprint 113)
    "DispatchHandlers",
]
