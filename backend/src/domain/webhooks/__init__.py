"""
Webhooks Domain Module

Provides webhook handling functionality for external integrations.
Sprint 2 - Story S2-1
"""
from .n8n_service import N8nWebhookService
from .schemas import (
    WebhookPayload,
    WebhookResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)

__all__ = [
    "N8nWebhookService",
    "WebhookPayload",
    "WebhookResponse",
    "WebhookTestRequest",
    "WebhookTestResponse",
]
