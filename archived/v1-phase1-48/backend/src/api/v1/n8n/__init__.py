"""n8n Integration API Module.

Provides webhook endpoints for n8n → IPA integration (Mode 2)
and connection management endpoints.

Sprint 124: Phase 34 — n8n Integration Mode 1 + Mode 2
"""

from .routes import router

__all__ = ["router"]
