# =============================================================================
# IPA Platform - Hybrid API Module
# =============================================================================
# Sprint 53: Context Bridge & Sync
#
# API routes for hybrid MAF + Claude SDK context management.
# =============================================================================

from .context_routes import router as context_router

__all__ = ["context_router"]
