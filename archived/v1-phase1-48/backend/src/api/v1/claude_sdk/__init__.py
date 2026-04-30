"""Claude SDK API module.

This module provides FastAPI routes for Claude Agent SDK operations.

Core Endpoints (routes.py):
    POST /api/v1/claude-sdk/query - Execute one-shot query
    POST /api/v1/claude-sdk/sessions - Create new session
    POST /api/v1/claude-sdk/sessions/{id}/query - Query within session
    DELETE /api/v1/claude-sdk/sessions/{id} - Close session
    GET /api/v1/claude-sdk/sessions/{id}/history - Get session history
    GET /api/v1/claude-sdk/health - Health check

Tools Endpoints (tools_routes.py):
    GET /api/v1/claude-sdk/tools - List all tools
    GET /api/v1/claude-sdk/tools/{name} - Get tool details
    POST /api/v1/claude-sdk/tools/execute - Execute a tool
    POST /api/v1/claude-sdk/tools/validate - Validate tool parameters

Hooks Endpoints (hooks_routes.py):
    GET /api/v1/claude-sdk/hooks - List all hooks
    GET /api/v1/claude-sdk/hooks/{id} - Get hook details
    POST /api/v1/claude-sdk/hooks/register - Register a hook
    DELETE /api/v1/claude-sdk/hooks/{id} - Remove a hook
    PUT /api/v1/claude-sdk/hooks/{id}/enable - Enable a hook
    PUT /api/v1/claude-sdk/hooks/{id}/disable - Disable a hook

MCP Endpoints (mcp_routes.py):
    GET /api/v1/claude-sdk/mcp/servers - List MCP servers
    POST /api/v1/claude-sdk/mcp/servers/connect - Connect to server
    POST /api/v1/claude-sdk/mcp/servers/{id}/disconnect - Disconnect server
    GET /api/v1/claude-sdk/mcp/servers/{id}/health - Server health check
    GET /api/v1/claude-sdk/mcp/tools - List MCP tools
    POST /api/v1/claude-sdk/mcp/tools/execute - Execute MCP tool

Hybrid Endpoints (hybrid_routes.py):
    POST /api/v1/claude-sdk/hybrid/execute - Execute hybrid task
    POST /api/v1/claude-sdk/hybrid/analyze - Analyze task
    GET /api/v1/claude-sdk/hybrid/metrics - Get metrics
    POST /api/v1/claude-sdk/hybrid/context/sync - Sync context
    GET /api/v1/claude-sdk/hybrid/capabilities - List capabilities

Intent Router Endpoints (intent_routes.py) - Sprint 52:
    POST /api/v1/claude-sdk/intent/classify - Classify user intent
    POST /api/v1/claude-sdk/intent/analyze-complexity - Analyze task complexity
    POST /api/v1/claude-sdk/intent/detect-multi-agent - Detect multi-agent needs
    GET /api/v1/claude-sdk/intent/classifiers - List available classifiers
    GET /api/v1/claude-sdk/intent/stats - Get classification statistics
    PUT /api/v1/claude-sdk/intent/config - Update router configuration

Autonomous Planning Endpoints (autonomous_routes.py) - Sprint 79:
    POST /api/v1/claude-sdk/autonomous/plan - Generate autonomous plan
    GET /api/v1/claude-sdk/autonomous/{plan_id} - Get plan details
    POST /api/v1/claude-sdk/autonomous/{plan_id}/execute - Execute plan (SSE)
    DELETE /api/v1/claude-sdk/autonomous/{plan_id} - Delete plan
    GET /api/v1/claude-sdk/autonomous - List all plans
    POST /api/v1/claude-sdk/autonomous/estimate - Estimate resources
    POST /api/v1/claude-sdk/autonomous/{plan_id}/verify - Verify execution
"""

from fastapi import APIRouter

from .routes import router as core_router
from .tools_routes import router as tools_router
from .hooks_routes import router as hooks_router
from .mcp_routes import router as mcp_router
from .hybrid_routes import router as hybrid_router
from .intent_routes import router as intent_router
from .autonomous_routes import router as autonomous_router
from .schemas import (
    QueryRequest,
    QueryResponse,
    CreateSessionRequest,
    SessionResponse,
    SessionQueryRequest,
    SessionQueryResponse,
    SessionHistoryResponse,
    CloseSessionResponse,
)

# Create main router that includes all sub-routers
router = APIRouter(prefix="/claude-sdk", tags=["Claude SDK"])

# Include all sub-routers
router.include_router(core_router)
router.include_router(tools_router)
router.include_router(hooks_router)
router.include_router(mcp_router)
router.include_router(hybrid_router)
router.include_router(intent_router)
router.include_router(autonomous_router, prefix="/autonomous")

__all__ = [
    "router",
    "core_router",
    "tools_router",
    "hooks_router",
    "mcp_router",
    "hybrid_router",
    "intent_router",
    "autonomous_router",
    "QueryRequest",
    "QueryResponse",
    "CreateSessionRequest",
    "SessionResponse",
    "SessionQueryRequest",
    "SessionQueryResponse",
    "SessionHistoryResponse",
    "CloseSessionResponse",
]
