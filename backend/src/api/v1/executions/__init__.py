# =============================================================================
# IPA Platform - Executions API Module
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Execution API module providing REST endpoints for:
#   - Listing executions with pagination and filtering
#   - Getting execution details
#   - Cancelling executions
#   - Getting valid state transitions
# =============================================================================

from src.api.v1.executions.routes import router

__all__ = ["router"]
