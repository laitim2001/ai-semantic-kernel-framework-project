"""
Admin Dashboard Service

Sprint 2 - Story S2-8: Admin Dashboard APIs

Provides business logic for admin dashboard functionality.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, case, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

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

logger = logging.getLogger(__name__)


class AdminDashboardService:
    """Service for admin dashboard operations.

    Provides statistics, metrics, and activity data for the admin dashboard.

    Example:
        service = AdminDashboardService(db)
        overview = await service.get_overview_statistics()
    """

    def __init__(self, db: AsyncSession):
        """Initialize AdminDashboardService.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_overview_statistics(self) -> OverviewResponse:
        """Get overview statistics for dashboard.

        Returns:
            OverviewResponse with workflow, execution, and user stats
        """
        from src.infrastructure.database.models.workflow import Workflow, WorkflowStatus
        from src.infrastructure.database.models.execution import Execution, ExecutionStatus
        from src.infrastructure.database.models.user import User

        # Workflow statistics
        workflow_result = await self.db.execute(
            select(
                func.count(Workflow.id).label("total"),
                func.sum(case((Workflow.status == WorkflowStatus.ACTIVE, 1), else_=0)).label("active"),
                func.sum(case((Workflow.status == WorkflowStatus.DRAFT, 1), else_=0)).label("draft"),
                func.sum(case((Workflow.status == WorkflowStatus.ARCHIVED, 1), else_=0)).label("archived"),
            )
        )
        wf_row = workflow_result.first()
        workflow_stats = WorkflowStats(
            total=wf_row.total or 0,
            active=wf_row.active or 0,
            draft=wf_row.draft or 0,
            archived=wf_row.archived or 0,
        )

        # Execution statistics
        today = datetime.now(timezone.utc).date()
        exec_result = await self.db.execute(
            select(
                func.count(Execution.id).label("total"),
                func.sum(case((Execution.status == ExecutionStatus.COMPLETED, 1), else_=0)).label("successful"),
                func.sum(case((Execution.status == ExecutionStatus.FAILED, 1), else_=0)).label("failed"),
                func.sum(case((Execution.status == ExecutionStatus.RUNNING, 1), else_=0)).label("running"),
                func.sum(case((Execution.status == ExecutionStatus.PENDING, 1), else_=0)).label("pending"),
            )
        )
        exec_row = exec_result.first()

        # Today's executions
        today_result = await self.db.execute(
            select(func.count(Execution.id)).where(
                func.date(Execution.created_at) == today
            )
        )
        today_count = today_result.scalar() or 0

        total_exec = exec_row.total or 0
        successful = exec_row.successful or 0
        success_rate = (successful / total_exec * 100) if total_exec > 0 else 0.0

        execution_stats = ExecutionStats(
            total=total_exec,
            successful=successful,
            failed=exec_row.failed or 0,
            running=exec_row.running or 0,
            pending=exec_row.pending or 0,
            today=today_count,
            success_rate=round(success_rate, 2),
        )

        # User statistics
        user_result = await self.db.execute(
            select(
                func.count(User.id).label("total"),
                func.sum(case((User.is_active == True, 1), else_=0)).label("active"),
                func.sum(case((User.is_superuser == True, 1), else_=0)).label("admins"),
            )
        )
        user_row = user_result.first()
        user_stats = UserStats(
            total=user_row.total or 0,
            active=user_row.active or 0,
            admins=user_row.admins or 0,
        )

        return OverviewResponse(
            workflows=workflow_stats,
            executions=execution_stats,
            users=user_stats,
            last_updated=datetime.now(timezone.utc),
        )

    async def get_execution_trend(self, days: int = 7) -> TrendResponse:
        """Get execution trend data for the specified period.

        Args:
            days: Number of days to include (default 7)

        Returns:
            TrendResponse with daily execution data
        """
        from src.infrastructure.database.models.execution import Execution, ExecutionStatus

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date(Execution.created_at).label("date"),
                func.count(Execution.id).label("total"),
                func.sum(case((Execution.status == ExecutionStatus.COMPLETED, 1), else_=0)).label("successful"),
                func.sum(case((Execution.status == ExecutionStatus.FAILED, 1), else_=0)).label("failed"),
            )
            .where(Execution.created_at >= start_date)
            .group_by(func.date(Execution.created_at))
            .order_by(func.date(Execution.created_at))
        )

        rows = result.all()
        data = [
            TrendDataPoint(
                date=str(row.date),
                total=row.total or 0,
                successful=row.successful or 0,
                failed=row.failed or 0,
            )
            for row in rows
        ]

        return TrendResponse(
            period=f"Last {days} days",
            data=data,
        )

    async def get_realtime_metrics(self) -> RealtimeMetrics:
        """Get real-time system metrics.

        Returns:
            RealtimeMetrics with current system state
        """
        from src.infrastructure.database.models.execution import Execution, ExecutionStatus
        from src.infrastructure.database.models.checkpoint import Checkpoint, CheckpointStatus

        # Running executions
        running_result = await self.db.execute(
            select(Execution)
            .where(Execution.status == ExecutionStatus.RUNNING)
            .limit(10)
        )
        running_rows = running_result.scalars().all()

        now = datetime.now(timezone.utc)
        running_executions = []
        for exec in running_rows:
            started = exec.started_at or exec.created_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            duration = (now - started).total_seconds()

            running_executions.append(RunningExecution(
                execution_id=str(exec.id),
                workflow_id=str(exec.workflow_id),
                workflow_name=None,  # Would need join for name
                status=exec.status.value,
                started_at=started,
                duration_seconds=duration,
                current_step=exec.current_step_index,
                total_steps=None,
            ))

        # Pending count
        pending_result = await self.db.execute(
            select(func.count(Execution.id))
            .where(Execution.status == ExecutionStatus.PENDING)
        )
        pending_count = pending_result.scalar() or 0

        # Recent executions (last 5 minutes)
        five_min_ago = now - timedelta(minutes=5)
        recent_result = await self.db.execute(
            select(func.count(Execution.id))
            .where(Execution.created_at >= five_min_ago)
        )
        recent_count = recent_result.scalar() or 0

        # Average duration (last hour, completed only)
        one_hour_ago = now - timedelta(hours=1)
        avg_result = await self.db.execute(
            select(func.avg(Execution.duration_ms) / 1000.0)
            .where(
                and_(
                    Execution.status == ExecutionStatus.COMPLETED,
                    Execution.completed_at >= one_hour_ago,
                )
            )
        )
        avg_duration = avg_result.scalar()

        # Active checkpoints
        checkpoint_result = await self.db.execute(
            select(func.count(Checkpoint.id))
            .where(Checkpoint.status == CheckpointStatus.PENDING)
        )
        active_checkpoints = checkpoint_result.scalar() or 0

        return RealtimeMetrics(
            running_executions=running_executions,
            running_count=len(running_executions),
            pending_count=pending_count,
            recent_executions_5min=recent_count,
            avg_duration_seconds=round(avg_duration, 2) if avg_duration else None,
            queue_depth=0,  # Would need RabbitMQ integration
            active_checkpoints=active_checkpoints,
        )

    async def get_system_status(self) -> SystemStatus:
        """Get overall system status.

        Returns:
            SystemStatus with component health
        """
        import os
        import time

        from src.infrastructure.database.session import AsyncSessionLocal

        components = {}
        overall_status = "healthy"

        # Check database
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            components["database"] = "up"
        except Exception as e:
            components["database"] = "down"
            overall_status = "unhealthy"

        # Check Redis
        try:
            import redis.asyncio as redis
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", ""),
                decode_responses=True,
            )
            await r.ping()
            await r.close()
            components["redis"] = "up"
        except Exception:
            components["redis"] = "down"
            if overall_status == "healthy":
                overall_status = "degraded"

        # Check RabbitMQ
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://{os.getenv('RABBITMQ_HOST', 'rabbitmq')}:{os.getenv('RABBITMQ_MANAGEMENT_PORT', '15672')}/api/healthchecks/node",
                    auth=(os.getenv("RABBITMQ_USER", "admin"), os.getenv("RABBITMQ_PASSWORD", "admin")),
                    timeout=5.0,
                )
                components["rabbitmq"] = "up" if resp.status_code == 200 else "degraded"
        except Exception:
            components["rabbitmq"] = "down"

        # Calculate uptime (approximate)
        from src.api.v1.monitoring.routes import _start_time
        uptime = time.time() - _start_time

        return SystemStatus(
            status=overall_status,
            uptime_seconds=uptime,
            version=os.getenv("APP_VERSION", "0.1.0"),
            environment=os.getenv("ENVIRONMENT", "development"),
            components=components,
        )

    async def get_activity_feed(
        self,
        limit: int = 50,
        activity_type: Optional[str] = None,
    ) -> ActivityFeedResponse:
        """Get recent activity feed.

        Args:
            limit: Maximum activities to return
            activity_type: Filter by type (execution, workflow, user, alert)

        Returns:
            ActivityFeedResponse with recent activities
        """
        from src.infrastructure.database.models.audit_log import AuditLog

        query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)

        if activity_type:
            query = query.where(AuditLog.resource_type == activity_type)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        activities = []
        for log in logs:
            action_str = log.action.value if hasattr(log.action, 'value') else str(log.action)
            activities.append(RecentActivity(
                id=str(log.id),
                type=log.resource_type or "unknown",
                action=action_str,
                description=f"{action_str} on {log.resource_type}" + (f" ({log.resource_id})" if log.resource_id else ""),
                timestamp=log.created_at,
                user=str(log.user_id) if log.user_id else None,
            ))

        return ActivityFeedResponse(
            activities=activities,
            total_count=len(activities),
        )
