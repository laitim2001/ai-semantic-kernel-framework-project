# =============================================================================
# IPA Platform - AG-UI API Module
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
#
# REST API endpoints for AG-UI protocol integration.
# Provides SSE streaming endpoint compatible with CopilotKit frontend.
#
# Dependencies:
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

from src.api.v1.ag_ui.routes import router

__all__ = ["router"]
