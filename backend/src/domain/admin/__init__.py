"""
Admin Domain Module

Sprint 2 - Story S2-8: Admin Dashboard APIs
"""
from .schemas import (
    WorkflowStats,
    ExecutionStats,
    UserStats,
    OverviewResponse,
    TrendDataPoint,
    TrendResponse,
    RunningExecution,
    RealtimeMetrics,
    SystemStatus,
    RecentActivity,
    ActivityFeedResponse,
)
from .service import AdminDashboardService

__all__ = [
    "WorkflowStats",
    "ExecutionStats",
    "UserStats",
    "OverviewResponse",
    "TrendDataPoint",
    "TrendResponse",
    "RunningExecution",
    "RealtimeMetrics",
    "SystemStatus",
    "RecentActivity",
    "ActivityFeedResponse",
    "AdminDashboardService",
]
