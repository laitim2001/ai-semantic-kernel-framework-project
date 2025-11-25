"""
IPA Platform - FastAPI Backend Application
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Version
__version__ = "0.1.0"

# Create FastAPI app
app = FastAPI(
    title="IPA Platform API",
    description="Intelligent Process Automation Platform powered by Semantic Kernel",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "IPA Platform API",
        "version": __version__,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": __version__,
    }


# Sprint 2: Audit API Routes
from src.api.v1.audit import router as audit_router

app.include_router(audit_router, prefix="/api/v1", tags=["audit"])

# Sprint 2: Webhook API Routes
from src.api.v1.webhooks import router as webhooks_router

app.include_router(webhooks_router, prefix="/api/v1", tags=["webhooks"])

# Sprint 2: Notifications API Routes (S2-3)
from src.api.v1.notifications import router as notifications_router

app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])

# Sprint 2: Checkpoints API Routes (S2-4)
from src.api.v1.checkpoints import router as checkpoints_router

app.include_router(checkpoints_router, prefix="/api/v1", tags=["checkpoints"])

# Sprint 2: Monitoring API Routes (S2-5)
from src.api.v1.monitoring import router as monitoring_router

app.include_router(monitoring_router, prefix="/api/v1", tags=["monitoring"])

# Sprint 2: Alerts API Routes (S2-6)
from src.api.v1.alerts import router as alerts_router

app.include_router(alerts_router, prefix="/api/v1", tags=["alerts"])

# Sprint 2: Admin Dashboard API Routes (S2-8)
from src.api.v1.admin import router as admin_router

app.include_router(admin_router, prefix="/api/v1", tags=["admin"])

# Initialize OpenTelemetry (if enabled)
try:
    if os.getenv("OTEL_ENABLED", "true").lower() == "true":
        from src.core.telemetry import setup_telemetry
        setup_telemetry(
            app=app,
            service_name="ipa-platform",
            service_version=__version__,
            enable_console=os.getenv("ENVIRONMENT", "development") == "development",
        )
        logger.info("OpenTelemetry instrumentation enabled")
except ImportError as e:
    logger.warning(f"OpenTelemetry not available: {e}")
except Exception as e:
    logger.error(f"Failed to initialize OpenTelemetry: {e}")

# TODO: 添加其他路由
# from src.workflow.router import router as workflow_router
# from src.execution.router import router as execution_router
# from src.agent.router import router as agent_router
#
# app.include_router(workflow_router, prefix="/api/v1/workflows", tags=["workflows"])
# app.include_router(execution_router, prefix="/api/v1/executions", tags=["executions"])
# app.include_router(agent_router, prefix="/api/v1/agents", tags=["agents"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
