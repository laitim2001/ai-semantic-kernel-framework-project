# =============================================================================
# IPA Platform - API v1 Module
# =============================================================================
# Sprint 4: Developer Experience - Complete Developer Tools
# Sprint 7: Concurrent Execution Engine (Phase 2)
#
# API version 1 module aggregating all route modules.
# Includes:
#   - agents: Agent CRUD and execution
#   - workflows: Workflow CRUD and validation
#   - executions: Execution tracking and state management
#   - checkpoints: Human-in-the-loop checkpoint management
#   - connectors: Cross-system connector management
#   - cache: LLM response caching
#   - triggers: Webhook trigger management (n8n integration)
#   - prompts: Prompt template management
#   - audit: Audit logging and compliance
#   - notifications: Teams notification integration
#   - routing: Cross-scenario routing
#   - templates: Agent template marketplace (Sprint 4)
#   - learning: Few-shot learning mechanism (Sprint 4)
#   - devtools: Execution tracing and debugging (Sprint 4)
#   - versioning: Template version management (Sprint 4)
#   - concurrent: Concurrent execution with Fork-Join (Sprint 7)
# =============================================================================

from fastapi import APIRouter

from src.api.v1.agents.routes import router as agents_router
from src.api.v1.audit.routes import router as audit_router
from src.api.v1.cache.routes import router as cache_router
from src.api.v1.checkpoints.routes import router as checkpoints_router
from src.api.v1.concurrent.routes import router as concurrent_router
from src.api.v1.connectors.routes import router as connectors_router
from src.api.v1.dashboard.routes import router as dashboard_router
from src.api.v1.devtools.routes import router as devtools_router
from src.api.v1.executions.routes import router as executions_router
from src.api.v1.learning.routes import router as learning_router
from src.api.v1.notifications.routes import router as notifications_router
from src.api.v1.prompts.routes import router as prompts_router
from src.api.v1.routing.routes import router as routing_router
from src.api.v1.templates.routes import router as templates_router
from src.api.v1.triggers.routes import router as triggers_router
from src.api.v1.versioning.routes import router as versioning_router
from src.api.v1.workflows.routes import router as workflows_router

# Create main v1 router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(dashboard_router)
api_router.include_router(agents_router)
api_router.include_router(workflows_router)
api_router.include_router(executions_router)
api_router.include_router(checkpoints_router)
api_router.include_router(connectors_router)
api_router.include_router(cache_router)
api_router.include_router(triggers_router)
api_router.include_router(prompts_router)
api_router.include_router(audit_router)
api_router.include_router(notifications_router)
api_router.include_router(routing_router)
api_router.include_router(templates_router)
api_router.include_router(learning_router)
api_router.include_router(devtools_router)
api_router.include_router(versioning_router)
api_router.include_router(concurrent_router)  # Sprint 7: Concurrent Execution

__all__ = ["api_router"]
