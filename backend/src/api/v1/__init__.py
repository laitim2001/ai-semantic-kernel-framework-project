# =============================================================================
# IPA Platform - API v1 Module
# =============================================================================
# Sprint 4: Developer Experience - Complete Developer Tools
# Phase 2-29: Feature development across 106 sprints
# Sprint 111: Global Auth Middleware — all protected routes require JWT
#
# API version 1 module aggregating all route modules.
#
# Architecture (Sprint 111):
#   api_router (prefix=/api/v1)
#     ├── public_router    — No authentication required
#     │   └── auth_router  — Login, Register, Refresh, etc.
#     └── protected_router — JWT authentication required (all other routes)
#         ├── Phase 1: Foundation (17 modules)
#         ├── Phase 2: Advanced Orchestration (5 modules)
#         ├── Phase 8-10: Code Interpreter + MCP + Sessions
#         ├── Phase 12: Claude Agent SDK
#         ├── Phase 13-14: Hybrid MAF+Claude SDK
#         ├── Phase 15: AG-UI Protocol
#         ├── Phase 18-22: Platform Features
#         ├── Phase 23: Multi-Agent Coordination
#         ├── Phase 28: Three-Tier Routing
#         └── Phase 29: Agent Swarm
# =============================================================================

from fastapi import APIRouter, Depends

from src.core.auth import require_auth

# =============================================================================
# Route Imports
# =============================================================================

# Phase 1: Foundation
from src.api.v1.agents.routes import router as agents_router
from src.api.v1.auth import router as auth_router  # Sprint 70: Authentication
from src.api.v1.files import router as files_router  # Sprint 75: File Upload
from src.api.v1.memory import router as memory_router  # Sprint 79: Memory System
from src.api.v1.code_interpreter.routes import router as code_interpreter_router
from src.api.v1.audit.routes import router as audit_router
from src.api.v1.audit.decision_routes import router as decision_audit_router  # Sprint 80
from src.api.v1.cache.routes import router as cache_router
from src.api.v1.checkpoints.routes import router as checkpoints_router
from src.api.v1.concurrent.routes import router as concurrent_router
from src.api.v1.connectors.routes import router as connectors_router
from src.api.v1.dashboard.routes import router as dashboard_router
from src.api.v1.devtools.routes import router as devtools_router
from src.api.v1.executions.routes import router as executions_router
from src.api.v1.groupchat.routes import router as groupchat_router
from src.api.v1.handoff.routes import router as handoff_router
from src.api.v1.learning.routes import router as learning_router
from src.api.v1.mcp.routes import router as mcp_router
from src.api.v1.sessions import router as sessions_router  # Sprint 42-47
from src.api.v1.nested.routes import router as nested_router
from src.api.v1.notifications.routes import router as notifications_router
from src.api.v1.performance.routes import router as performance_router
from src.api.v1.planning.routes import router as planning_router
from src.api.v1.prompts.routes import router as prompts_router
from src.api.v1.routing.routes import router as routing_router
from src.api.v1.templates.routes import router as templates_router
from src.api.v1.triggers.routes import router as triggers_router
from src.api.v1.versioning.routes import router as versioning_router
from src.api.v1.workflows.routes import router as workflows_router
from src.api.v1.claude_sdk import router as claude_sdk_router  # Sprint 48-51
from src.api.v1.hybrid import context_router as hybrid_context_router  # Sprint 53
from src.api.v1.hybrid import core_router as hybrid_core_router  # Sprint 52-54
from src.api.v1.hybrid import risk_router as hybrid_risk_router  # Sprint 55
from src.api.v1.hybrid import switch_router as hybrid_switch_router  # Sprint 56
from src.api.v1.ag_ui import router as ag_ui_router  # Sprint 58

# Phase 21: Sandbox Security
from src.api.v1.sandbox import router as sandbox_router  # Sprint 77-78

# Phase 22: Autonomous Planning
from src.api.v1.autonomous import router as autonomous_router  # Sprint 79

# Phase 23: Multi-Agent Coordination
from src.api.v1.a2a.routes import router as a2a_router  # Sprint 81
from src.api.v1.patrol.routes import router as patrol_router  # Sprint 82
from src.api.v1.correlation.routes import router as correlation_router  # Sprint 82
from src.api.v1.rootcause import router as rootcause_router  # Sprint 82

# Phase 28: Three-Tier Routing Architecture
from src.api.v1.orchestration import router as orchestration_router  # Sprint 96
from src.api.v1.orchestration import intent_router as orchestration_intent_router
from src.api.v1.orchestration import dialog_router as orchestration_dialog_router
from src.api.v1.orchestration import approval_router as orchestration_approval_router

# Phase 29: Agent Swarm Visualization
from src.api.v1.swarm import router as swarm_router  # Sprint 100
from src.api.v1.swarm import demo_router as swarm_demo_router  # Sprint 107

# =============================================================================
# Router Assembly
# =============================================================================

# Main API v1 router
api_router = APIRouter(prefix="/api/v1")

# -----------------------------------------------------------------------------
# Public Router — No authentication required
# Includes: auth endpoints (login, register, refresh, me)
# Note: Health check endpoints (/, /health, /ready) are registered on the
# FastAPI app directly in main.py, outside the /api/v1 prefix.
# -----------------------------------------------------------------------------
public_router = APIRouter()
public_router.include_router(auth_router)  # Sprint 70: Authentication (login, register, refresh)

# -----------------------------------------------------------------------------
# Protected Router — JWT authentication required
# All business endpoints require a valid JWT token via the require_auth
# dependency. This ensures 100% auth coverage for non-public routes.
# Individual routes can additionally use get_current_user (with DB lookup)
# from src.api.v1.dependencies for full User model access.
# -----------------------------------------------------------------------------
protected_router = APIRouter(dependencies=[Depends(require_auth)])

# Phase 1: Foundation (17 modules)
protected_router.include_router(dashboard_router)
protected_router.include_router(agents_router)
protected_router.include_router(workflows_router)
protected_router.include_router(executions_router)
protected_router.include_router(checkpoints_router)
protected_router.include_router(connectors_router)
protected_router.include_router(cache_router)
protected_router.include_router(triggers_router)
protected_router.include_router(prompts_router)
protected_router.include_router(audit_router)
protected_router.include_router(notifications_router)
protected_router.include_router(routing_router)
protected_router.include_router(templates_router)
protected_router.include_router(learning_router)
protected_router.include_router(devtools_router)
protected_router.include_router(versioning_router)

# Phase 2: Advanced Orchestration (5 modules)
protected_router.include_router(concurrent_router)   # Sprint 7
protected_router.include_router(handoff_router)      # Sprint 8
protected_router.include_router(groupchat_router)    # Sprint 9
protected_router.include_router(planning_router)     # Sprint 10
protected_router.include_router(nested_router)       # Sprint 11
protected_router.include_router(performance_router)  # Sprint 12

# Phase 8: Code Interpreter Integration
protected_router.include_router(code_interpreter_router)  # Sprint 37

# Phase 9: MCP Architecture
protected_router.include_router(mcp_router)  # Sprint 39-41

# Phase 10: Session Mode
protected_router.include_router(sessions_router)  # Sprint 42-44

# Phase 12: Claude Agent SDK Integration
protected_router.include_router(claude_sdk_router)  # Sprint 48-51

# Phase 13: Hybrid MAF + Claude SDK Architecture
protected_router.include_router(hybrid_context_router)  # Sprint 53
protected_router.include_router(hybrid_core_router)  # Sprint 52-54

# Phase 14: HITL & Approval
protected_router.include_router(hybrid_risk_router)  # Sprint 55
protected_router.include_router(hybrid_switch_router)  # Sprint 56

# Phase 15: AG-UI Integration
protected_router.include_router(ag_ui_router)  # Sprint 58

# Phase 20: File Attachment Support
protected_router.include_router(files_router)  # Sprint 75

# Phase 22: Claude Autonomous + Memory
protected_router.include_router(memory_router)  # Sprint 79
protected_router.include_router(decision_audit_router)  # Sprint 80

# Phase 21: Sandbox Security
protected_router.include_router(sandbox_router)  # Sprint 77-78

# Phase 22: Autonomous Planning
protected_router.include_router(autonomous_router)  # Sprint 79

# Phase 23: Multi-Agent Coordination
protected_router.include_router(a2a_router)  # Sprint 81
protected_router.include_router(patrol_router)  # Sprint 82
protected_router.include_router(correlation_router)  # Sprint 82
protected_router.include_router(rootcause_router)  # Sprint 82

# Phase 28: Three-Tier Routing Architecture
protected_router.include_router(orchestration_router)  # Sprint 96
protected_router.include_router(orchestration_intent_router)  # Sprint 96
protected_router.include_router(orchestration_dialog_router)  # Sprint 98
protected_router.include_router(orchestration_approval_router)  # Sprint 98

# Phase 29: Agent Swarm Visualization
protected_router.include_router(swarm_router)  # Sprint 100
protected_router.include_router(swarm_demo_router)  # Sprint 107

# -----------------------------------------------------------------------------
# Assemble into main api_router
# -----------------------------------------------------------------------------
api_router.include_router(public_router)
api_router.include_router(protected_router)

__all__ = ["api_router"]
