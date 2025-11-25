"""
Workflow Version Management API routes
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_active_user
from src.domain.workflows.schemas import (
    VersionResponse,
    VersionListResponse,
    VersionCreateRequest,
    RollbackRequest,
    VersionCompareResponse,
    WorkflowResponse
)
from src.domain.workflows.version_differ import VersionDiffer
from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from src.infrastructure.database.repositories.workflow_version_repository import WorkflowVersionRepository
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


def get_workflow_repository(session: AsyncSession = Depends(get_session)) -> WorkflowRepository:
    """Get workflow repository dependency"""
    return WorkflowRepository(session)


def get_workflow_version_repository(session: AsyncSession = Depends(get_session)) -> WorkflowVersionRepository:
    """Get workflow version repository dependency"""
    return WorkflowVersionRepository(session)


@router.get("/{workflow_id}/versions", response_model=VersionListResponse)
async def list_versions(
    workflow_id: UUID,
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of versions returned"),
    current_user: User = Depends(get_current_active_user),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    version_repo: WorkflowVersionRepository = Depends(get_workflow_version_repository)
):
    """
    List all versions for a workflow

    Args:
        workflow_id: Workflow UUID
        limit: Optional limit on number of versions
        current_user: Current authenticated user
        workflow_repo: Workflow repository
        version_repo: Version repository

    Returns:
        List of versions with metadata

    Raises:
        HTTPException: If workflow not found
    """
    # Check if workflow exists
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Get versions
    versions = await version_repo.get_by_workflow_id(workflow_id, limit=limit)
    total = await version_repo.count_versions(workflow_id)

    logger.info(f"Listed {len(versions)} versions for workflow {workflow_id} by user {current_user.id}")

    return VersionListResponse(
        items=versions,
        total=total,
        current_version_id=workflow.current_version_id
    )


@router.get("/{workflow_id}/versions/{version_number}", response_model=VersionResponse)
async def get_version(
    workflow_id: UUID,
    version_number: int,
    current_user: User = Depends(get_current_active_user),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    version_repo: WorkflowVersionRepository = Depends(get_workflow_version_repository)
):
    """
    Get a specific version by version number

    Args:
        workflow_id: Workflow UUID
        version_number: Version number to retrieve
        current_user: Current authenticated user
        workflow_repo: Workflow repository
        version_repo: Version repository

    Returns:
        Version details

    Raises:
        HTTPException: If workflow or version not found
    """
    # Check if workflow exists
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Get version
    version = await version_repo.get_by_version_number(workflow_id, version_number)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for workflow {workflow_id}"
        )

    logger.info(f"Retrieved version {version_number} for workflow {workflow_id} by user {current_user.id}")

    return version


@router.post("/{workflow_id}/versions/rollback", response_model=WorkflowResponse)
async def rollback_version(
    workflow_id: UUID,
    request: RollbackRequest,
    current_user: User = Depends(get_current_active_user),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    version_repo: WorkflowVersionRepository = Depends(get_workflow_version_repository)
):
    """
    Rollback workflow to a specific version

    This creates a NEW version with the content from the target version,
    preserving complete version history.

    Args:
        workflow_id: Workflow UUID
        request: Rollback request with version number
        current_user: Current authenticated user
        workflow_repo: Workflow repository
        version_repo: Version repository

    Returns:
        Updated workflow

    Raises:
        HTTPException: If workflow or version not found
    """
    # Get workflow
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Get target version
    target_version = await version_repo.get_by_version_number(workflow_id, request.version_number)
    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {request.version_number} not found for workflow {workflow_id}"
        )

    # Extract definition from target version
    definition = target_version.definition

    # Update workflow with target version's definition
    from src.domain.workflows.schemas import WorkflowUpdate, TriggerType, WorkflowStatus

    workflow_update = WorkflowUpdate(
        name=definition.get("name"),
        description=definition.get("description"),
        trigger_type=TriggerType(definition.get("trigger_type", "manual")),
        trigger_config=definition.get("trigger_config", {}),
        status=WorkflowStatus(definition.get("status", "draft")),
        tags=definition.get("tags", [])
    )

    # Prepare rollback summary
    change_summary = request.change_summary or f"Rolled back to version {request.version_number}"

    # Update workflow (this automatically creates a new version)
    updated_workflow = await workflow_repo.update(
        workflow,
        workflow_update,
        created_by=current_user.id,
        change_summary=change_summary
    )

    logger.info(f"Rolled back workflow {workflow_id} to version {request.version_number} by user {current_user.id}")

    return updated_workflow


@router.get("/{workflow_id}/versions/compare", response_model=VersionCompareResponse)
async def compare_versions(
    workflow_id: UUID,
    version1: int = Query(..., gt=0, description="First version number"),
    version2: int = Query(..., gt=0, description="Second version number"),
    current_user: User = Depends(get_current_active_user),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    version_repo: WorkflowVersionRepository = Depends(get_workflow_version_repository)
):
    """
    Compare two workflow versions

    Args:
        workflow_id: Workflow UUID
        version1: First version number
        version2: Second version number
        current_user: Current authenticated user
        workflow_repo: Workflow repository
        version_repo: Version repository

    Returns:
        Comparison details with differences

    Raises:
        HTTPException: If workflow or versions not found
    """
    # Check if workflow exists
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Get both versions
    v1 = await version_repo.get_by_version_number(workflow_id, version1)
    if not v1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version1} not found"
        )

    v2 = await version_repo.get_by_version_number(workflow_id, version2)
    if not v2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version2} not found"
        )

    # Compare versions
    differences = VersionDiffer.compare(v1.definition, v2.definition)

    logger.info(f"Compared versions {version1} and {version2} for workflow {workflow_id} by user {current_user.id}")

    return VersionCompareResponse(
        version1=v1,
        version2=v2,
        differences=differences
    )


@router.post("/{workflow_id}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version_snapshot(
    workflow_id: UUID,
    request: VersionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    version_repo: WorkflowVersionRepository = Depends(get_workflow_version_repository)
):
    """
    Manually create a version snapshot of current workflow state

    Args:
        workflow_id: Workflow UUID
        request: Version creation request with change summary
        current_user: Current authenticated user
        workflow_repo: Workflow repository
        version_repo: Version repository

    Returns:
        Created version

    Raises:
        HTTPException: If workflow not found
    """
    # Get workflow
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Create version snapshot
    version = await version_repo.create_version(
        workflow=workflow,
        created_by=current_user.id,
        change_summary=request.change_summary
    )

    logger.info(f"Created manual version snapshot for workflow {workflow_id} by user {current_user.id}")

    return version
