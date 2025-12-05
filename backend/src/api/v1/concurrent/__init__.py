# =============================================================================
# IPA Platform - Concurrent Execution API Module
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# API module for parallel execution management.
# Provides endpoints for:
#   - Concurrent task execution with Fork-Join patterns
#   - Branch status monitoring
#   - Execution cancellation
#   - Real-time WebSocket updates
# =============================================================================

from src.api.v1.concurrent.routes import router

__all__ = ["router"]
