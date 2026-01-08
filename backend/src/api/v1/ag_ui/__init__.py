# =============================================================================
# IPA Platform - AG-UI API Module
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-1: AG-UI SSE Endpoint
# Sprint 68: S68-3: File Upload API
#
# REST API endpoints for AG-UI protocol integration.
# Provides SSE streaming endpoint compatible with CopilotKit frontend.
#
# Dependencies:
#   - HybridEventBridge (src.integrations.ag_ui.bridge)
#   - AG-UI Events (src.integrations.ag_ui.events)
#   - SandboxConfig (src.core.sandbox_config)
# =============================================================================

from src.api.v1.ag_ui.routes import router
from src.api.v1.ag_ui.upload import router as upload_router

# Include upload router under main router
router.include_router(upload_router)

__all__ = ["router", "upload_router"]
