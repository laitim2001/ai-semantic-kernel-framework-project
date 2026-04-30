# =============================================================================
# IPA Platform - Auth API Module
# =============================================================================
# Sprint 70: S70-3 - Auth API Routes
# Sprint 72: S72-2 - Guest Data Migration API
# Phase 18: Authentication System
#
# Authentication API endpoints for registration, login, and token management.
# Includes guest data migration for authenticated users.
# =============================================================================

from src.api.v1.auth.routes import router
from src.api.v1.auth.migration import router as migration_router

# Include migration routes under auth prefix
router.include_router(migration_router)

__all__ = ["router"]
