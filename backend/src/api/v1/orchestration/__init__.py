# =============================================================================
# IPA Platform - Orchestration API Module
# =============================================================================
# Sprint 96: RiskAssessor + Policies (Phase 28)
#
# Orchestration API endpoints for intent classification and risk assessment.
# =============================================================================

from src.api.v1.orchestration.routes import router
from src.api.v1.orchestration.intent_routes import intent_router

__all__ = ["router", "intent_router"]
