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
from typing import AsyncGenerator, Callable, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_settings

# Configure logging — use structlog if enabled, otherwise basic config
_settings = get_settings()
if _settings.structured_logging_enabled:
    from src.core.logging import setup_logging
    setup_logging(
        json_output=True,
        log_level=_settings.log_level,
        enable_otel_correlation=_settings.otel_enabled,
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
logger = logging.getLogger(__name__)

# Observability shutdown callback (set during lifespan startup)
_otel_shutdown: Optional[Callable[[], None]] = None

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
    global _otel_shutdown
    settings = get_settings()

    # Startup
    logger.info(f"IPA Platform v{__version__} starting...")
    logger.info(f"Environment: {settings.app_env}")

    # Validate security settings (warns in dev, raises in production)
    settings.validate_security_settings()

    # Initialize OpenTelemetry observability (Sprint 122)
    if settings.otel_enabled:
        try:
            from src.core.observability import setup_observability

            _otel_shutdown = setup_observability(
                service_name=settings.otel_service_name,
                connection_string=settings.applicationinsights_connection_string,
                otel_enabled=True,
                sampling_rate=settings.otel_sampling_rate,
            )
            logger.info("OpenTelemetry observability initialized")
        except Exception as e:
            logger.warning(f"OpenTelemetry initialization failed: {e}")
            _otel_shutdown = None

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

    # Seed built-in expert definitions (Sprint 163)
    try:
        from src.integrations.orchestration.experts.seeder import seed_builtin_experts
        from src.infrastructure.database.session import DatabaseSession
        async with DatabaseSession() as session:
            seeded = await seed_builtin_experts(session)
        logger.info(f"Expert registry seeded: {seeded} new experts")
    except Exception as e:
        logger.warning(f"Expert registry seeding skipped: {e}")

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

    # Shutdown OpenTelemetry (Sprint 122)
    if _otel_shutdown:
        try:
            _otel_shutdown()
            logger.info("OpenTelemetry shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down OpenTelemetry: {e}")


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

    # Request ID middleware (Sprint 122) — must be added before CORS
    from src.core.logging.middleware import RequestIdMiddleware
    app.add_middleware(RequestIdMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch all unhandled exceptions with environment-aware responses."""
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc}",
            exc_info=True,
            extra={"request_path": str(request.url.path)},
        )

        if settings.app_env == "development":
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc),
                },
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                },
            )

    # Rate limiting middleware (Sprint 111)
    from src.middleware.rate_limit import setup_rate_limiting
    setup_rate_limiting(app)

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

        # Check Redis connectivity (Sprint 112)
        redis_status = "ok"
        try:
            import os
            redis_host = os.environ.get("REDIS_HOST")
            if redis_host:
                from redis.asyncio import Redis as AsyncRedis
                redis_port = int(os.environ.get("REDIS_PORT", "6379"))
                redis_password = os.environ.get("REDIS_PASSWORD")
                redis_client = AsyncRedis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                )
                await redis_client.ping()
                await redis_client.aclose()
            else:
                redis_status = "not_configured"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_status = "degraded"

        overall = "healthy"
        if db_status != "ok" or redis_status == "degraded":
            overall = "degraded"

        return JSONResponse(
            content={
                "status": overall,
                "version": __version__,
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "api": "ok",
                    "database": db_status,
                    "redis": redis_status,
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

    from src.core.server_config import ServerConfig

    server_config = ServerConfig()
    logger.info(f"Starting with config: {server_config}")

    uvicorn.run(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        reload=server_config.reload,
        workers=server_config.workers,
        log_level=server_config.log_level,
    )
