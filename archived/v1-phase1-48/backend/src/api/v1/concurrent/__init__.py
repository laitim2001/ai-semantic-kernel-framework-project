# =============================================================================
# IPA Platform - Concurrent Execution API Module
# =============================================================================
# Sprint 7: Concurrent Execution Engine (Phase 2)
# Sprint 14: ConcurrentBuilder 重構 (Phase 3 - P3-F1)
#
# API module for parallel execution management.
# Provides endpoints for:
#   - Concurrent task execution with Fork-Join patterns
#   - Branch status monitoring
#   - Execution cancellation
#   - Real-time WebSocket updates
#
# Phase 3 additions:
#   - V2 endpoints using ConcurrentBuilderAdapter
#   - Adapter service for migration support
#   - Backward compatible API schema
# =============================================================================

from src.api.v1.concurrent.routes import router
from src.api.v1.concurrent.adapter_service import (
    ConcurrentAPIService,
    ExecuteRequest,
    ExecuteResponse,
    BranchInfo,
    get_concurrent_api_service,
    reset_concurrent_api_service,
)

__all__ = [
    "router",
    # Phase 3: Adapter service
    "ConcurrentAPIService",
    "ExecuteRequest",
    "ExecuteResponse",
    "BranchInfo",
    "get_concurrent_api_service",
    "reset_concurrent_api_service",
]
