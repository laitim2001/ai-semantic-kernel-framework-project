"""
Code Interpreter API 模組

提供 Azure OpenAI Code Interpreter 功能的 REST API 端點。

Sprint 37: Phase 8 - Code Interpreter Integration
Sprint 38: File Storage & Visualization
"""

from .routes import router
from .visualization import router as visualization_router

# Include visualization routes in main router
router.include_router(visualization_router)

__all__ = ["router"]
