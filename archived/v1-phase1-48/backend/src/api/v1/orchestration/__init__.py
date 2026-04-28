# =============================================================================
# IPA Platform - Orchestration API Module
# =============================================================================
# Sprint 96: RiskAssessor + Policies (Phase 28)
# Sprint 98: GuidedDialog + HITL API (Phase 28 Integration)
#
# Orchestration API endpoints for:
# - Intent classification and risk assessment
# - Guided dialog sessions (Sprint 98)
# - HITL approval workflow (Sprint 98)
# =============================================================================

from src.api.v1.orchestration.routes import router
from src.api.v1.orchestration.intent_routes import intent_router
from src.api.v1.orchestration.dialog_routes import dialog_router
from src.api.v1.orchestration.approval_routes import approval_router
from src.api.v1.orchestration.webhook_routes import webhook_router  # Sprint 114
from src.api.v1.orchestration.route_management import route_management_router  # Sprint 115
from src.api.v1.orchestration.chat_routes import chat_router  # Phase 45

__all__ = [
    "router",
    "intent_router",
    "dialog_router",
    "approval_router",
    "webhook_router",
    "route_management_router",
    "chat_router",
]
