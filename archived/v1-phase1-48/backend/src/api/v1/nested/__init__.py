# =============================================================================
# IPA Platform - Nested Workflow API Module
# =============================================================================
# Sprint 11: S11-5 Nested Workflow API
#
# This module provides REST API endpoints for nested workflow management:
# - Nested workflow configuration
# - Sub-workflow execution
# - Recursive pattern execution
# - Workflow composition
# - Context propagation
# =============================================================================

from src.api.v1.nested.routes import router

__all__ = ["router"]

