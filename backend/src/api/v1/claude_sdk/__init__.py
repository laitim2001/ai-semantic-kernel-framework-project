"""Claude SDK API module.

This module provides FastAPI routes for Claude Agent SDK operations.

Endpoints:
    POST /api/v1/claude-sdk/query - Execute one-shot query
    POST /api/v1/claude-sdk/sessions - Create new session
    POST /api/v1/claude-sdk/sessions/{id}/query - Query within session
    DELETE /api/v1/claude-sdk/sessions/{id} - Close session
    GET /api/v1/claude-sdk/sessions/{id}/history - Get session history
    GET /api/v1/claude-sdk/health - Health check
"""

from .routes import router
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

__all__ = [
    "router",
    "QueryRequest",
    "QueryResponse",
    "CreateSessionRequest",
    "SessionResponse",
    "SessionQueryRequest",
    "SessionQueryResponse",
    "SessionHistoryResponse",
    "CloseSessionResponse",
]
