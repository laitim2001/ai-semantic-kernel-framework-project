"""
Audit Log Service

Provides business logic for audit logging operations.
Sprint 2 - Story S2-7

Note: This service is designed to work with the current audit_logs table schema.
Some filtering options are disabled until the schema is updated.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.audit_log import AuditAction, AuditLog
from .schemas import (
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogStats,
)

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service class for audit log operations.

    Provides methods to:
    - Create audit log entries
    - Query and filter audit logs
    - Generate audit statistics
    - Export audit logs
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize AuditService.

        Args:
            db: SQLAlchemy async database session
        """
        self.db = db

    async def log(
        self,
        action: str | AuditAction,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        resource_name: Optional[str] = None,
        user_id: Optional[UUID] = None,
        actor_type: str = "user",
        changes: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        This is the primary method for logging audit events.
        Should be called from API endpoints and services.

        Note: Some parameters are accepted for API compatibility but not stored
        in the current database schema (resource_name, actor_type, request_id, etc.)

        Args:
            action: The action being logged
            resource_type: Type of resource
            resource_id: UUID of the affected resource
            resource_name: Human-readable name (not stored in current schema)
            user_id: UUID of the user
            actor_type: Type of actor (not stored in current schema)
            changes: Dictionary of changes
            ip_address: Client IP
            user_agent: Client user agent
            request_id: Correlation ID (not stored in current schema)
            extra_data: Additional metadata (not stored in current schema)
            error_message: Error message if failed (not stored in current schema)
            duration_ms: Duration in milliseconds (not stored in current schema)

        Returns:
            Created AuditLog instance
        """
        try:
            # Convert string action to enum if needed
            if isinstance(action, str):
                try:
                    action = AuditAction(action)
                except ValueError:
                    logger.warning(f"Unknown audit action: {action}, using CREATE as default")
                    action = AuditAction.CREATE

            audit_log = AuditLog.create_log(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self.db.add(audit_log)
            await self.db.flush()
            await self.db.refresh(audit_log)

            logger.debug(
                f"Audit log created: action={action}, "
                f"resource={resource_type}/{resource_id}"
            )

            return audit_log

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            await self.db.rollback()
            raise

    async def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        """
        Get an audit log by ID.

        Args:
            log_id: The audit log ID

        Returns:
            AuditLog instance or None if not found
        """
        result = await self.db.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: AuditLogFilter
    ) -> AuditLogListResponse:
        """
        List audit logs with filtering and pagination.

        Args:
            filters: Filter and pagination parameters

        Returns:
            Paginated list of audit logs
        """
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        # Apply filters (only for columns that exist in the schema)
        conditions = []

        if filters.user_id:
            conditions.append(AuditLog.user_id == filters.user_id)

        if filters.action:
            try:
                action_enum = AuditAction(filters.action)
                conditions.append(AuditLog.action == action_enum)
            except ValueError:
                pass

        if filters.resource_type:
            conditions.append(AuditLog.resource_type == filters.resource_type)

        if filters.resource_id:
            conditions.append(AuditLog.resource_id == filters.resource_id)

        # Note: actor_type, request_id, has_error filters are disabled
        # because these columns don't exist in the current schema

        if filters.start_date:
            conditions.append(AuditLog.created_at >= filters.start_date)

        if filters.end_date:
            conditions.append(AuditLog.created_at <= filters.end_date)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(AuditLog, filters.sort_by, AuditLog.created_at)
        if filters.sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        # Execute query
        result = await self.db.execute(query)
        items = result.scalars().all()

        # Calculate pagination info
        total_pages = (total + filters.page_size - 1) // filters.page_size if total > 0 else 1

        # Convert items to response format
        response_items = []
        for item in items:
            response_items.append(AuditLogResponse(
                id=item.id,
                user_id=item.user_id,
                actor_type="user",  # Default
                action=item.action.value if item.action else "UNKNOWN",
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                resource_name=None,
                changes=item.changes,
                ip_address=str(item.ip_address) if item.ip_address else None,
                user_agent=item.user_agent,
                request_id=None,
                metadata=None,
                error_message=None,
                duration_ms=None,
                created_at=item.created_at,
            ))

        return AuditLogListResponse(
            items=response_items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_previous=filters.page > 1,
        )

    async def get_stats(
        self,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None
    ) -> AuditLogStats:
        """
        Get audit log statistics.

        Args:
            user_id: Optional filter by user
            resource_type: Optional filter by resource type

        Returns:
            Audit statistics
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        # Build base conditions
        base_conditions = []
        if user_id:
            base_conditions.append(AuditLog.user_id == user_id)
        if resource_type:
            base_conditions.append(AuditLog.resource_type == resource_type)

        # Total logs
        total_query = select(func.count(AuditLog.id))
        if base_conditions:
            total_query = total_query.where(and_(*base_conditions))
        total_result = await self.db.execute(total_query)
        total_logs = total_result.scalar() or 0

        # Logs today
        today_query = select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= today_start
        )
        if base_conditions:
            today_query = today_query.where(and_(*base_conditions))
        today_result = await self.db.execute(today_query)
        logs_today = today_result.scalar() or 0

        # Logs this week
        week_query = select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= week_start
        )
        if base_conditions:
            week_query = week_query.where(and_(*base_conditions))
        week_result = await self.db.execute(week_query)
        logs_this_week = week_result.scalar() or 0

        # Logs this month
        month_query = select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= month_start
        )
        if base_conditions:
            month_query = month_query.where(and_(*base_conditions))
        month_result = await self.db.execute(month_query)
        logs_this_month = month_result.scalar() or 0

        # Top actions
        top_actions_query = (
            select(
                AuditLog.action,
                func.count(AuditLog.id).label("count")
            )
            .group_by(AuditLog.action)
            .order_by(desc("count"))
            .limit(10)
        )
        top_actions_result = await self.db.execute(top_actions_query)
        top_actions = [
            {"action": str(action.value) if action else "unknown", "count": count}
            for action, count in top_actions_result.all()
        ]

        # Top resources
        top_resources_query = (
            select(
                AuditLog.resource_type,
                func.count(AuditLog.id).label("count")
            )
            .group_by(AuditLog.resource_type)
            .order_by(desc("count"))
            .limit(10)
        )
        top_resources_result = await self.db.execute(top_resources_query)
        top_resources = [
            {"resource_type": res_type, "count": count}
            for res_type, count in top_resources_result.all()
        ]

        # Error stats - currently 0 since error_message column doesn't exist
        error_count = 0
        error_rate = 0.0

        return AuditLogStats(
            total_logs=total_logs,
            logs_today=logs_today,
            logs_this_week=logs_this_week,
            logs_this_month=logs_this_month,
            top_actions=top_actions,
            top_resources=top_resources,
            error_count=error_count,
            error_rate=error_rate,
        )

    async def get_for_resource(
        self,
        resource_type: str,
        resource_id: UUID,
        limit: int = 100
    ) -> list[AuditLog]:
        """
        Get audit logs for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: UUID of the resource
            limit: Maximum number of logs to return

        Returns:
            List of audit logs
        """
        result = await self.db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_for_user(
        self,
        user_id: UUID,
        limit: int = 100
    ) -> list[AuditLog]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: UUID of the user
            limit: Maximum number of logs to return

        Returns:
            List of audit logs
        """
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_logs(
        self,
        retention_days: int = 90
    ) -> int:
        """
        Delete audit logs older than retention period.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of deleted logs
        """
        from sqlalchemy import delete

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Count before delete
        count_query = select(func.count(AuditLog.id)).where(
            AuditLog.created_at < cutoff_date
        )
        count_result = await self.db.execute(count_query)
        count_to_delete = count_result.scalar() or 0

        # Delete old logs
        delete_query = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        await self.db.execute(delete_query)
        await self.db.flush()

        logger.info(f"Cleaned up {count_to_delete} audit logs older than {retention_days} days")

        return count_to_delete
