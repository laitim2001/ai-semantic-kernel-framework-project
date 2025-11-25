"""
Notifications Domain Module

Sprint 2 - Story S2-3: Teams Notification Service

Provides:
- TeamsNotificationService for sending Teams Adaptive Cards
- Console/Mock provider for local development
- Webhook provider for production Teams integration
"""
from .service import TeamsNotificationService, get_notification_service
from .schemas import (
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    AdaptiveCardContent,
)

__all__ = [
    "TeamsNotificationService",
    "get_notification_service",
    "NotificationRequest",
    "NotificationResponse",
    "NotificationStatus",
    "AdaptiveCardContent",
]
