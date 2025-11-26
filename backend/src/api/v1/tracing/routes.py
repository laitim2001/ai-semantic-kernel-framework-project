"""
Tracing API Routes

Sprint 3 - Story S3-6: Distributed Tracing with Jaeger

Provides endpoints for:
- Tracing configuration status
- Test trace generation
- Trace context inspection
- Jaeger integration status
"""
import os
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field

from src.core.telemetry import (
    get_tracer,
    get_trace_id,
    get_span_id,
    create_span,
    add_span_attributes,
    add_span_event,
    set_span_status,
)
from opentelemetry.trace import SpanKind, StatusCode

router = APIRouter(prefix="/tracing", tags=["tracing"])


class TracingConfigResponse(BaseModel):
    """Response model for tracing configuration."""
    enabled: bool = Field(description="Whether tracing is enabled")
    service_name: str = Field(description="Service name in traces")
    jaeger_enabled: bool = Field(description="Whether Jaeger export is enabled")
    jaeger_endpoint: Optional[str] = Field(description="Jaeger OTLP endpoint")
    otlp_endpoint: Optional[str] = Field(description="OTLP endpoint")
    environment: str = Field(description="Environment name")


class TraceContextResponse(BaseModel):
    """Response model for current trace context."""
    trace_id: Optional[str] = Field(description="Current trace ID")
    span_id: Optional[str] = Field(description="Current span ID")
    has_valid_context: bool = Field(description="Whether context is valid")


class TestTraceResponse(BaseModel):
    """Response model for test trace generation."""
    trace_id: str = Field(description="Generated trace ID")
    span_count: int = Field(description="Number of spans created")
    duration_ms: float = Field(description="Total duration in milliseconds")
    message: str = Field(description="Status message")


class SpanInfo(BaseModel):
    """Information about a generated span."""
    name: str
    kind: str
    duration_ms: float
    attributes: Dict[str, Any]


class DetailedTraceResponse(BaseModel):
    """Detailed response for test trace generation."""
    trace_id: str
    spans: List[SpanInfo]
    total_duration_ms: float
    jaeger_ui_url: Optional[str] = Field(description="Link to view trace in Jaeger")


class JaegerHealthResponse(BaseModel):
    """Response model for Jaeger health check."""
    status: str = Field(description="Jaeger connection status")
    ui_url: Optional[str] = Field(description="Jaeger UI URL")
    collector_endpoint: Optional[str] = Field(description="Collector endpoint")
    message: str = Field(description="Status message")


@router.get(
    "/config",
    response_model=TracingConfigResponse,
    summary="Get tracing configuration",
    description="Returns the current tracing configuration including Jaeger settings.",
)
async def get_tracing_config() -> TracingConfigResponse:
    """Get current tracing configuration."""
    jaeger_enabled = os.getenv("JAEGER_ENABLED", "false").lower() == "true"
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    return TracingConfigResponse(
        enabled=True,
        service_name=os.getenv("OTEL_SERVICE_NAME", "ipa-platform"),
        jaeger_enabled=jaeger_enabled or bool(otlp_endpoint),
        jaeger_endpoint=f"http://{os.getenv('JAEGER_AGENT_HOST', 'localhost')}:16686" if jaeger_enabled else None,
        otlp_endpoint=otlp_endpoint,
        environment=os.getenv("APP_ENV", "development"),
    )


@router.get(
    "/context",
    response_model=TraceContextResponse,
    summary="Get current trace context",
    description="Returns the current trace and span IDs for debugging.",
)
async def get_trace_context() -> TraceContextResponse:
    """Get the current trace context."""
    trace_id = get_trace_id()
    span_id = get_span_id()

    return TraceContextResponse(
        trace_id=trace_id,
        span_id=span_id,
        has_valid_context=bool(trace_id and span_id),
    )


@router.post(
    "/test",
    response_model=TestTraceResponse,
    summary="Generate test trace",
    description="Generates a test trace with multiple spans to verify Jaeger integration.",
)
async def generate_test_trace(
    span_count: int = Query(3, ge=1, le=10, description="Number of spans to create"),
    include_error: bool = Query(False, description="Include an error span"),
) -> TestTraceResponse:
    """
    Generate a test trace with multiple spans.

    This endpoint creates a trace with nested spans to verify
    that tracing is working correctly and visible in Jaeger.
    """
    start_time = time.time()
    tracer = get_tracer("ipa.tracing.test")

    with tracer.start_as_current_span(
        "test-trace-root",
        kind=SpanKind.SERVER,
        attributes={
            "test.generated": True,
            "test.timestamp": datetime.utcnow().isoformat(),
            "test.span_count": span_count,
        },
    ) as root_span:
        trace_id = get_trace_id()

        # Create child spans
        for i in range(span_count):
            with tracer.start_as_current_span(
                f"test-span-{i+1}",
                kind=SpanKind.INTERNAL,
                attributes={
                    "test.span_index": i + 1,
                    "test.operation": f"operation-{i+1}",
                },
            ) as span:
                # Simulate some work
                await asyncio.sleep(0.05)
                add_span_event(f"completed-step-{i+1}", {"step": i + 1})

        # Optionally create an error span
        if include_error:
            with tracer.start_as_current_span(
                "test-error-span",
                kind=SpanKind.INTERNAL,
            ) as error_span:
                error_span.set_status(StatusCode.ERROR, "Test error for demonstration")
                error_span.add_event("error", {"error.message": "Simulated error"})

    duration_ms = (time.time() - start_time) * 1000

    return TestTraceResponse(
        trace_id=trace_id or "unknown",
        span_count=span_count + (1 if include_error else 0) + 1,  # +1 for root
        duration_ms=round(duration_ms, 2),
        message=f"Test trace generated successfully. View in Jaeger UI.",
    )


@router.post(
    "/test/detailed",
    response_model=DetailedTraceResponse,
    summary="Generate detailed test trace",
    description="Generates a test trace and returns detailed span information.",
)
async def generate_detailed_test_trace(
    simulate_db: bool = Query(True, description="Simulate database operations"),
    simulate_external: bool = Query(True, description="Simulate external API calls"),
    simulate_cache: bool = Query(True, description="Simulate cache operations"),
) -> DetailedTraceResponse:
    """
    Generate a detailed test trace simulating real operations.

    Creates spans that simulate:
    - Database queries
    - External API calls
    - Cache operations
    """
    start_time = time.time()
    tracer = get_tracer("ipa.tracing.test")
    spans_info = []

    with tracer.start_as_current_span(
        "workflow-execution",
        kind=SpanKind.SERVER,
        attributes={
            "workflow.id": "test-workflow-001",
            "workflow.name": "Test Workflow",
        },
    ) as root_span:
        trace_id = get_trace_id()
        root_start = time.time()

        # Simulate database operation
        if simulate_db:
            with tracer.start_as_current_span(
                "database.query",
                kind=SpanKind.CLIENT,
                attributes={
                    "db.system": "postgresql",
                    "db.operation": "SELECT",
                    "db.statement": "SELECT * FROM workflows WHERE id = $1",
                },
            ) as db_span:
                db_start = time.time()
                await asyncio.sleep(0.02)
                add_span_event("query.executed", {"rows_returned": 1})
                spans_info.append(SpanInfo(
                    name="database.query",
                    kind="CLIENT",
                    duration_ms=round((time.time() - db_start) * 1000, 2),
                    attributes={"db.system": "postgresql", "db.operation": "SELECT"},
                ))

        # Simulate external API call
        if simulate_external:
            with tracer.start_as_current_span(
                "http.request",
                kind=SpanKind.CLIENT,
                attributes={
                    "http.method": "POST",
                    "http.url": "https://api.example.com/process",
                    "http.target": "/process",
                },
            ) as http_span:
                http_start = time.time()
                await asyncio.sleep(0.05)
                http_span.set_attribute("http.status_code", 200)
                add_span_event("response.received", {"status_code": 200})
                spans_info.append(SpanInfo(
                    name="http.request",
                    kind="CLIENT",
                    duration_ms=round((time.time() - http_start) * 1000, 2),
                    attributes={"http.method": "POST", "http.status_code": 200},
                ))

        # Simulate cache operation
        if simulate_cache:
            with tracer.start_as_current_span(
                "cache.get",
                kind=SpanKind.CLIENT,
                attributes={
                    "cache.system": "redis",
                    "cache.operation": "GET",
                    "cache.key": "workflow:test-001:state",
                },
            ) as cache_span:
                cache_start = time.time()
                await asyncio.sleep(0.005)
                cache_span.set_attribute("cache.hit", True)
                add_span_event("cache.hit", {"key": "workflow:test-001:state"})
                spans_info.append(SpanInfo(
                    name="cache.get",
                    kind="CLIENT",
                    duration_ms=round((time.time() - cache_start) * 1000, 2),
                    attributes={"cache.system": "redis", "cache.hit": True},
                ))

        # Add root span info
        spans_info.insert(0, SpanInfo(
            name="workflow-execution",
            kind="SERVER",
            duration_ms=round((time.time() - root_start) * 1000, 2),
            attributes={"workflow.id": "test-workflow-001"},
        ))

    total_duration = (time.time() - start_time) * 1000

    # Build Jaeger UI URL if available
    jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
    jaeger_ui_url = None
    if trace_id:
        jaeger_ui_url = f"http://{jaeger_host}:16686/trace/{trace_id}"

    return DetailedTraceResponse(
        trace_id=trace_id or "unknown",
        spans=spans_info,
        total_duration_ms=round(total_duration, 2),
        jaeger_ui_url=jaeger_ui_url,
    )


@router.get(
    "/health",
    response_model=JaegerHealthResponse,
    summary="Check Jaeger health",
    description="Checks if Jaeger is reachable and returns connection status.",
)
async def check_jaeger_health() -> JaegerHealthResponse:
    """Check Jaeger connectivity."""
    jaeger_enabled = os.getenv("JAEGER_ENABLED", "false").lower() == "true"
    jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not jaeger_enabled and not otlp_endpoint:
        return JaegerHealthResponse(
            status="disabled",
            ui_url=None,
            collector_endpoint=None,
            message="Jaeger tracing is not enabled. Set JAEGER_ENABLED=true to enable.",
        )

    ui_url = f"http://{jaeger_host}:16686"

    # Try to check Jaeger health (simple connectivity check)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ui_url}/api/services")
            if response.status_code == 200:
                return JaegerHealthResponse(
                    status="healthy",
                    ui_url=ui_url,
                    collector_endpoint=otlp_endpoint or f"http://{jaeger_host}:4317",
                    message="Jaeger is reachable and accepting traces.",
                )
    except Exception as e:
        return JaegerHealthResponse(
            status="unhealthy",
            ui_url=ui_url,
            collector_endpoint=otlp_endpoint or f"http://{jaeger_host}:4317",
            message=f"Cannot reach Jaeger: {str(e)}. Check if Jaeger is running.",
        )

    return JaegerHealthResponse(
        status="unknown",
        ui_url=ui_url,
        collector_endpoint=otlp_endpoint,
        message="Could not determine Jaeger status.",
    )


@router.get(
    "/services",
    summary="List traced services",
    description="Returns list of services sending traces to Jaeger.",
)
async def list_traced_services() -> Dict[str, Any]:
    """
    List services registered in Jaeger.

    Note: This requires Jaeger to be running and accessible.
    """
    jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
    ui_url = f"http://{jaeger_host}:16686"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ui_url}/api/services")
            if response.status_code == 200:
                data = response.json()
                services = data.get("data", [])
                return {
                    "status": "ok",
                    "services": services,
                    "count": len(services),
                    "jaeger_ui": ui_url,
                }
    except Exception as e:
        return {
            "status": "error",
            "services": [],
            "count": 0,
            "message": f"Cannot fetch services: {str(e)}",
        }

    return {
        "status": "unknown",
        "services": [],
        "count": 0,
        "message": "Could not determine services.",
    }
