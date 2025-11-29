"""
Tools API module

Provides REST APIs for tool management and execution.
"""
from fastapi import APIRouter
from .routes import router as tools_router

router = APIRouter()
router.include_router(tools_router, tags=["tools"])

__all__ = ["router"]
