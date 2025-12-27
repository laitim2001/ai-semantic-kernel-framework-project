# =============================================================================
# IPA Platform - Main Application
# Phase 11 Fix: Added chat/websocket routers with /sessions prefix (2025-12-24)
# =============================================================================
# Intelligent Process Automation Platform
#
# Built on Microsoft Agent Framework for multi-agent orchestration
# with human-in-the-loop capabilities.
#
# Sprint 1: Core Engine - Agent Framework Integration
# =============================================================================

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Version
__version__ = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup/shutdown events.

    Initializes and cleans up:
        - Database connection pool
        - Agent Framework service
        - Redis cache (future)
    """
    settings = get_settings()

    # Startup
    logger.info(f"IPA Platform v{__version__} starting...")
    logger.info(f"Environment: {settings.app_env}")

    # Initialize database
    try:
        from src.infrastructure.database.session import init_db
        await init_db()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Continue without database in development
        if settings.app_env == "production":
            raise

    # Initialize Agent Service
    try:
        from src.domain.agents.service import init_agent_service
        await init_agent_service()
        logger.info("Agent service initialized")
    except Exception as e:
        logger.warning(f"Agent service initialization warning: {e}")
        # Continue without agent service - will use mock mode

    yield

    # Shutdown
    logger.info("IPA Platform shutting down...")

    # Close database connections
    try:
        from src.infrastructure.database.session import close_db
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

    # Shutdown Agent Service
    try:
        from src.domain.agents.service import get_agent_service
        service = get_agent_service()
        await service.shutdown()
        logger.info("Agent service shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down agent service: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="IPA Platform API",
        description="""
        Intelligent Process Automation Platform

        Built on Microsoft Agent Framework for enterprise AI agent orchestration.

        ## Features (MVP)
        - F1: Multi-Agent Orchestration
        - F2: Human-in-the-loop Checkpoints
        - F3: Cross-system Integration
        - F4: Cross-scenario Collaboration
        - F5: Few-shot Learning
        - F6: Agent Templates
        - F7: DevUI Debugging
        - F8: n8n Trigger Integration
        - F9: Prompt Template Management
        - F10: Audit Trail
        - F11: Teams Notifications
        - F12: Monitoring Dashboard
        - F13: Web UI
        - F14: Redis Caching

        ## API Endpoints
        - `/api/v1/agents` - Agent management and execution
        - `/api/v1/workflows` - Workflow definitions (coming soon)
        - `/api/v1/executions` - Execution tracking (coming soon)
        """,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_api_docs else None,
        redoc_url="/redoc" if settings.enable_api_docs else None,
        openapi_url="/openapi.json" if settings.enable_api_docs else None,
        # Disable automatic redirect from /path to /path/ to avoid 307 responses
        redirect_slashes=False,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""

    @app.get("/", tags=["Health"])
    async def root():
        """Root endpoint - API information."""
        return {
            "service": "IPA Platform API",
            "version": __version__,
            "status": "running",
            "framework": "Microsoft Agent Framework",
            "docs": "/docs",
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for container orchestration."""
        # Check database connectivity
        db_status = "ok"
        try:
            from sqlalchemy import text
            from src.infrastructure.database.session import get_engine
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            db_status = "degraded"

        return JSONResponse(
            content={
                "status": "healthy" if db_status == "ok" else "degraded",
                "version": __version__,
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "api": "ok",
                    "database": db_status,
                },
            },
            status_code=200,
        )

    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        """Readiness check endpoint for Kubernetes/Azure App Service."""
        return JSONResponse(
            content={
                "ready": True,
                "version": __version__,
            },
            status_code=200,
        )

    # ==========================================================================
    # API v1 Routes
    # ==========================================================================

    # Include API v1 router
    from src.api.v1 import api_router
    app.include_router(api_router)


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
