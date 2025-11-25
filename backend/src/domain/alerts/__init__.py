"""
Alerts Domain Module

Sprint 2 - Story S2-6: Alert Manager Integration
"""
from .schemas import (
    Alert,
    AlertLabel,
    AlertAnnotation,
    AlertManagerPayload,
    AlertResponse,
    AlertHistoryItem,
    AlertStatsResponse,
)
from .service import AlertService, get_alert_service

__all__ = [
    "Alert",
    "AlertLabel",
    "AlertAnnotation",
    "AlertManagerPayload",
    "AlertResponse",
    "AlertHistoryItem",
    "AlertStatsResponse",
    "AlertService",
    "get_alert_service",
]
