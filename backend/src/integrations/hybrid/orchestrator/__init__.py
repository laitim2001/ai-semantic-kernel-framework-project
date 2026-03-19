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
from src.integrations.hybrid.orchestrator.task_result_protocol import (
    TaskResultEnvelope,
    TaskResultNormaliser,
    WorkerResult,
    WorkerType,
    ResultStatus,
)
from src.integrations.hybrid.orchestrator.result_synthesiser import (
    ResultSynthesiser,
)
from src.integrations.hybrid.orchestrator.session_recovery import (
    SessionRecoveryManager,
    SessionSummary,
    RecoveryResult,
)
from src.integrations.hybrid.orchestrator.observability_bridge import (
    ObservabilityBridge,
)
from src.integrations.hybrid.orchestrator.memory_manager import (
    OrchestratorMemoryManager,
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
    # TaskResult Protocol + Synthesiser (Sprint 114)
    "TaskResultEnvelope",
    "TaskResultNormaliser",
    "WorkerResult",
    "WorkerType",
    "ResultStatus",
    "ResultSynthesiser",
    # Session Recovery (Sprint 115)
    "SessionRecoveryManager",
    "SessionSummary",
    "RecoveryResult",
    # Observability Bridge (Sprint 116)
    "ObservabilityBridge",
    # Memory Manager (Sprint 117)
    "OrchestratorMemoryManager",
]
