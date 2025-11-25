"""
Workflow Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict


class TriggerType(str, Enum):
    """Workflow trigger types"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"


class WorkflowStatus(str, Enum):
    """Workflow status"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class WorkflowBase(BaseModel):
    """Base workflow schema with common fields"""
    name: str = Field(..., min_length=2, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    trigger_type: TriggerType = Field(..., description="How the workflow is triggered")
    trigger_config: dict[str, Any] = Field(default_factory=dict, description="Trigger configuration (JSON)")
    status: WorkflowStatus = Field(default=WorkflowStatus.DRAFT, description="Workflow status")
    tags: List[str] = Field(default_factory=list, description="Workflow tags for categorization")

    @validator('trigger_config')
    def validate_trigger_config(cls, v, values):
        """Validate trigger configuration based on trigger type"""
        trigger_type = values.get('trigger_type')

        if trigger_type == TriggerType.SCHEDULED:
            if 'cron_expression' not in v:
                raise ValueError("Scheduled workflows must have 'cron_expression' in trigger_config")

        elif trigger_type == TriggerType.WEBHOOK:
            if 'webhook_url' not in v and 'webhook_secret' not in v:
                raise ValueError("Webhook workflows should have 'webhook_url' or 'webhook_secret' in trigger_config")

        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags list"""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")

        for tag in v:
            if len(tag) > 50:
                raise ValueError("Tag length must not exceed 50 characters")

        return v


class WorkflowCreate(WorkflowBase):
    """Schema for creating a new workflow"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Customer Onboarding Workflow",
                "description": "Automated customer onboarding process with email verification",
                "trigger_type": "webhook",
                "trigger_config": {
                    "webhook_secret": "secret_key_here"
                },
                "status": "draft",
                "tags": ["customer", "onboarding", "automation"]
            }
        }
    )


class WorkflowUpdate(BaseModel):
    """Schema for updating an existing workflow (all fields optional)"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    trigger_type: Optional[TriggerType] = None
    trigger_config: Optional[dict[str, Any]] = None
    status: Optional[WorkflowStatus] = None
    tags: Optional[List[str]] = None

    @validator('trigger_config')
    def validate_trigger_config(cls, v, values):
        """Validate trigger configuration if provided"""
        if v is not None:
            trigger_type = values.get('trigger_type')

            if trigger_type == TriggerType.SCHEDULED:
                if 'cron_expression' not in v:
                    raise ValueError("Scheduled workflows must have 'cron_expression' in trigger_config")

            elif trigger_type == TriggerType.WEBHOOK:
                if 'webhook_url' not in v and 'webhook_secret' not in v:
                    raise ValueError("Webhook workflows should have 'webhook_url' or 'webhook_secret'")

        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags if provided"""
        if v is not None:
            if len(v) > 10:
                raise ValueError("Maximum 10 tags allowed")

            for tag in v:
                if len(tag) > 50:
                    raise ValueError("Tag length must not exceed 50 characters")

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Workflow Name",
                "status": "active",
                "tags": ["updated", "production"]
            }
        }
    )


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response"""
    id: UUID = Field(..., description="Workflow unique identifier")
    created_by: UUID = Field(..., description="User ID who created the workflow")
    current_version_id: Optional[UUID] = Field(None, description="Current active version ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Customer Onboarding Workflow",
                "description": "Automated customer onboarding process",
                "trigger_type": "webhook",
                "trigger_config": {"webhook_secret": "***"},
                "status": "active",
                "tags": ["customer", "onboarding"],
                "created_by": "223e4567-e89b-12d3-a456-426614174001",
                "current_version_id": "323e4567-e89b-12d3-a456-426614174002",
                "created_at": "2025-11-21T12:00:00Z",
                "updated_at": "2025-11-21T12:30:00Z"
            }
        }
    )


class WorkflowListResponse(BaseModel):
    """Schema for paginated workflow list response"""
    items: List[WorkflowResponse] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total number of workflows")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Workflow 1",
                        "description": "Description 1",
                        "trigger_type": "manual",
                        "trigger_config": {},
                        "status": "active",
                        "tags": ["tag1"],
                        "created_by": "223e4567-e89b-12d3-a456-426614174001",
                        "current_version_id": None,
                        "created_at": "2025-11-21T12:00:00Z",
                        "updated_at": "2025-11-21T12:00:00Z"
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }
    )


class WorkflowFilterParams(BaseModel):
    """Query parameters for filtering workflows"""
    status: Optional[WorkflowStatus] = Field(None, description="Filter by status")
    trigger_type: Optional[TriggerType] = Field(None, description="Filter by trigger type")
    tags: Optional[str] = Field(None, description="Filter by tags (comma-separated)")
    search: Optional[str] = Field(None, description="Search in name and description")
    created_by: Optional[UUID] = Field(None, description="Filter by creator")

    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    # Sorting
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order (asc/desc)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "active",
                "trigger_type": "webhook",
                "tags": "customer,onboarding",
                "search": "onboarding",
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }
    )


# ========================================
# Workflow Version Management Schemas
# ========================================

class VersionResponse(BaseModel):
    """Schema for workflow version response"""
    id: UUID = Field(..., description="Version unique identifier")
    workflow_id: UUID = Field(..., description="Workflow ID this version belongs to")
    version_number: int = Field(..., description="Sequential version number (1, 2, 3...)")
    definition: dict[str, Any] = Field(..., description="Complete workflow definition at this version")
    change_summary: Optional[str] = Field(None, description="Summary of changes in this version")
    created_by: UUID = Field(..., description="User ID who created this version")
    created_at: datetime = Field(..., description="Version creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "523e4567-e89b-12d3-a456-426614174003",
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "version_number": 3,
                "definition": {
                    "name": "Customer Onboarding Workflow",
                    "description": "Automated process",
                    "trigger_type": "webhook",
                    "trigger_config": {"webhook_secret": "***"},
                    "status": "active",
                    "tags": ["customer", "onboarding"]
                },
                "change_summary": "Updated trigger configuration",
                "created_by": "223e4567-e89b-12d3-a456-426614174001",
                "created_at": "2025-11-21T14:30:00Z"
            }
        }
    )


class VersionListResponse(BaseModel):
    """Schema for workflow version list response"""
    items: List[VersionResponse] = Field(..., description="List of versions (newest first)")
    total: int = Field(..., description="Total number of versions")
    current_version_id: Optional[UUID] = Field(None, description="Current active version ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "523e4567-e89b-12d3-a456-426614174003",
                        "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                        "version_number": 3,
                        "definition": {"name": "Workflow v3"},
                        "change_summary": "Latest changes",
                        "created_by": "223e4567-e89b-12d3-a456-426614174001",
                        "created_at": "2025-11-21T14:30:00Z"
                    }
                ],
                "total": 3,
                "current_version_id": "523e4567-e89b-12d3-a456-426614174003"
            }
        }
    )


class VersionCreateRequest(BaseModel):
    """Schema for manually creating a version snapshot"""
    change_summary: str = Field(..., min_length=1, max_length=500, description="Description of changes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "change_summary": "Manual snapshot before major refactoring"
            }
        }
    )


class RollbackRequest(BaseModel):
    """Schema for rolling back to a specific version"""
    version_number: int = Field(..., gt=0, description="Version number to rollback to")
    change_summary: Optional[str] = Field(None, max_length=500, description="Reason for rollback")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version_number": 2,
                "change_summary": "Rollback due to bug in version 4"
            }
        }
    )


class VersionCompareResponse(BaseModel):
    """Schema for comparing two workflow versions"""
    version1: VersionResponse = Field(..., description="First version details")
    version2: VersionResponse = Field(..., description="Second version details")
    differences: dict[str, Any] = Field(..., description="Differences between versions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version1": {
                    "id": "423e4567-e89b-12d3-a456-426614174002",
                    "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                    "version_number": 2,
                    "definition": {"trigger_type": "manual"},
                    "change_summary": "Initial version",
                    "created_by": "223e4567-e89b-12d3-a456-426614174001",
                    "created_at": "2025-11-21T12:00:00Z"
                },
                "version2": {
                    "id": "523e4567-e89b-12d3-a456-426614174003",
                    "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                    "version_number": 4,
                    "definition": {"trigger_type": "webhook"},
                    "change_summary": "Changed to webhook trigger",
                    "created_by": "223e4567-e89b-12d3-a456-426614174001",
                    "created_at": "2025-11-21T14:00:00Z"
                },
                "differences": {
                    "modified": {
                        "trigger_type": {
                            "old": "manual",
                            "new": "webhook"
                        }
                    },
                    "added": {},
                    "removed": {}
                }
            }
        }
    )
