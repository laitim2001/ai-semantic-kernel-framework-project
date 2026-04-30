# =============================================================================
# IPA Platform - Versioning API Routes
# =============================================================================
# Sprint 4: Developer Experience - Template Version Management
#
# REST API endpoints for template version control:
#   - POST /versions - Create a new version
#   - GET /versions - List all versions
#   - GET /versions/{version_id} - Get version details
#   - DELETE /versions/{version_id} - Delete a version
#   - POST /versions/{version_id}/publish - Publish a version
#   - POST /versions/{version_id}/deprecate - Deprecate a version
#   - POST /versions/{version_id}/archive - Archive a version
#   - GET /templates/{template_id}/versions - List template versions
#   - GET /templates/{template_id}/latest - Get latest version
#   - POST /templates/{template_id}/rollback - Rollback to version
#   - POST /versions/compare - Compare two versions
#   - GET /statistics - Get versioning statistics
#   - GET /templates/{template_id}/statistics - Get template statistics
#   - GET /health - Health check
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.versioning.schemas import (
    CompareRequest,
    CreateVersionRequest,
    DeprecateVersionRequest,
    DiffHunkResponse,
    DiffLineResponse,
    DiffResponse,
    HealthCheckResponse,
    PublishVersionRequest,
    RollbackRequest,
    TemplateStatisticsResponse,
    VersionDetailResponse,
    VersionListResponse,
    VersionResponse,
    VersionStatisticsResponse,
)
from src.domain.versioning import (
    VersioningError,
    VersioningService,
)
from src.domain.versioning.service import ChangeType, VersionStatus


router = APIRouter(prefix="/versions", tags=["versioning"])


# =============================================================================
# Service Instance Management
# =============================================================================

_versioning_service: Optional[VersioningService] = None


def get_versioning_service() -> VersioningService:
    """Get or create versioning service instance."""
    global _versioning_service
    if _versioning_service is None:
        _versioning_service = VersioningService()
    return _versioning_service


def set_versioning_service(service: VersioningService) -> None:
    """Set versioning service instance (for testing)."""
    global _versioning_service
    _versioning_service = service


# =============================================================================
# Helper Functions
# =============================================================================


def _to_version_response(version) -> VersionResponse:
    """Convert version to response."""
    return VersionResponse(
        id=version.id,
        template_id=version.template_id,
        version=str(version.version),
        status=version.status.value,
        created_at=version.created_at,
        created_by=version.created_by,
        changelog=version.changelog,
        parent_version_id=version.parent_version_id,
        tags=version.tags,
        metadata=version.metadata,
    )


def _to_version_detail_response(version) -> VersionDetailResponse:
    """Convert version to detail response."""
    return VersionDetailResponse(
        id=version.id,
        template_id=version.template_id,
        version=str(version.version),
        content=version.content,
        status=version.status.value,
        created_at=version.created_at,
        created_by=version.created_by,
        changelog=version.changelog,
        parent_version_id=version.parent_version_id,
        tags=version.tags,
        metadata=version.metadata,
    )


def _to_diff_response(diff) -> DiffResponse:
    """Convert diff to response."""
    return DiffResponse(
        old_version=diff.old_version,
        new_version=diff.new_version,
        changes=[
            DiffHunkResponse(
                old_start=h.old_start,
                old_count=h.old_count,
                new_start=h.new_start,
                new_count=h.new_count,
                lines=[
                    DiffLineResponse(
                        type=line.type,
                        content=line.content,
                        old_line=line.old_line,
                        new_line=line.new_line,
                    )
                    for line in h.lines
                ],
            )
            for h in diff.changes
        ],
        summary=diff.summary,
        affected_fields=diff.affected_fields,
    )


# =============================================================================
# Static Routes (before dynamic routes)
# =============================================================================


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check versioning service health."""
    service = get_versioning_service()

    return HealthCheckResponse(
        service="versioning",
        status="healthy",
        total_versions=service.get_version_count(),
    )


@router.get("/statistics", response_model=VersionStatisticsResponse)
async def get_statistics():
    """Get versioning statistics."""
    service = get_versioning_service()
    stats = service.get_statistics()

    return VersionStatisticsResponse(
        total_templates=stats.total_templates,
        total_versions=stats.total_versions,
        versions_by_status=stats.versions_by_status,
        avg_versions_per_template=stats.avg_versions_per_template,
        recent_versions=stats.recent_versions,
    )


@router.post("/compare", response_model=DiffResponse)
async def compare_versions(request: CompareRequest):
    """Compare two versions."""
    service = get_versioning_service()

    try:
        diff = service.compare_versions(
            old_version_id=request.old_version_id,
            new_version_id=request.new_version_id,
        )
        return _to_diff_response(diff)
    except VersioningError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Version Management
# =============================================================================


@router.post("/", response_model=VersionResponse)
async def create_version(request: CreateVersionRequest):
    """Create a new version."""
    service = get_versioning_service()

    # Validate change type
    try:
        change_type = ChangeType(request.change_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid change type: {request.change_type}",
        )

    version = service.create_version(
        template_id=request.template_id,
        content=request.content,
        change_type=change_type,
        changelog=request.changelog,
        created_by=request.created_by,
        tags=request.tags,
        metadata=request.metadata,
    )

    return _to_version_response(version)


@router.get("/", response_model=VersionListResponse)
async def list_all_versions(
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
):
    """List all versions."""
    service = get_versioning_service()

    # Get all templates
    all_versions = []
    templates = list(service._template_versions.keys())

    if template_id:
        templates = [template_id]

    for tmpl_id in templates:
        versions = service.list_versions(tmpl_id, limit=limit)
        all_versions.extend(versions)

    # Filter by status
    if status:
        try:
            version_status = VersionStatus(status)
            all_versions = [v for v in all_versions if v.status == version_status]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Sort by created_at
    all_versions.sort(key=lambda v: v.created_at, reverse=True)

    return VersionListResponse(
        versions=[_to_version_response(v) for v in all_versions[:limit]],
        total=len(all_versions[:limit]),
    )


@router.get("/{version_id}", response_model=VersionDetailResponse)
async def get_version(version_id: UUID):
    """Get version details."""
    service = get_versioning_service()

    version = service.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"Version not found: {version_id}")

    return _to_version_detail_response(version)


@router.delete("/{version_id}")
async def delete_version(version_id: UUID):
    """Delete a version."""
    service = get_versioning_service()

    try:
        if service.delete_version(version_id):
            return {"message": "Version deleted", "version_id": str(version_id)}
        else:
            raise HTTPException(status_code=404, detail=f"Version not found: {version_id}")
    except VersioningError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Status Management
# =============================================================================


@router.post("/{version_id}/publish", response_model=VersionResponse)
async def publish_version(version_id: UUID, request: PublishVersionRequest):
    """Publish a version."""
    service = get_versioning_service()

    try:
        version = service.publish_version(
            version_id=version_id,
            published_by=request.published_by,
        )
        if not version:
            raise HTTPException(status_code=404, detail=f"Version not found: {version_id}")
        return _to_version_response(version)
    except VersioningError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{version_id}/deprecate", response_model=VersionResponse)
async def deprecate_version(version_id: UUID, request: DeprecateVersionRequest):
    """Deprecate a version."""
    service = get_versioning_service()

    version = service.deprecate_version(
        version_id=version_id,
        reason=request.reason,
    )
    if not version:
        raise HTTPException(status_code=404, detail=f"Version not found: {version_id}")

    return _to_version_response(version)


@router.post("/{version_id}/archive", response_model=VersionResponse)
async def archive_version(version_id: UUID):
    """Archive a version."""
    service = get_versioning_service()

    version = service.archive_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"Version not found: {version_id}")

    return _to_version_response(version)


# =============================================================================
# Template-Specific Endpoints
# =============================================================================


@router.get("/templates/{template_id}/versions", response_model=VersionListResponse)
async def list_template_versions(
    template_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
):
    """List versions of a template."""
    service = get_versioning_service()

    # Parse status
    version_status = None
    if status:
        try:
            version_status = VersionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    versions = service.list_versions(
        template_id=template_id,
        status=version_status,
        limit=limit,
    )

    return VersionListResponse(
        versions=[_to_version_response(v) for v in versions],
        total=len(versions),
    )


@router.get("/templates/{template_id}/latest", response_model=VersionDetailResponse)
async def get_latest_version(
    template_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get latest version of a template."""
    service = get_versioning_service()

    # Parse status
    version_status = None
    if status:
        try:
            version_status = VersionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    version = service.get_latest_version(
        template_id=template_id,
        status=version_status,
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail=f"No versions found for template: {template_id}",
        )

    return _to_version_detail_response(version)


@router.post("/templates/{template_id}/rollback", response_model=VersionResponse)
async def rollback_version(template_id: str, request: RollbackRequest):
    """Rollback to a previous version."""
    service = get_versioning_service()

    try:
        version = service.rollback(
            template_id=template_id,
            target_version_id=request.target_version_id,
            created_by=request.created_by,
        )
        return _to_version_response(version)
    except VersioningError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}/statistics", response_model=TemplateStatisticsResponse)
async def get_template_statistics(template_id: str):
    """Get statistics for a template."""
    service = get_versioning_service()
    stats = service.get_template_statistics(template_id)

    return TemplateStatisticsResponse(
        template_id=stats["template_id"],
        total_versions=stats["total_versions"],
        current_version=stats.get("current_version"),
        latest_version=stats.get("latest_version"),
        versions_by_status=stats.get("versions_by_status", {}),
        first_created=stats.get("first_created"),
        last_updated=stats.get("last_updated"),
    )
