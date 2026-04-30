# =============================================================================
# IPA Platform - Hybrid API Module
# =============================================================================
# Sprint 53: Context Bridge & Sync
# Sprint 55: S55-4 - Risk Assessment API Integration
# Sprint 56: Mode Switcher & HITL - Mode Switch API
# Sprint 52-54: Core Hybrid Routes (analyze, execute, metrics)
#
# API routes for hybrid MAF + Claude SDK context management.
# Includes risk assessment endpoints, mode switching API, and core hybrid operations.
# =============================================================================

from .context_routes import router as context_router
from .core_routes import router as core_router
from .risk_routes import router as risk_router
from .switch_routes import router as switch_router

__all__ = ["context_router", "core_router", "risk_router", "switch_router"]
