# =============================================================================
# IPA Platform - Versioning API Schemas
# =============================================================================
# Sprint 4: Developer Experience - Template Version Management
#
# Pydantic schemas for versioning API request/response validation.
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Version Schemas
# =============================================================================


class CreateVersionRequest(BaseModel):
    """Request to create a new version."""

    template_id: str = Field(..., min_length=1, description="Template ID")
    content: Dict[str, Any] = Field(..., description="Version content")
    change_type: str = Field("patch", description="Change type: major, minor, patch")
    changelog: str = Field("", description="Change description")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    tags: List[str] = Field(default_factory=list, description="Version tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class VersionResponse(BaseModel):
    """Version response."""

    id: UUID
    template_id: str
    version: str
    status: str
    created_at: datetime
    created_by: Optional[str]
    changelog: str
    parent_version_id: Optional[UUID]
    tags: List[str]
    metadata: Dict[str, Any]


class VersionDetailResponse(BaseModel):
    """Version detail response with content."""

    id: UUID
    template_id: str
    version: str
    content: Dict[str, Any]
    status: str
    created_at: datetime
    created_by: Optional[str]
    changelog: str
    parent_version_id: Optional[UUID]
    tags: List[str]
    metadata: Dict[str, Any]


class VersionListResponse(BaseModel):
    """Version list response."""

    versions: List[VersionResponse]
    total: int


# =============================================================================
# Status Schemas
# =============================================================================


class PublishVersionRequest(BaseModel):
    """Request to publish a version."""

    published_by: Optional[str] = Field(None, description="Publisher identifier")


class DeprecateVersionRequest(BaseModel):
    """Request to deprecate a version."""

    reason: str = Field("", description="Deprecation reason")


# =============================================================================
# Diff Schemas
# =============================================================================


class DiffLineResponse(BaseModel):
    """Diff line response."""

    type: str  # add, remove, context
    content: str
    old_line: Optional[int]
    new_line: Optional[int]


class DiffHunkResponse(BaseModel):
    """Diff hunk response."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLineResponse]


class DiffResponse(BaseModel):
    """Diff response."""

    old_version: Optional[str]
    new_version: str
    changes: List[DiffHunkResponse]
    summary: Dict[str, int]
    affected_fields: List[str]


class CompareRequest(BaseModel):
    """Request to compare versions."""

    old_version_id: Optional[UUID] = Field(None, description="Old version ID")
    new_version_id: UUID = Field(..., description="New version ID")


# =============================================================================
# Rollback Schemas
# =============================================================================


class RollbackRequest(BaseModel):
    """Request to rollback to a version."""

    target_version_id: UUID = Field(..., description="Target version to rollback to")
    created_by: Optional[str] = Field(None, description="Creator identifier")


# =============================================================================
# Statistics Schemas
# =============================================================================


class VersionStatisticsResponse(BaseModel):
    """Version statistics response."""

    total_templates: int
    total_versions: int
    versions_by_status: Dict[str, int]
    avg_versions_per_template: float
    recent_versions: List[Dict[str, Any]]


class TemplateStatisticsResponse(BaseModel):
    """Template-specific statistics response."""

    template_id: str
    total_versions: int
    current_version: Optional[str]
    latest_version: Optional[str]
    versions_by_status: Dict[str, int]
    first_created: Optional[str]
    last_updated: Optional[str]


# =============================================================================
# Health Check Schema
# =============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    service: str = "versioning"
    status: str
    total_versions: int
