# =============================================================================
# IPA Platform - Memory API Module
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# This module provides FastAPI routes for memory operations.
#
# Endpoints:
#   POST   /api/v1/memory/add           - Add new memory
#   GET    /api/v1/memory/search        - Search memories
#   GET    /api/v1/memory/user/{id}     - Get user memories
#   GET    /api/v1/memory/{id}          - Get memory by ID
#   DELETE /api/v1/memory/{id}          - Delete memory
#   GET    /api/v1/memory/health        - Health check
# =============================================================================

from .routes import router
from .schemas import (
    AddMemoryRequest,
    AddMemoryResponse,
    SearchMemoryRequest,
    SearchMemoryResponse,
    MemoryResponse,
    MemoryListResponse,
)


__all__ = [
    "router",
    "AddMemoryRequest",
    "AddMemoryResponse",
    "SearchMemoryRequest",
    "SearchMemoryResponse",
    "MemoryResponse",
    "MemoryListResponse",
]
