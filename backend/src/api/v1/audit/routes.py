"""
Audit Log API Routes

Provides REST API endpoints for audit log operations.
Sprint 2 - Story S2-7

Endpoints:
- GET  /api/v1/audit/logs         - List audit logs with filtering
- GET  /api/v1/audit/logs/{id}    - Get a specific audit log
- GET  /api/v1/audit/stats        - Get audit statistics
- GET  /api/v1/audit/resource/{resource_type}/{resource_id} - Get logs for a resource
- POST /api/v1/audit/export       - Export audit logs
"""
import csv
import io
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.domain.audit.schemas import (
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogStats,
    AuditLogExportRequest,
)
from src.domain.audit.service import AuditService
from src.infrastructure.database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[UUID] = Query(None, description="Filter by resource ID"),
    actor_type: Optional[str] = Query(None, description="Filter by actor type"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    start_date: Optional[datetime] = Query(None, description="Filter logs after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter logs before this date"),
    has_error: Optional[bool] = Query(None, description="Filter by error presence"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
):
    """
    List audit logs with filtering and pagination.

    Returns a paginated list of audit logs that can be filtered by various criteria.
    """
    filters = AuditLogFilter(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_type=actor_type,
        request_id=request_id,
        start_date=start_date,
        end_date=end_date,
        has_error=has_error,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    service = AuditService(db)
    result = await service.list(filters)

    logger.debug(f"Listed {len(result.items)} audit logs (page {page})")
    return result


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific audit log by ID.
    """
    service = AuditService(db)
    log = await service.get_by_id(log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return AuditLogResponse.model_validate(log)


@router.get("/stats", response_model=AuditLogStats)
async def get_audit_stats(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    db: Session = Depends(get_db),
):
    """
    Get audit log statistics.

    Returns aggregate statistics about audit logs including:
    - Total count and counts by time period
    - Top actions and resources
    - Error rate
    """
    service = AuditService(db)
    stats = await service.get_stats(user_id=user_id, resource_type=resource_type)

    return stats


@router.get("/resource/{resource_type}/{resource_id}")
async def get_logs_for_resource(
    resource_type: str,
    resource_id: UUID,
    limit: int = Query(100, ge=1, le=500, description="Maximum logs to return"),
    db: Session = Depends(get_db),
):
    """
    Get audit logs for a specific resource.

    Useful for viewing the history of a workflow, execution, or other entity.
    """
    service = AuditService(db)
    logs = await service.get_for_resource(resource_type, resource_id, limit)

    return {
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "count": len(logs),
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
    }


@router.get("/user/{user_id}")
async def get_logs_for_user(
    user_id: UUID,
    limit: int = Query(100, ge=1, le=500, description="Maximum logs to return"),
    db: Session = Depends(get_db),
):
    """
    Get audit logs for a specific user.

    Useful for viewing all actions performed by a user.
    """
    service = AuditService(db)
    logs = await service.get_for_user(user_id, limit)

    return {
        "user_id": str(user_id),
        "count": len(logs),
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
    }


@router.post("/export")
async def export_audit_logs(
    export_request: AuditLogExportRequest,
    db: Session = Depends(get_db),
):
    """
    Export audit logs to CSV or JSON format.

    Exports logs within the specified date range.
    """
    service = AuditService(db)

    # Build filters
    filters = AuditLogFilter(
        start_date=export_request.start_date,
        end_date=export_request.end_date,
        page=1,
        page_size=10000,  # Max export size
    )

    result = await service.list(filters)

    if export_request.format.lower() == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        headers = [
            "id", "created_at", "action", "resource_type", "resource_id",
            "resource_name", "user_id", "actor_type", "ip_address",
            "request_id", "error_message", "duration_ms"
        ]
        if export_request.include_metadata:
            headers.append("metadata")
        writer.writerow(headers)

        # Data rows
        for log in result.items:
            row = [
                log.id,
                log.created_at.isoformat(),
                log.action,
                log.resource_type,
                str(log.resource_id) if log.resource_id else "",
                log.resource_name or "",
                str(log.user_id) if log.user_id else "",
                log.actor_type or "",
                log.ip_address or "",
                log.request_id or "",
                log.error_message or "",
                log.duration_ms or "",
            ]
            if export_request.include_metadata:
                row.append(json.dumps(log.metadata) if log.metadata else "")
            writer.writerow(row)

        output.seek(0)

        filename = f"audit_logs_{export_request.start_date.date()}_{export_request.end_date.date()}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    else:
        # Generate JSON
        data = {
            "export_date": datetime.utcnow().isoformat(),
            "start_date": export_request.start_date.isoformat(),
            "end_date": export_request.end_date.isoformat(),
            "total_logs": result.total,
            "logs": [log.model_dump() for log in result.items]
        }

        filename = f"audit_logs_{export_request.start_date.date()}_{export_request.end_date.date()}.json"

        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.post("/cleanup")
async def cleanup_old_logs(
    retention_days: int = Query(90, ge=30, le=365, description="Days to retain"),
    db: Session = Depends(get_db),
):
    """
    Clean up old audit logs.

    Deletes logs older than the specified retention period.
    This is typically called by a scheduled job.

    NOTE: This is an admin-only operation. In production, this
    should be protected by appropriate authorization.
    """
    service = AuditService(db)
    deleted_count = await service.cleanup_old_logs(retention_days)

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "retention_days": retention_days,
    }
