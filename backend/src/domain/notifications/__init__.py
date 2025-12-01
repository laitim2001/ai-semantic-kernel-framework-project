"""
Notifications Domain Module
============================

This module provides notification services for the IPA Platform, including:
- Microsoft Teams integration via Adaptive Cards
- Approval request notifications
- Execution completion notifications
- Error alert notifications

Sprint 3 - S3-4: Teams Notification Integration

Author: IPA Platform Team
Created: 2025-11-30
"""

from src.domain.notifications.teams import (
    NotificationError,
    NotificationPriority,
    NotificationResult,
    NotificationType,
    TeamsCard,
    TeamsNotificationConfig,
    TeamsNotificationService,
)

__all__ = [
    # Configuration
    "TeamsNotificationConfig",
    # Service
    "TeamsNotificationService",
    # Types
    "NotificationType",
    "NotificationPriority",
    "NotificationResult",
    "TeamsCard",
    # Exceptions
    "NotificationError",
]
