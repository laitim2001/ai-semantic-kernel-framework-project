"""
Audit Log Schemas (Pydantic Models)

Sprint 2 - Story S2-7

Note: These schemas are designed to work with the current audit_logs table schema.
Some fields are optional to support backwards compatibility.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AuditLogCreate(BaseModel):
    """Schema for creating audit log entries."""
    action: str = Field(..., description="Action being logged (CREATE, UPDATE, DELETE, etc.)")
    resource_type: str = Field(..., description="Type of resource (workflow, execution, agent)")
    resource_id: Optional[UUID] = Field(None, description="UUID of the affected resource")
    resource_name: Optional[str] = Field(None, description="Human-readable resource name")
    user_id: Optional[UUID] = Field(None, description="UUID of the user performing the action")
    actor_type: str = Field(default="user", description="Type of actor (user, system, webhook)")
    changes: Optional[dict[str, Any]] = Field(None, description="Dictionary of changes made")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent string")
    request_id: Optional[str] = Field(None, description="Correlation/request ID")
    extra_data: Optional[dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if action failed")
    duration_ms: Optional[int] = Field(None, description="Duration of action in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action": "CREATE",
                "resource_type": "workflow",
                "resource_id": "550e8400-e29b-41d4-a716-446655440000",
                "resource_name": "My Workflow",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "actor_type": "user",
                "changes": {"name": "My Workflow"},
                "ip_address": "192.168.1.1",
                "request_id": "req-12345",
            }
        }
    )


class AuditLogResponse(BaseModel):
    """Schema for audit log responses."""
    id: int
    user_id: Optional[UUID] = None
    actor_type: Optional[str] = "user"  # Default value for compatibility
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    resource_name: Optional[str] = None  # Not in current DB schema
    changes: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None  # Not in current DB schema
    metadata: Optional[dict[str, Any]] = None  # Not in current DB schema
    error_message: Optional[str] = None  # Not in current DB schema
    duration_ms: Optional[int] = None  # Not in current DB schema
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[UUID] = Field(None, description="Filter by resource ID")
    actor_type: Optional[str] = Field(None, description="Filter by actor type")
    request_id: Optional[str] = Field(None, description="Filter by request ID")
    start_date: Optional[datetime] = Field(None, description="Filter logs after this date")
    end_date: Optional[datetime] = Field(None, description="Filter logs before this date")
    has_error: Optional[bool] = Field(None, description="Filter by error presence")

    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=500, description="Items per page")

    # Sorting
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list response."""
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 50,
                "total_pages": 2,
                "has_next": True,
                "has_previous": False,
            }
        }
    )


class AuditLogExportRequest(BaseModel):
    """Schema for audit log export request."""
    start_date: datetime = Field(..., description="Export logs from this date")
    end_date: datetime = Field(..., description="Export logs until this date")
    format: str = Field(default="csv", description="Export format (csv, json)")
    resource_types: Optional[list[str]] = Field(None, description="Filter by resource types")
    actions: Optional[list[str]] = Field(None, description="Filter by actions")
    include_metadata: bool = Field(default=False, description="Include metadata in export")


class AuditLogStats(BaseModel):
    """Schema for audit log statistics."""
    total_logs: int
    logs_today: int
    logs_this_week: int
    logs_this_month: int
    top_actions: list[dict[str, Any]]
    top_resources: list[dict[str, Any]]
    error_count: int
    error_rate: float
