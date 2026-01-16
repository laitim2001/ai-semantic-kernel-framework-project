"""
HITL (Human-in-the-Loop) Module

Provides human approval workflow management for high-risk IT operations.

Components:
- HITLController: Main controller for approval workflow coordination
- ApprovalHandler: High-level approval operations with persistence
- NotificationService: Teams/Email notification for approval requests

Sprint 97: Phase 28 - HITL Implementation
"""

from .controller import (
    # Enums
    ApprovalStatus,
    ApprovalType,
    # Data classes
    ApprovalEvent,
    ApprovalRequest,
    # Protocols
    ApprovalStorage,
    NotificationService,
    # Controller
    HITLController,
    # Implementations
    InMemoryApprovalStorage,
    MockNotificationService,
    # Factory functions
    create_hitl_controller,
    create_mock_hitl_controller,
)

from .approval_handler import (
    # Storage
    RedisApprovalStorage,
    # Handler
    ApprovalResult,
    ApprovalHandler,
    # Factory functions
    create_approval_handler,
    create_redis_storage,
)

from .notification import (
    # Card structures
    TeamsMessageCard,
    TeamsCardBuilder,
    # Results
    NotificationResult,
    # Services
    TeamsNotificationService,
    EmailNotificationService,
    CompositeNotificationService,
    # Factory functions
    create_teams_notification_service,
    create_composite_notification_service,
)


__all__ = [
    # Enums
    "ApprovalStatus",
    "ApprovalType",
    # Data classes
    "ApprovalEvent",
    "ApprovalRequest",
    "ApprovalResult",
    # Protocols
    "ApprovalStorage",
    "NotificationService",
    # Controller
    "HITLController",
    # Handler
    "ApprovalHandler",
    # Storage implementations
    "InMemoryApprovalStorage",
    "RedisApprovalStorage",
    # Notification
    "TeamsMessageCard",
    "TeamsCardBuilder",
    "NotificationResult",
    "TeamsNotificationService",
    "EmailNotificationService",
    "CompositeNotificationService",
    "MockNotificationService",
    # Factory functions
    "create_hitl_controller",
    "create_mock_hitl_controller",
    "create_approval_handler",
    "create_redis_storage",
    "create_teams_notification_service",
    "create_composite_notification_service",
]
