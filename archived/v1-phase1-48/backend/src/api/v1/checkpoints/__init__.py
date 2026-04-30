# =============================================================================
# IPA Platform - Checkpoint API Module
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Checkpoint API module providing REST endpoints for:
#   - Listing pending checkpoints
#   - Getting checkpoint details
#   - Approving/rejecting checkpoints
#   - Checkpoint statistics
#
# Usage:
#   from src.api.v1.checkpoints import router as checkpoints_router
#   app.include_router(checkpoints_router, prefix="/api/v1")
# =============================================================================

from src.api.v1.checkpoints.routes import router

__all__ = ["router"]
