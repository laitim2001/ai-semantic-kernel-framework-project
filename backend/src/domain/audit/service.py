"""
Audit Log Service

Provides business logic for audit logging operations.
Sprint 2 - Story S2-7
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from src.infrastructure.database.models.audit_log import AuditAction, AuditLog
from .schemas import (
    AuditLogCreate,
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

    def __init__(self, db: Session):
        """
        Initialize AuditService.

        Args:
            db: SQLAlchemy database session
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
        metadata: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        This is the primary method for logging audit events.
        Should be called from API endpoints and services.

        Args:
            action: The action being logged
            resource_type: Type of resource
            resource_id: UUID of the affected resource
            resource_name: Human-readable name
            user_id: UUID of the user
            actor_type: Type of actor
            changes: Dictionary of changes
            ip_address: Client IP
            user_agent: Client user agent
            request_id: Correlation ID
            metadata: Additional metadata
            error_message: Error message if failed
            duration_ms: Duration in milliseconds

        Returns:
            Created AuditLog instance
        """
        try:
            # Convert string action to enum if needed
            if isinstance(action, str):
                try:
                    action = AuditAction(action)
                except ValueError:
                    logger.warning(f"Unknown audit action: {action}, using as-is")

            audit_log = AuditLog.create_log(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                user_id=user_id,
                actor_type=actor_type,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                metadata=metadata,
                error_message=error_message,
                duration_ms=duration_ms,
            )

            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)

            logger.debug(
                f"Audit log created: action={action}, "
                f"resource={resource_type}/{resource_id}"
            )

            return audit_log

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            self.db.rollback()
            raise

    def log_sync(
        self,
        action: str | AuditAction,
        resource_type: str,
        **kwargs
    ) -> AuditLog:
        """
        Synchronous version of log() for non-async contexts.
        """
        try:
            if isinstance(action, str):
                try:
                    action = AuditAction(action)
                except ValueError:
                    pass

            audit_log = AuditLog.create_log(
                action=action,
                resource_type=resource_type,
                **kwargs
            )

            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)

            return audit_log

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            self.db.rollback()
            raise

    async def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        """
        Get an audit log by ID.

        Args:
            log_id: The audit log ID

        Returns:
            AuditLog instance or None if not found
        """
        return self.db.query(AuditLog).filter(AuditLog.id == log_id).first()

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
        query = self.db.query(AuditLog)

        # Apply filters
        if filters.user_id:
            query = query.filter(AuditLog.user_id == filters.user_id)

        if filters.action:
            try:
                action_enum = AuditAction(filters.action)
                query = query.filter(AuditLog.action == action_enum)
            except ValueError:
                pass

        if filters.resource_type:
            query = query.filter(AuditLog.resource_type == filters.resource_type)

        if filters.resource_id:
            query = query.filter(AuditLog.resource_id == filters.resource_id)

        if filters.actor_type:
            query = query.filter(AuditLog.actor_type == filters.actor_type)

        if filters.request_id:
            query = query.filter(AuditLog.request_id == filters.request_id)

        if filters.start_date:
            query = query.filter(AuditLog.created_at >= filters.start_date)

        if filters.end_date:
            query = query.filter(AuditLog.created_at <= filters.end_date)

        if filters.has_error is not None:
            if filters.has_error:
                query = query.filter(AuditLog.error_message.isnot(None))
            else:
                query = query.filter(AuditLog.error_message.is_(None))

        # Get total count
        total = query.count()

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
        items = query.all()

        # Calculate pagination info
        total_pages = (total + filters.page_size - 1) // filters.page_size

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(item) for item in items],
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

        base_query = self.db.query(AuditLog)

        if user_id:
            base_query = base_query.filter(AuditLog.user_id == user_id)
        if resource_type:
            base_query = base_query.filter(AuditLog.resource_type == resource_type)

        # Total logs
        total_logs = base_query.count()

        # Logs by time period
        logs_today = base_query.filter(AuditLog.created_at >= today_start).count()
        logs_this_week = base_query.filter(AuditLog.created_at >= week_start).count()
        logs_this_month = base_query.filter(AuditLog.created_at >= month_start).count()

        # Top actions
        top_actions = (
            self.db.query(
                AuditLog.action,
                func.count(AuditLog.id).label("count")
            )
            .group_by(AuditLog.action)
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        # Top resources
        top_resources = (
            self.db.query(
                AuditLog.resource_type,
                func.count(AuditLog.id).label("count")
            )
            .group_by(AuditLog.resource_type)
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        # Error stats
        error_count = base_query.filter(AuditLog.error_message.isnot(None)).count()
        error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0

        return AuditLogStats(
            total_logs=total_logs,
            logs_today=logs_today,
            logs_this_week=logs_this_week,
            logs_this_month=logs_this_month,
            top_actions=[
                {"action": str(action.value) if action else "unknown", "count": count}
                for action, count in top_actions
            ],
            top_resources=[
                {"resource_type": resource_type, "count": count}
                for resource_type, count in top_resources
            ],
            error_count=error_count,
            error_rate=round(error_rate, 2),
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
        return (
            self.db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )

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
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )

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
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        deleted = (
            self.db.query(AuditLog)
            .filter(AuditLog.created_at < cutoff_date)
            .delete(synchronize_session=False)
        )

        self.db.commit()

        logger.info(f"Cleaned up {deleted} audit logs older than {retention_days} days")

        return deleted


# Convenience function for quick logging
def log_audit(
    db: Session,
    action: str | AuditAction,
    resource_type: str,
    **kwargs
) -> AuditLog:
    """
    Convenience function for synchronous audit logging.

    Usage:
        from src.domain.audit.service import log_audit
        log_audit(db, "CREATE", "workflow", resource_id=workflow.id, user_id=user.id)
    """
    service = AuditService(db)
    return service.log_sync(action, resource_type, **kwargs)
