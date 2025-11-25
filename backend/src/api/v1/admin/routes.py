"""
Admin Dashboard API Routes

Sprint 2 - Story S2-8: Admin Dashboard APIs

Provides endpoints for:
- Dashboard overview statistics
- Execution trends
- Real-time metrics
- System status
- Activity feed
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_session
from src.domain.admin import (
    OverviewResponse,
    TrendResponse,
    RealtimeMetrics,
    SystemStatus,
    ActivityFeedResponse,
    AdminDashboardService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get("/statistics/overview", response_model=OverviewResponse)
async def get_overview_statistics(
    db: AsyncSession = Depends(get_session),
):
    """
    Get dashboard overview statistics.

    Returns aggregated statistics including:
    - Workflow counts (total, active)
    - Execution counts (total, successful, failed, running, today)
    - Success rate percentage
    - User counts (total, active, admins)

    This data is suitable for dashboard cards and summary views.

    Returns:
        OverviewResponse with workflow, execution, and user statistics
    """
    service = AdminDashboardService(db)
    return await service.get_overview_statistics()


@router.get("/statistics/trend", response_model=TrendResponse)
async def get_execution_trend(
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get execution trend data.

    Returns daily execution counts for the specified period.
    Useful for rendering trend charts on the dashboard.

    Args:
        days: Number of days to include (1-90, default 7)

    Returns:
        TrendResponse with daily data points
    """
    service = AdminDashboardService(db)
    return await service.get_execution_trend(days=days)


@router.get("/metrics/realtime", response_model=RealtimeMetrics)
async def get_realtime_metrics(
    db: AsyncSession = Depends(get_session),
):
    """
    Get real-time system metrics.

    Returns current system state including:
    - Running executions with details
    - Pending execution count
    - Recent execution count (last 5 minutes)
    - Average execution duration (last hour)
    - Active checkpoint approvals

    This endpoint should be polled periodically for live dashboards.

    Returns:
        RealtimeMetrics with current system state
    """
    service = AdminDashboardService(db)
    return await service.get_realtime_metrics()


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status(
    db: AsyncSession = Depends(get_session),
):
    """
    Get overall system status.

    Checks health of all system components:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Message Queue (RabbitMQ)

    Returns overall status (healthy, degraded, unhealthy) and
    individual component states.

    Returns:
        SystemStatus with component health
    """
    service = AdminDashboardService(db)
    return await service.get_system_status()


@router.get("/activity/feed", response_model=ActivityFeedResponse)
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200, description="Maximum activities to return"),
    type: Optional[str] = Query(None, description="Filter by type (execution, workflow, user, alert)"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get recent activity feed.

    Returns recent activities from the audit log.
    Useful for activity timeline on the dashboard.

    Args:
        limit: Maximum activities to return (1-200, default 50)
        type: Optional filter by activity type

    Returns:
        ActivityFeedResponse with recent activities
    """
    service = AdminDashboardService(db)
    return await service.get_activity_feed(limit=limit, activity_type=type)


@router.get("/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_session),
):
    """
    Get combined dashboard summary.

    Returns all dashboard data in a single request:
    - Overview statistics
    - 7-day trend
    - Real-time metrics
    - System status
    - Recent activity (last 10)

    Useful for initial dashboard load to minimize API calls.

    Returns:
        Combined dashboard data
    """
    service = AdminDashboardService(db)

    # Fetch all data in parallel would be better, but sequential for simplicity
    overview = await service.get_overview_statistics()
    trend = await service.get_execution_trend(days=7)
    realtime = await service.get_realtime_metrics()
    status = await service.get_system_status()
    activity = await service.get_activity_feed(limit=10)

    return {
        "overview": overview,
        "trend": trend,
        "realtime": realtime,
        "system_status": status,
        "recent_activity": activity,
    }
