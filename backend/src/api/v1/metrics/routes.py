"""
Business Metrics API Routes

Sprint 3 - Story S3-7: Custom Business Metrics

Provides endpoints for:
- Business metrics summary
- Active user statistics
- LLM cost tracking
- Workflow execution statistics
- Prometheus-format metrics export
"""
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.core.telemetry import get_metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


# ========================================
# Response Models
# ========================================

class ActiveUserResponse(BaseModel):
    """Active user information."""
    user_id: str
    last_active: str
    action_count: int


class ActiveUsersResponse(BaseModel):
    """Response model for active users."""
    count: int = Field(description="Number of active users")
    window_minutes: int = Field(description="Time window in minutes")
    users: List[ActiveUserResponse] = Field(description="Active user details")


class LLMUsageResponse(BaseModel):
    """LLM usage statistics."""
    total_calls: int = Field(default=0, description="Total LLM API calls")
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    by_model: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Breakdown by model")


class WorkflowStatsResponse(BaseModel):
    """Workflow execution statistics."""
    total_created: int = Field(default=0, description="Total workflows created")
    total_executions: int = Field(default=0, description="Total executions")
    total_failed: int = Field(default=0, description="Total failed executions")
    active_executions: int = Field(default=0, description="Currently active executions")
    avg_duration_seconds: Optional[float] = Field(default=None, description="Average execution duration")


class BusinessMetricsSummaryResponse(BaseModel):
    """Complete business metrics summary."""
    timestamp: str = Field(description="Timestamp of the summary")
    active_users: Dict[str, int] = Field(description="Active user counts")
    workflow_stats: WorkflowStatsResponse = Field(description="Workflow statistics")
    llm_usage: LLMUsageResponse = Field(description="LLM usage statistics")
    webhook_stats: Dict[str, int] = Field(description="Webhook statistics")
    notification_stats: Dict[str, int] = Field(description="Notification statistics")
    api_stats: Dict[str, int] = Field(description="API request statistics")


class MetricHistoryEntry(BaseModel):
    """Single metric history entry."""
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: str


class MetricHistoryResponse(BaseModel):
    """Metric history response."""
    metric_name: Optional[str]
    hours: int
    count: int
    entries: List[MetricHistoryEntry]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    initialized: bool
    tracked_users: int
    history_size: int


# ========================================
# Endpoints
# ========================================

@router.get(
    "/summary",
    response_model=BusinessMetricsSummaryResponse,
    summary="Get business metrics summary",
    description="Returns a complete summary of all business metrics.",
)
async def get_business_metrics_summary() -> BusinessMetricsSummaryResponse:
    """Get complete business metrics summary."""
    metrics_service = get_metrics_service()
    summary = metrics_service.get_business_metrics_summary()

    return BusinessMetricsSummaryResponse(
        timestamp=datetime.utcnow().isoformat(),
        active_users={
            "15_minutes": summary["active_users_15m"],
            "1_hour": summary["active_users_1h"],
            "total_tracked": summary["tracked_users"],
        },
        workflow_stats=WorkflowStatsResponse(
            total_created=0,  # Would need DB query for accurate count
            total_executions=0,
            total_failed=0,
            active_executions=0,
            avg_duration_seconds=None,
        ),
        llm_usage=LLMUsageResponse(
            total_calls=0,
            total_tokens=0,
            total_cost_usd=0.0,
            by_model={},
        ),
        webhook_stats={
            "received": 0,
            "triggered": 0,
        },
        notification_stats={
            "sent": 0,
        },
        api_stats={
            "total_requests": 0,
            "errors": 0,
        },
    )


@router.get(
    "/active-users",
    response_model=ActiveUsersResponse,
    summary="Get active users",
    description="Returns list of active users within a time window.",
)
async def get_active_users(
    minutes: int = Query(15, ge=1, le=1440, description="Time window in minutes"),
) -> ActiveUsersResponse:
    """Get active users within a time window."""
    metrics_service = get_metrics_service()
    users = metrics_service.get_active_users(minutes=minutes)

    return ActiveUsersResponse(
        count=len(users),
        window_minutes=minutes,
        users=[
            ActiveUserResponse(
                user_id=u["user_id"],
                last_active=u["last_active"],
                action_count=u["action_count"],
            )
            for u in users
        ],
    )


@router.get(
    "/history",
    response_model=MetricHistoryResponse,
    summary="Get metric history",
    description="Returns historical metric snapshots.",
)
async def get_metric_history(
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
) -> MetricHistoryResponse:
    """Get metric history."""
    metrics_service = get_metrics_service()
    history = metrics_service.get_metric_history(
        name=metric_name,
        hours=hours,
        limit=limit,
    )

    return MetricHistoryResponse(
        metric_name=metric_name,
        hours=hours,
        count=len(history),
        entries=[
            MetricHistoryEntry(
                name=h["name"],
                value=h["value"],
                labels=h["labels"],
                timestamp=h["timestamp"],
            )
            for h in history
        ],
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Metrics service health check",
    description="Returns health status of the metrics service.",
)
async def get_metrics_health() -> HealthResponse:
    """Get metrics service health."""
    metrics_service = get_metrics_service()
    health = metrics_service.health_check()

    return HealthResponse(**health)


@router.get(
    "/prometheus",
    summary="Prometheus metrics endpoint",
    description="Returns metrics in Prometheus exposition format.",
)
async def get_prometheus_metrics() -> str:
    """
    Get metrics in Prometheus format.

    Note: This endpoint provides a basic implementation.
    For production, use OpenTelemetry Prometheus exporter.
    """
    from fastapi.responses import PlainTextResponse

    metrics_service = get_metrics_service()
    summary = metrics_service.get_business_metrics_summary()

    # Build Prometheus-format output
    lines = [
        "# HELP active_users_count Number of active users",
        "# TYPE active_users_count gauge",
        f'active_users_count{{window="15m"}} {summary["active_users_15m"]}',
        f'active_users_count{{window="1h"}} {summary["active_users_1h"]}',
        "",
        "# HELP tracked_users_total Total number of tracked users",
        "# TYPE tracked_users_total gauge",
        f"tracked_users_total {summary['tracked_users']}",
        "",
        "# HELP metric_history_size Number of metric snapshots in history",
        "# TYPE metric_history_size gauge",
        f"metric_history_size {summary['metric_history_size']}",
    ]

    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.post(
    "/test/workflow",
    summary="Generate test workflow metrics",
    description="Generates test workflow metrics for dashboard testing.",
)
async def generate_test_workflow_metrics(
    workflow_id: str = Query("test-workflow-001", description="Test workflow ID"),
    duration_seconds: float = Query(5.0, description="Execution duration"),
    status: str = Query("completed", description="Execution status"),
) -> Dict[str, Any]:
    """Generate test workflow metrics."""
    metrics_service = get_metrics_service()

    # Record workflow creation
    metrics_service.record_workflow_created(
        workflow_id=workflow_id,
        created_by="test-user",
        workflow_type="test",
    )

    # Record execution start
    metrics_service.record_execution_start(
        workflow_id=workflow_id,
        triggered_by="test",
    )

    # Record execution complete
    metrics_service.record_execution_complete(
        workflow_id=workflow_id,
        duration_seconds=duration_seconds,
        status=status,
        error_type="test_error" if status == "failed" else None,
    )

    return {
        "status": "ok",
        "message": f"Test workflow metrics generated",
        "workflow_id": workflow_id,
        "duration_seconds": duration_seconds,
        "execution_status": status,
    }


@router.post(
    "/test/llm",
    summary="Generate test LLM metrics",
    description="Generates test LLM usage metrics for dashboard testing.",
)
async def generate_test_llm_metrics(
    model: str = Query("gpt-4", description="LLM model name"),
    tokens: int = Query(1000, description="Tokens used"),
    cost: float = Query(0.03, description="Cost in USD"),
    duration_seconds: float = Query(2.5, description="Request duration"),
) -> Dict[str, Any]:
    """Generate test LLM metrics."""
    metrics_service = get_metrics_service()

    metrics_service.record_llm_call(
        model=model,
        tokens_used=tokens,
        duration_seconds=duration_seconds,
        cost=cost,
        status="success",
    )

    return {
        "status": "ok",
        "message": f"Test LLM metrics generated",
        "model": model,
        "tokens": tokens,
        "cost_usd": cost,
        "duration_seconds": duration_seconds,
    }


@router.post(
    "/test/user-activity",
    summary="Generate test user activity",
    description="Generates test user activity metrics for dashboard testing.",
)
async def generate_test_user_activity(
    user_id: str = Query("test-user-001", description="Test user ID"),
    action: str = Query("workflow.view", description="Action type"),
    count: int = Query(1, ge=1, le=100, description="Number of actions to generate"),
) -> Dict[str, Any]:
    """Generate test user activity metrics."""
    metrics_service = get_metrics_service()

    for _ in range(count):
        metrics_service.record_user_activity(
            user_id=user_id,
            action=action,
        )

    return {
        "status": "ok",
        "message": f"Test user activity generated",
        "user_id": user_id,
        "action": action,
        "count": count,
        "active_users_15m": metrics_service.get_active_users_count(15),
    }


@router.get(
    "/available",
    summary="List available metrics",
    description="Returns list of all available business metrics.",
)
async def list_available_metrics() -> Dict[str, Any]:
    """List all available metrics."""
    metrics_service = get_metrics_service()
    summary = metrics_service.get_business_metrics_summary()

    return {
        "metrics": summary["metrics_available"],
        "count": len(summary["metrics_available"]),
        "categories": {
            "workflow": [
                "workflow_executions_total",
                "workflow_created_total",
                "workflow_failed_total",
                "workflow_execution_duration_seconds",
            ],
            "llm": [
                "llm_api_calls_total",
                "llm_tokens_used_total",
                "llm_cost_total",
            ],
            "checkpoint": [
                "checkpoint_requests_total",
                "checkpoint_wait_time_seconds",
            ],
            "webhook": [
                "webhooks_received_total",
                "webhooks_triggered_total",
            ],
            "notification": [
                "notifications_sent_total",
            ],
            "user": [
                "user_actions_total",
                "user_logins_total",
                "active_users_count",
            ],
            "api": [
                "api_requests_total",
                "api_errors_total",
            ],
        },
    }
