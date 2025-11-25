"""
Workflow API routes
"""
import logging
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import get_current_active_user
from src.domain.workflows.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowFilterParams,
    TriggerType,
    WorkflowStatus
)
from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Import and include version management routes
from src.api.v1.workflows import versions
router.include_router(versions.router, tags=["Workflow Versions"])


def get_workflow_repository(session: AsyncSession = Depends(get_session)) -> WorkflowRepository:
    """
    Get workflow repository dependency

    Args:
        session: Database session

    Returns:
        WorkflowRepository instance
    """
    return WorkflowRepository(session)


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_active_user),
    repository: WorkflowRepository = Depends(get_workflow_repository)
):
    """
    Create a new workflow

    Args:
        workflow_data: Workflow creation data
        current_user: Current authenticated user
        repository: Workflow repository

    Returns:
        Created workflow

    Raises:
        HTTPException: If workflow with same name already exists
    """
    # Check if workflow with same name exists
    if await repository.exists_by_name(workflow_data.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow with name '{workflow_data.name}' already exists"
        )

    # Create workflow
    workflow = await repository.create(workflow_data, created_by=current_user.id)

    logger.info(f"Workflow created: {workflow.id} by user {current_user.id}")

    return workflow


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    status_filter: Optional[WorkflowStatus] = Query(None, alias="status", description="Filter by status"),
    trigger_type: Optional[TriggerType] = Query(None, description="Filter by trigger type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    created_by: Optional[UUID] = Query(None, description="Filter by creator"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: User = Depends(get_current_active_user),
    repository: WorkflowRepository = Depends(get_workflow_repository)
):
    """
    List workflows with pagination and filtering

    Args:
        status_filter: Optional status filter
        trigger_type: Optional trigger type filter
        tags: Optional tags filter (comma-separated)
        search: Optional search query
        created_by: Optional creator filter
        page: Page number
        page_size: Items per page
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        current_user: Current authenticated user
        repository: Workflow repository

    Returns:
        Paginated list of workflows
    """
    # Build filter parameters
    filters = WorkflowFilterParams(
        status=status_filter,
        trigger_type=trigger_type,
        tags=tags,
        search=search,
        created_by=created_by,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # Get workflows
    workflows, total = await repository.list_workflows(filters)

    # Calculate pagination metadata
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return WorkflowListResponse(
        items=workflows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    repository: WorkflowRepository = Depends(get_workflow_repository)
):
    """
    Get workflow by ID

    Args:
        workflow_id: Workflow UUID
        current_user: Current authenticated user
        repository: Workflow repository

    Returns:
        Workflow details

    Raises:
        HTTPException: If workflow not found
    """
    workflow = await repository.get_by_id(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    logger.info(f"Workflow retrieved: {workflow_id} by user {current_user.id}")

    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_data: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    repository: WorkflowRepository = Depends(get_workflow_repository)
):
    """
    Update workflow

    Args:
        workflow_id: Workflow UUID
        workflow_data: Update data
        current_user: Current authenticated user
        repository: Workflow repository

    Returns:
        Updated workflow

    Raises:
        HTTPException: If workflow not found or name conflict
    """
    # Get existing workflow
    workflow = await repository.get_by_id(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Check name uniqueness if name is being updated
    if workflow_data.name and workflow_data.name != workflow.name:
        if await repository.exists_by_name(workflow_data.name, exclude_id=workflow_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow with name '{workflow_data.name}' already exists"
            )

    # Update workflow (this will automatically create a version)
    updated_workflow = await repository.update(
        workflow,
        workflow_data,
        created_by=current_user.id,
        change_summary="Workflow updated via API"
    )

    logger.info(f"Workflow updated: {workflow_id} by user {current_user.id}")

    return updated_workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    repository: WorkflowRepository = Depends(get_workflow_repository)
):
    """
    Delete workflow

    Args:
        workflow_id: Workflow UUID
        current_user: Current authenticated user
        repository: Workflow repository

    Returns:
        No content

    Raises:
        HTTPException: If workflow not found
    """
    # Get existing workflow
    workflow = await repository.get_by_id(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Delete workflow
    await repository.delete(workflow)

    logger.info(f"Workflow deleted: {workflow_id} by user {current_user.id}")
