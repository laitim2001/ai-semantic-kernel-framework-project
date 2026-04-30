# Session API Module
# Session Mode API - Interactive chat REST endpoints

from .routes import router as session_router
from .chat import router as chat_router
from .websocket import router as websocket_router

# Combined router for backward compatibility
from fastapi import APIRouter
router = APIRouter()
router.include_router(session_router)
router.include_router(chat_router)
router.include_router(websocket_router)

__all__ = ["router", "session_router", "chat_router", "websocket_router"]
