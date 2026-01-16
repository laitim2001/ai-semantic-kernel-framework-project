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
    MockBusinessIntentRouter,
    RouterConfig,
    create_router,
    create_mock_router,
)
from .guided_dialog import (
    GuidedDialogEngine,
    MockGuidedDialogEngine,
    ConversationContextManager,
    QuestionGenerator,
    RefinementRules,
    create_guided_dialog_engine,
    create_mock_dialog_engine,
)
from .input_gateway import (
    # Models
    SourceType,
    IncomingRequest,
    GatewayConfig,
    GatewayMetrics,
    # Gateway
    InputGateway,
    MockInputGateway,
    create_input_gateway,
    create_mock_gateway,
    # Schema Validator
    SchemaValidator,
    MockSchemaValidator,
    SchemaDefinition,
    ValidationError,
    # Source Handlers
    BaseSourceHandler,
    ServiceNowHandler,
    MockServiceNowHandler,
    PrometheusHandler,
    MockPrometheusHandler,
    UserInputHandler,
    MockUserInputHandler,
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
    MockNotificationService,
    # Factory functions
    create_hitl_controller,
    create_mock_hitl_controller,
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
    "MockBusinessIntentRouter",
    "RouterConfig",
    "create_router",
    "create_mock_router",
    # Guided Dialog
    "GuidedDialogEngine",
    "MockGuidedDialogEngine",
    "ConversationContextManager",
    "QuestionGenerator",
    "RefinementRules",
    "create_guided_dialog_engine",
    "create_mock_dialog_engine",
    # Input Gateway - Models
    "SourceType",
    "IncomingRequest",
    "GatewayConfig",
    "GatewayMetrics",
    # Input Gateway - Core
    "InputGateway",
    "MockInputGateway",
    "create_input_gateway",
    "create_mock_gateway",
    # Input Gateway - Schema Validator
    "SchemaValidator",
    "MockSchemaValidator",
    "SchemaDefinition",
    "ValidationError",
    # Input Gateway - Source Handlers
    "BaseSourceHandler",
    "ServiceNowHandler",
    "MockServiceNowHandler",
    "PrometheusHandler",
    "MockPrometheusHandler",
    "UserInputHandler",
    "MockUserInputHandler",
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
    "MockNotificationService",
    # HITL - Factory functions
    "create_hitl_controller",
    "create_mock_hitl_controller",
]
