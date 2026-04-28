# =============================================================================
# IPA Platform - Audit API Routes
# =============================================================================
# Sprint 3: 集成 & 可靠性 - 審計日誌系統
#
# REST API endpoints for Audit log management:
#   - GET /audit/logs - 查詢審計日誌
#   - GET /audit/logs/{id} - 獲取單個條目
#   - GET /audit/executions/{id}/trail - 執行軌跡
#   - GET /audit/statistics - 統計信息
#   - GET /audit/export - 導出報告
#   - GET /audit/actions - 動作類型列表
#   - GET /audit/resources - 資源類型列表
# =============================================================================

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from src.api.v1.audit.schemas import (
    ActionListResponse,
    AuditEntryResponse,
    AuditListResponse,
    AuditStatisticsResponse,
    AuditTrailResponse,
    ExportResponse,
    ResourceListResponse,
)
from src.domain.audit.logger import (
    AuditAction,
    AuditLogger,
    AuditQueryParams,
    AuditResource,
    AuditSeverity,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    responses={
        500: {"description": "Internal server error"},
    },
)


# =============================================================================
# Dependency Injection
# =============================================================================

# Global logger instance (in production, use proper DI)
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger."""
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger()

    return _audit_logger


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get(
    "/logs",
    response_model=AuditListResponse,
    summary="查詢審計日誌",
    description="獲取審計日誌列表，支持多條件過濾",
)
async def list_audit_logs(
    action: Optional[str] = Query(None, description="動作類型過濾"),
    resource: Optional[str] = Query(None, description="資源類型過濾"),
    actor_id: Optional[str] = Query(None, description="操作者 ID 過濾"),
    resource_id: Optional[str] = Query(None, description="資源 ID 過濾"),
    execution_id: Optional[UUID] = Query(None, description="執行 ID 過濾"),
    workflow_id: Optional[UUID] = Query(None, description="工作流 ID 過濾"),
    severity: Optional[str] = Query(None, description="嚴重程度過濾"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量"),
    offset: int = Query(0, ge=0, description="跳過數量"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> AuditListResponse:
    """查詢審計日誌."""
    # 解析動作類型
    actions = None
    if action:
        try:
            actions = [AuditAction(action)]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}",
            )

    # 解析資源類型
    resources = None
    if resource:
        try:
            resources = [AuditResource(resource)]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource: {resource}",
            )

    # 解析嚴重程度
    severity_filter = None
    if severity:
        try:
            severity_filter = AuditSeverity(severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity: {severity}",
            )

    params = AuditQueryParams(
        actions=actions,
        resources=resources,
        actor_id=actor_id,
        resource_id=resource_id,
        execution_id=execution_id,
        workflow_id=workflow_id,
        severity=severity_filter,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    entries = audit_logger.query(params)
    total = audit_logger.count(params)

    return AuditListResponse(
        items=[
            AuditEntryResponse(
                id=e.id,
                action=e.action.value,
                resource=e.resource.value,
                resource_id=e.resource_id,
                actor_id=e.actor_id,
                actor_name=e.actor_name,
                timestamp=e.timestamp,
                severity=e.severity.value,
                message=e.message,
                details=e.details,
                metadata=e.metadata,
                ip_address=e.ip_address,
                user_agent=e.user_agent,
                execution_id=e.execution_id,
                workflow_id=e.workflow_id,
            )
            for e in entries
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/logs/{entry_id}",
    response_model=AuditEntryResponse,
    summary="獲取審計條目",
    description="獲取指定 ID 的審計條目",
)
async def get_audit_entry(
    entry_id: UUID,
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> AuditEntryResponse:
    """獲取單個審計條目."""
    entry = audit_logger.get_entry(entry_id)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit entry not found: {entry_id}",
        )

    return AuditEntryResponse(
        id=entry.id,
        action=entry.action.value,
        resource=entry.resource.value,
        resource_id=entry.resource_id,
        actor_id=entry.actor_id,
        actor_name=entry.actor_name,
        timestamp=entry.timestamp,
        severity=entry.severity.value,
        message=entry.message,
        details=entry.details,
        metadata=entry.metadata,
        ip_address=entry.ip_address,
        user_agent=entry.user_agent,
        execution_id=entry.execution_id,
        workflow_id=entry.workflow_id,
    )


@router.get(
    "/executions/{execution_id}/trail",
    response_model=AuditTrailResponse,
    summary="獲取執行軌跡",
    description="獲取指定執行的完整審計軌跡",
)
async def get_execution_trail(
    execution_id: UUID,
    include_related: bool = Query(True, description="是否包含相關事件"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> AuditTrailResponse:
    """獲取執行軌跡."""
    entries = audit_logger.get_execution_trail(
        execution_id=execution_id,
        include_related=include_related,
    )

    # 計算時間範圍
    start_time = None
    end_time = None
    if entries:
        start_time = entries[0].timestamp
        end_time = entries[-1].timestamp

    return AuditTrailResponse(
        execution_id=execution_id,
        entries=[
            AuditEntryResponse(
                id=e.id,
                action=e.action.value,
                resource=e.resource.value,
                resource_id=e.resource_id,
                actor_id=e.actor_id,
                actor_name=e.actor_name,
                timestamp=e.timestamp,
                severity=e.severity.value,
                message=e.message,
                details=e.details,
                metadata=e.metadata,
                ip_address=e.ip_address,
                user_agent=e.user_agent,
                execution_id=e.execution_id,
                workflow_id=e.workflow_id,
            )
            for e in entries
        ],
        total_entries=len(entries),
        start_time=start_time,
        end_time=end_time,
    )


# =============================================================================
# Statistics & Export Endpoints
# =============================================================================


@router.get(
    "/statistics",
    response_model=AuditStatisticsResponse,
    summary="獲取統計信息",
    description="獲取審計日誌統計信息",
)
async def get_statistics(
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> AuditStatisticsResponse:
    """獲取審計統計."""
    stats = audit_logger.get_statistics(
        start_time=start_time,
        end_time=end_time,
    )

    return AuditStatisticsResponse(
        total_entries=stats["total_entries"],
        by_action=stats["by_action"],
        by_resource=stats["by_resource"],
        by_severity=stats["by_severity"],
        period=stats["period"],
    )


@router.get(
    "/export",
    summary="導出審計日誌",
    description="導出審計日誌為 CSV 或 JSON 格式",
)
async def export_logs(
    format: str = Query("csv", description="導出格式 (csv/json)"),
    action: Optional[str] = Query(None, description="動作類型過濾"),
    resource: Optional[str] = Query(None, description="資源類型過濾"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(1000, ge=1, le=10000, description="導出數量限制"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """導出審計日誌."""
    # 解析動作類型
    actions = None
    if action:
        try:
            actions = [AuditAction(action)]
        except ValueError:
            pass

    # 解析資源類型
    resources = None
    if resource:
        try:
            resources = [AuditResource(resource)]
        except ValueError:
            pass

    params = AuditQueryParams(
        actions=actions,
        resources=resources,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    if format.lower() == "csv":
        csv_data = audit_logger.export_csv(params)
        return PlainTextResponse(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            },
        )

    elif format.lower() == "json":
        json_data = audit_logger.export_json(params)
        return {
            "format": "json",
            "data": json_data,
            "entry_count": len(json_data),
            "timestamp": datetime.utcnow().isoformat(),
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}. Use 'csv' or 'json'.",
        )


# =============================================================================
# Metadata Endpoints
# =============================================================================


@router.get(
    "/actions",
    response_model=ActionListResponse,
    summary="列出動作類型",
    description="獲取所有可用的動作類型",
)
async def list_actions() -> ActionListResponse:
    """列出所有動作類型."""
    actions = [
        {"value": action.value, "name": action.name}
        for action in AuditAction
    ]
    return ActionListResponse(actions=actions)


@router.get(
    "/resources",
    response_model=ResourceListResponse,
    summary="列出資源類型",
    description="獲取所有可用的資源類型",
)
async def list_resources() -> ResourceListResponse:
    """列出所有資源類型."""
    resources = [
        {"value": resource.value, "name": resource.name}
        for resource in AuditResource
    ]
    return ResourceListResponse(resources=resources)


@router.get(
    "/health",
    summary="健康檢查",
    description="審計服務健康檢查",
)
async def health_check(
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """健康檢查."""
    return {
        "status": "healthy",
        "service": "audit",
        "entry_count": audit_logger.get_entry_count(),
        "timestamp": datetime.utcnow().isoformat(),
    }
