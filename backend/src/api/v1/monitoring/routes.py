"""
Monitoring API Routes

Sprint 2 - Story S2-5: Monitoring Integration Service

Provides endpoints for:
- Prometheus metrics scraping
- Health checks with component status
- System information
"""
import logging
import platform
import os
from datetime import datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# ============================================
# Response Models
# ============================================

class ComponentHealth(BaseModel):
    """Health status of a component."""
    status: str  # "up", "down", "degraded"
    details: dict = {}


class SystemHealth(BaseModel):
    """Overall system health response."""
    status: str
    timestamp: str
    version: str
    environment: str
    components: dict[str, ComponentHealth]


class SystemInfo(BaseModel):
    """System information response."""
    service_name: str
    version: str
    environment: str
    python_version: str
    platform: str
    uptime_seconds: float
    features: dict[str, bool]


# ============================================
# Endpoints
# ============================================

@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    This endpoint is designed to be scraped by Prometheus.

    Note: In production, use opentelemetry-exporter-prometheus
    which automatically exposes metrics. This endpoint provides
    a manual fallback for local development.
    """
    try:
        # Try to use prometheus_client if available
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY
        metrics_output = generate_latest(REGISTRY)
        return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        # Fallback: Return basic metrics in Prometheus format
        metrics = [
            "# HELP ipa_platform_info Service information",
            "# TYPE ipa_platform_info gauge",
            f'ipa_platform_info{{version="{os.getenv("APP_VERSION", "0.1.0")}",environment="{os.getenv("ENVIRONMENT", "development")}"}} 1',
            "",
            "# HELP ipa_platform_up Service availability",
            "# TYPE ipa_platform_up gauge",
            "ipa_platform_up 1",
        ]
        return Response(content="\n".join(metrics), media_type="text/plain")


@router.get("/health", response_model=SystemHealth)
async def detailed_health_check():
    """
    Detailed health check with component status.

    Checks the health of all system components:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Message Queue (RabbitMQ)
    - External Services (n8n, etc.)

    Returns:
        SystemHealth with component-level status
    """
    from sqlalchemy import text
    from src.infrastructure.database.session import AsyncSessionLocal

    components = {}
    overall_status = "healthy"

    # Check Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            components["database"] = ComponentHealth(
                status="up",
                details={"type": "PostgreSQL"}
            )
    except Exception as e:
        components["database"] = ComponentHealth(
            status="down",
            details={"error": str(e)[:100]}
        )
        overall_status = "unhealthy"

    # Check Redis
    try:
        import redis.asyncio as redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", "")

        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password else None,
            decode_responses=True,
        )
        await r.ping()
        await r.close()

        components["redis"] = ComponentHealth(
            status="up",
            details={"type": "Redis", "host": redis_host}
        )
    except Exception as e:
        components["redis"] = ComponentHealth(
            status="down",
            details={"error": str(e)[:100]}
        )
        overall_status = "degraded" if overall_status != "unhealthy" else overall_status

    # Check RabbitMQ
    try:
        import httpx
        rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
        rabbitmq_port = int(os.getenv("RABBITMQ_MANAGEMENT_PORT", "15672"))
        rabbitmq_user = os.getenv("RABBITMQ_USER", "admin")
        rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "admin")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://{rabbitmq_host}:{rabbitmq_port}/api/healthchecks/node",
                auth=(rabbitmq_user, rabbitmq_password),
                timeout=5.0,
            )
            if resp.status_code == 200:
                components["rabbitmq"] = ComponentHealth(
                    status="up",
                    details={"type": "RabbitMQ", "host": rabbitmq_host}
                )
            else:
                components["rabbitmq"] = ComponentHealth(
                    status="degraded",
                    details={"status_code": resp.status_code}
                )
    except Exception as e:
        components["rabbitmq"] = ComponentHealth(
            status="down",
            details={"error": str(e)[:100]}
        )
        # RabbitMQ down doesn't make system unhealthy for reads

    return SystemHealth(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=os.getenv("APP_VERSION", "0.1.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        components=components,
    )


@router.get("/info", response_model=SystemInfo)
async def system_info():
    """
    Get system information.

    Returns service information including:
    - Version
    - Environment
    - Python version
    - Platform
    - Enabled features
    """
    # Calculate uptime (approximate - based on module load time)
    import time
    uptime = time.time() - _start_time

    return SystemInfo(
        service_name="IPA Platform API",
        version=os.getenv("APP_VERSION", "0.1.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        python_version=platform.python_version(),
        platform=platform.platform(),
        uptime_seconds=uptime,
        features={
            "telemetry_enabled": os.getenv("OTEL_SERVICE_NAME") is not None,
            "prometheus_enabled": os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true",
            "teams_notifications": os.getenv("NOTIFICATION_PROVIDER", "console") != "console",
            "n8n_integration": bool(os.getenv("N8N_BASE_URL")),
        }
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if critical dependencies are unavailable.
    """
    from sqlalchemy import text
    from src.infrastructure.database.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)[:100]}")


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the service process is alive.
    """
    return {"alive": True}


# Track start time for uptime calculation
import time
_start_time = time.time()
