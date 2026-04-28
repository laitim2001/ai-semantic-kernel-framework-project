# =============================================================================
# IPA Platform - Audit API Schemas
# =============================================================================
# Sprint 3: 集成 & 可靠性 - 審計日誌系統
#
# Pydantic schemas for Audit API endpoints.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Response Schemas
# =============================================================================


class AuditEntryResponse(BaseModel):
    """審計條目響應."""

    id: UUID = Field(..., description="條目 ID")
    action: str = Field(..., description="動作類型")
    resource: str = Field(..., description="資源類型")
    resource_id: Optional[str] = Field(None, description="資源 ID")
    actor_id: Optional[str] = Field(None, description="操作者 ID")
    actor_name: str = Field(..., description="操作者名稱")
    timestamp: datetime = Field(..., description="時間戳")
    severity: str = Field(..., description="嚴重程度")
    message: str = Field(..., description="消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="詳細信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
    ip_address: Optional[str] = Field(None, description="IP 地址")
    user_agent: Optional[str] = Field(None, description="用戶代理")
    execution_id: Optional[UUID] = Field(None, description="執行 ID")
    workflow_id: Optional[UUID] = Field(None, description="工作流 ID")


class AuditListResponse(BaseModel):
    """審計日誌列表響應."""

    items: List[AuditEntryResponse] = Field(..., description="條目列表")
    total: int = Field(..., description="總數")
    offset: int = Field(0, description="偏移量")
    limit: int = Field(100, description="返回數量")


class AuditTrailResponse(BaseModel):
    """執行軌跡響應."""

    execution_id: UUID = Field(..., description="執行 ID")
    entries: List[AuditEntryResponse] = Field(..., description="軌跡條目")
    total_entries: int = Field(..., description="條目總數")
    start_time: Optional[datetime] = Field(None, description="開始時間")
    end_time: Optional[datetime] = Field(None, description="結束時間")


class AuditStatisticsResponse(BaseModel):
    """審計統計響應."""

    total_entries: int = Field(..., description="條目總數")
    by_action: Dict[str, int] = Field(..., description="按動作統計")
    by_resource: Dict[str, int] = Field(..., description="按資源統計")
    by_severity: Dict[str, int] = Field(..., description="按嚴重程度統計")
    period: Dict[str, Optional[str]] = Field(..., description="統計期間")


class ExportResponse(BaseModel):
    """導出響應."""

    format: str = Field(..., description="導出格式")
    data: str = Field(..., description="導出數據")
    entry_count: int = Field(..., description="條目數量")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="導出時間"
    )


class ActionListResponse(BaseModel):
    """動作列表響應."""

    actions: List[Dict[str, str]] = Field(..., description="動作列表")


class ResourceListResponse(BaseModel):
    """資源列表響應."""

    resources: List[Dict[str, str]] = Field(..., description="資源列表")
