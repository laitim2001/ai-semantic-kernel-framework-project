# =============================================================================
# IPA Platform - Workflow API Routes
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# RESTful API endpoints for Workflow management:
#   - POST /workflows/ - Create workflow
#   - GET /workflows/ - List workflows
#   - GET /workflows/{id} - Get workflow
#   - PUT /workflows/{id} - Update workflow
#   - DELETE /workflows/{id} - Delete workflow
#   - POST /workflows/{id}/execute - Execute workflow
#   - POST /workflows/{id}/validate - Validate workflow
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.workflows.models import WorkflowDefinition
from src.domain.workflows.schemas import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse,
    WorkflowValidationResponse,
)
from src.domain.workflows.service import (
    WorkflowExecutionService,
    get_workflow_execution_service,
)
from src.infrastructure.database.session import get_session
from src.infrastructure.database.repositories.workflow import WorkflowRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# =============================================================================
# Dependencies
# =============================================================================


async def get_workflow_repository(
    session: AsyncSession = Depends(get_session),
) -> WorkflowRepository:
    """Dependency for WorkflowRepository."""
    return WorkflowRepository(session)


async def get_execution_service() -> WorkflowExecutionService:
    """Dependency for WorkflowExecutionService."""
    return get_workflow_execution_service()


# =============================================================================
# Helper Functions
# =============================================================================


def workflow_to_response(workflow) -> WorkflowResponse:
    """Convert Workflow ORM model to response schema."""
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        trigger_type=workflow.trigger_type,
        trigger_config=workflow.trigger_config if isinstance(workflow.trigger_config, dict) else {},
        graph_definition=workflow.graph_definition if isinstance(workflow.graph_definition, dict) else {},
        status=workflow.status,
        version=workflow.version,
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workflow",
    description="Create a new workflow with graph definition.",
)
async def create_workflow(
    request: WorkflowCreateRequest,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowResponse:
    """
    Create a new workflow.

    - **name**: Workflow name
    - **description**: Optional description
    - **trigger_type**: How the workflow is triggered
    - **graph_definition**: Node and edge definitions
    """
    # Convert graph schema to dict
    graph_dict = {
        "nodes": [node.model_dump() for node in request.graph_definition.nodes],
        "edges": [edge.model_dump() for edge in request.graph_definition.edges],
        "variables": request.graph_definition.variables,
    }

    # Validate workflow definition
    try:
        definition = WorkflowDefinition.from_dict(graph_dict)
        errors = definition.validate()
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Invalid workflow definition", "errors": errors},
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow definition: {str(e)}",
        )

    # Create workflow
    workflow = await repo.create(
        name=request.name,
        description=request.description,
        trigger_type=request.trigger_type,
        trigger_config=request.trigger_config,
        graph_definition=graph_dict,
    )

    logger.info(f"Created workflow: {workflow.name} (id={workflow.id})")

    return workflow_to_response(workflow)


@router.get(
    "/",
    response_model=WorkflowListResponse,
    summary="List Workflows",
    description="Get paginated list of workflows with optional filters.",
)
async def list_workflows(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    trigger_type: Optional[str] = Query(default=None, description="Filter by trigger type"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
    search: Optional[str] = Query(default=None, description="Search in name/description"),
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowListResponse:
    """
    List workflows with pagination and filters.

    - **page**: Page number (1-indexed)
    - **page_size**: Number of items per page
    - **trigger_type**: Optional trigger type filter
    - **status**: Optional status filter
    - **search**: Optional search query
    """
    if search:
        items, total = await repo.search(search, page=page, page_size=page_size)
    else:
        filters = {}
        if trigger_type:
            filters["trigger_type"] = trigger_type
        if status_filter:
            filters["status"] = status_filter

        items, total = await repo.list(page=page, page_size=page_size, **filters)

    return WorkflowListResponse(
        items=[workflow_to_response(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Get Workflow",
    description="Get a specific workflow by ID.",
)
async def get_workflow(
    workflow_id: UUID,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowResponse:
    """Get workflow by ID."""
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    return workflow_to_response(workflow)


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update Workflow",
    description="Update an existing workflow.",
)
async def update_workflow(
    workflow_id: UUID,
    request: WorkflowUpdateRequest,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowResponse:
    """
    Update workflow fields.

    Only provided fields will be updated.
    """
    # Check exists
    existing = await repo.get(workflow_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    # Build update data
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.trigger_type is not None:
        update_data["trigger_type"] = request.trigger_type
    if request.trigger_config is not None:
        update_data["trigger_config"] = request.trigger_config
    if request.graph_definition is not None:
        graph_dict = {
            "nodes": [node.model_dump() for node in request.graph_definition.nodes],
            "edges": [edge.model_dump() for edge in request.graph_definition.edges],
            "variables": request.graph_definition.variables,
        }

        # Validate new graph definition
        try:
            definition = WorkflowDefinition.from_dict(graph_dict)
            errors = definition.validate()
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Invalid workflow definition", "errors": errors},
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid workflow definition: {str(e)}",
            )

        update_data["graph_definition"] = graph_dict
    if request.status is not None:
        update_data["status"] = request.status

    # Update
    workflow = await repo.update(workflow_id, **update_data)

    # Increment version
    await repo.increment_version(workflow_id)
    workflow = await repo.get(workflow_id)

    logger.info(f"Updated workflow: {workflow.name} (id={workflow.id})")

    return workflow_to_response(workflow)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Workflow",
    description="Delete a workflow.",
)
async def delete_workflow(
    workflow_id: UUID,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> None:
    """Delete workflow by ID."""
    deleted = await repo.delete(workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    logger.info(f"Deleted workflow: {workflow_id}")


# =============================================================================
# Execution Endpoints
# =============================================================================


@router.post(
    "/{workflow_id}/execute",
    response_model=WorkflowExecutionResponse,
    summary="Execute Workflow",
    description="Execute a workflow with input data.",
)
async def execute_workflow(
    workflow_id: UUID,
    request: WorkflowExecuteRequest,
    repo: WorkflowRepository = Depends(get_workflow_repository),
    execution_service: WorkflowExecutionService = Depends(get_execution_service),
) -> WorkflowExecutionResponse:
    """
    Execute a workflow.

    - **input**: Initial input data for the workflow
    - **variables**: Optional runtime variables
    """
    # Get workflow
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    # Check workflow is active
    if workflow.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow is not active (status: {workflow.status})",
        )

    # Parse workflow definition
    try:
        definition = WorkflowDefinition.from_dict(workflow.graph_definition)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse workflow definition: {str(e)}",
        )

    # Execute workflow
    try:
        result = await execution_service.execute_workflow(
            workflow_id=workflow_id,
            definition=definition,
            input_data=request.input,
            variables=request.variables,
        )

        logger.info(
            f"Workflow {workflow.name} executed: "
            f"status={result.status}, tokens={result.total_llm_tokens}, "
            f"cost=${result.total_llm_cost:.6f}"
        )

        from datetime import datetime

        return WorkflowExecutionResponse(
            execution_id=result.execution_id,
            workflow_id=result.workflow_id,
            status=result.status,
            result=result.result,
            node_results=[
                {
                    "node_id": nr.node_id,
                    "type": nr.node_type.value,
                    "output": nr.output,
                    "error": nr.error,
                    "llm_calls": nr.llm_calls,
                    "llm_tokens": nr.llm_tokens,
                    "llm_cost": nr.llm_cost,
                    "started_at": nr.started_at,
                    "completed_at": nr.completed_at,
                }
                for nr in result.node_results
            ],
            stats={
                "total_llm_calls": result.total_llm_calls,
                "total_llm_tokens": result.total_llm_tokens,
                "total_llm_cost": result.total_llm_cost,
                "duration_seconds": result.duration_seconds,
            },
            started_at=result.started_at,
            completed_at=result.completed_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@router.post(
    "/{workflow_id}/validate",
    response_model=WorkflowValidationResponse,
    summary="Validate Workflow",
    description="Validate a workflow definition without saving.",
)
async def validate_workflow(
    workflow_id: UUID,
    repo: WorkflowRepository = Depends(get_workflow_repository),
    execution_service: WorkflowExecutionService = Depends(get_execution_service),
) -> WorkflowValidationResponse:
    """
    Validate a workflow definition.

    Returns validation errors and warnings.
    """
    # Get workflow
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    # Parse and validate
    try:
        definition = WorkflowDefinition.from_dict(workflow.graph_definition)
        validation_result = await execution_service.validate_workflow(definition)

        return WorkflowValidationResponse(
            valid=validation_result["valid"],
            errors=validation_result["errors"],
            warnings=validation_result["warnings"],
        )
    except Exception as e:
        return WorkflowValidationResponse(
            valid=False,
            errors=[f"Failed to parse workflow: {str(e)}"],
            warnings=[],
        )


@router.post(
    "/{workflow_id}/activate",
    response_model=WorkflowResponse,
    summary="Activate Workflow",
    description="Set workflow status to active.",
)
async def activate_workflow(
    workflow_id: UUID,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowResponse:
    """Activate a workflow."""
    workflow = await repo.activate(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    logger.info(f"Activated workflow: {workflow.name} (id={workflow.id})")
    return workflow_to_response(workflow)


@router.post(
    "/{workflow_id}/deactivate",
    response_model=WorkflowResponse,
    summary="Deactivate Workflow",
    description="Set workflow status to inactive.",
)
async def deactivate_workflow(
    workflow_id: UUID,
    repo: WorkflowRepository = Depends(get_workflow_repository),
) -> WorkflowResponse:
    """Deactivate a workflow."""
    workflow = await repo.deactivate(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    logger.info(f"Deactivated workflow: {workflow.name} (id={workflow.id})")
    return workflow_to_response(workflow)
