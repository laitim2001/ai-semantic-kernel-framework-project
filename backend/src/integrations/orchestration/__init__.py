"""
Orchestration Integration Module

This module provides intelligent routing and dialog management:
- Layer 1: Pattern Matcher (rule-based, high-confidence)
- Layer 2: Semantic Router (vector similarity)
- Layer 3: LLM Classifier (semantic understanding)
- Guided Dialog Engine (multi-turn information gathering)
- Input Gateway (source-based routing with simplified paths)
- Risk Assessor (risk evaluation for routing decisions)
- HITL Controller (human-in-the-loop approval workflow)

Sprint 91: Pattern Matcher + Rule Definition (Phase 28)
Sprint 92: Semantic Router + LLM Classifier (Phase 28)
Sprint 93: BusinessIntentRouter + CompletenessChecker (Phase 28)
Sprint 94: GuidedDialogEngine + Incremental Update (Phase 28)
Sprint 95: InputGateway + SourceHandlers (Phase 28)
Sprint 96: RiskAssessor + Policies (Phase 28)
Sprint 97: HITLController + ApprovalHandler (Phase 28)
Sprint 99: E2E Tests + Performance + Metrics (Phase 28)
"""

from .intent_router.models import (
    ITIntentCategory,
    CompletenessInfo,
    RoutingDecision,
    PatternMatchResult,
    RiskLevel,
    WorkflowType,
)
from .intent_router.pattern_matcher import PatternMatcher
from .intent_router.router import (
    BusinessIntentRouter,
    RouterConfig,
    create_router,
)
from .guided_dialog import (
    # Engine
    DialogResponse,
    DialogState,
    GuidedDialogEngine,
    create_guided_dialog_engine,
    # Context Manager
    ConversationContextManager,
    # Question Generator
    QuestionGenerator,
    # Refinement Rules
    RefinementRules,
)
from .input_gateway import (
    # Models
    SourceType,
    IncomingRequest,
    GatewayConfig,
    GatewayMetrics,
    # Gateway
    InputGateway,
    create_input_gateway,
    # Schema Validator
    SchemaValidator,
    SchemaDefinition,
    ValidationError,
    # Source Handlers
    BaseSourceHandler,
    ServiceNowHandler,
    PrometheusHandler,
    UserInputHandler,
)
from .risk_assessor import (
    # Core classes
    RiskAssessor,
    RiskAssessment,
    RiskFactor,
    AssessmentContext,
    # Policy classes
    RiskPolicies,
    RiskPolicy,
)
from .hitl import (
    # Enums
    ApprovalStatus,
    ApprovalType,
    # Data classes
    ApprovalEvent,
    ApprovalRequest,
    ApprovalResult,
    # Controller and Handler
    HITLController,
    ApprovalHandler,
    # Storage
    InMemoryApprovalStorage,
    RedisApprovalStorage,
    # Notification
    TeamsNotificationService,
    TeamsMessageCard,
    TeamsCardBuilder,
    # Factory functions
    create_hitl_controller,
)
from .metrics import (
    # Collector
    OrchestrationMetricsCollector,
    # Global Functions
    get_metrics_collector,
    reset_metrics_collector,
    # Decorators
    track_routing_metrics,
    # Constants
    OPENTELEMETRY_AVAILABLE,
)

__all__ = [
    # Core Models
    "ITIntentCategory",
    "CompletenessInfo",
    "RoutingDecision",
    "PatternMatchResult",
    "RiskLevel",
    "WorkflowType",
    # Pattern Matcher
    "PatternMatcher",
    # Business Intent Router
    "BusinessIntentRouter",
    "RouterConfig",
    "create_router",
    # Guided Dialog
    "DialogResponse",
    "DialogState",
    "GuidedDialogEngine",
    "ConversationContextManager",
    "QuestionGenerator",
    "RefinementRules",
    "create_guided_dialog_engine",
    # Input Gateway - Models
    "SourceType",
    "IncomingRequest",
    "GatewayConfig",
    "GatewayMetrics",
    # Input Gateway - Core
    "InputGateway",
    "create_input_gateway",
    # Input Gateway - Schema Validator
    "SchemaValidator",
    "SchemaDefinition",
    "ValidationError",
    # Input Gateway - Source Handlers
    "BaseSourceHandler",
    "ServiceNowHandler",
    "PrometheusHandler",
    "UserInputHandler",
    # Risk Assessor
    "RiskAssessor",
    "RiskAssessment",
    "RiskFactor",
    "AssessmentContext",
    "RiskPolicies",
    "RiskPolicy",
    # HITL - Enums
    "ApprovalStatus",
    "ApprovalType",
    # HITL - Data classes
    "ApprovalEvent",
    "ApprovalRequest",
    "ApprovalResult",
    # HITL - Controller and Handler
    "HITLController",
    "ApprovalHandler",
    # HITL - Storage
    "InMemoryApprovalStorage",
    "RedisApprovalStorage",
    # HITL - Notification
    "TeamsNotificationService",
    "TeamsMessageCard",
    "TeamsCardBuilder",
    # HITL - Factory functions
    "create_hitl_controller",
    # Metrics
    "OrchestrationMetricsCollector",
    "get_metrics_collector",
    "reset_metrics_collector",
    "track_routing_metrics",
    "OPENTELEMETRY_AVAILABLE",
]
