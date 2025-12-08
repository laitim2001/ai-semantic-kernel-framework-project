# =============================================================================
# IPA Platform - Workflow API Routes
# =============================================================================
# Sprint 29: API Routes 遷移 (Phase 5)
#
# Migration Notes (Sprint 29):
#   - Migrated from direct WorkflowDefinition to WorkflowDefinitionAdapter
#   - Uses official Agent Framework Workflow API for validation and execution
#   - Maintains backward compatibility with existing API schemas
#   - Database operations remain with WorkflowRepository (infrastructure layer)
#
# RESTful API endpoints for Workflow management:
#   - POST /workflows/ - Create workflow
#   - GET /workflows/ - List workflows
#   - GET /workflows/{id} - Get workflow
#   - PUT /workflows/{id} - Update workflow
#   - DELETE /workflows/{id} - Delete workflow
#   - POST /workflows/{id}/execute - Execute workflow
#   - POST /workflows/{id}/validate - Validate workflow
#
# References:
#   - Sprint 29 Plan: docs/03-implementation/sprint-planning/phase-5/sprint-29-plan.md
#   - WorkflowDefinitionAdapter: src/integrations/agent_framework/core/workflow.py
# =============================================================================

import logging
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Sprint 29: Import from Adapter Layer
# =============================================================================
from src.integrations.agent_framework.core.workflow import (
    WorkflowDefinitionAdapter,
    WorkflowRunResult,
    create_workflow_adapter,
)
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


def serialize_graph_definition(graph_schema) -> dict:
    """Convert graph schema to a JSON-serializable dict.

    Ensures all UUIDs are converted to strings for JSONB storage.
    """
    def serialize_node(node) -> dict:
        node_dict = node.model_dump()
        # Explicitly convert agent_id UUID to string if present
        if node_dict.get("agent_id") is not None:
            node_dict["agent_id"] = str(node_dict["agent_id"])
        return node_dict

    return {
        "nodes": [serialize_node(node) for node in graph_schema.nodes],
        "edges": [edge.model_dump() for edge in graph_schema.edges],
        "variables": graph_schema.variables,
    }


def validate_workflow_definition(graph_dict: dict) -> tuple[bool, list[str]]:
    """
    Validate a workflow definition using WorkflowDefinitionAdapter.

    Sprint 29: Uses official Agent Framework validation via adapter.

    Args:
        graph_dict: The workflow graph definition as dict

    Returns:
        Tuple of (is_valid, errors)
    """
    try:
        definition = WorkflowDefinition.from_dict(graph_dict)
        adapter = WorkflowDefinitionAdapter(definition=definition)
        errors = definition.validate()
        return len(errors) == 0, errors
    except ValueError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


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

    Sprint 29: Uses WorkflowDefinitionAdapter for validation.
    """
    # Convert graph schema to dict with proper UUID serialization
    graph_dict = serialize_graph_definition(request.graph_definition)

    # Validate workflow definition using adapter
    is_valid, errors = validate_workflow_definition(graph_dict)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid workflow definition", "errors": errors},
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

    Sprint 29: Uses WorkflowDefinitionAdapter for validation.
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
        # Convert graph schema with proper UUID serialization
        graph_dict = serialize_graph_definition(request.graph_definition)

        # Validate new graph definition using adapter
        is_valid, errors = validate_workflow_definition(graph_dict)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Invalid workflow definition", "errors": errors},
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
) -> WorkflowExecutionResponse:
    """
    Execute a workflow.

    - **input**: Initial input data for the workflow
    - **variables**: Optional runtime variables

    Sprint 29: Uses WorkflowDefinitionAdapter.run() for execution.
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

    # Parse workflow definition and create adapter
    try:
        definition = WorkflowDefinition.from_dict(workflow.graph_definition)
        adapter = WorkflowDefinitionAdapter(definition=definition)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse workflow definition: {str(e)}",
        )

    # Execute workflow via adapter
    execution_id = uuid4()
    start_time = datetime.utcnow()

    try:
        # Merge input data with variables
        input_data = {
            **request.input,
            "variables": request.variables or {},
        }

        # Execute via WorkflowDefinitionAdapter
        result: WorkflowRunResult = await adapter.run(
            input_data=input_data,
            execution_id=execution_id,
            context={"workflow_id": str(workflow_id)},
        )

        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(
            f"Workflow {workflow.name} executed: "
            f"success={result.success}, duration={duration_seconds:.2f}s"
        )

        # Build node results from execution
        node_results = []
        for node_id, node_output in result.node_results.items():
            node_results.append({
                "node_id": node_id,
                "type": "unknown",  # Type info not available in result
                "output": node_output.data if hasattr(node_output, 'data') else node_output,
                "error": None,
                "llm_calls": 0,
                "llm_tokens": 0,
                "llm_cost": 0.0,
                "started_at": start_time,
                "completed_at": end_time,
            })

        return WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="completed" if result.success else "failed",
            result=result.result,
            node_results=node_results,
            stats={
                "total_llm_calls": 0,
                "total_llm_tokens": 0,
                "total_llm_cost": 0.0,
                "duration_seconds": duration_seconds,
            },
            started_at=start_time,
            completed_at=end_time,
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
) -> WorkflowValidationResponse:
    """
    Validate a workflow definition.

    Returns validation errors and warnings.

    Sprint 29: Uses WorkflowDefinitionAdapter for validation.
    """
    # Get workflow
    workflow = await repo.get(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id '{workflow_id}' not found",
        )

    # Parse and validate using adapter
    try:
        definition = WorkflowDefinition.from_dict(workflow.graph_definition)
        adapter = WorkflowDefinitionAdapter(definition=definition)

        # Get validation errors from definition
        errors = definition.validate()

        # Additional validation warnings
        warnings = []

        # Check for unreachable nodes
        if len(definition.edges) == 0 and len(definition.nodes) > 1:
            warnings.append("Workflow has multiple nodes but no edges")

        # Check for start node
        start_node = definition.get_start_node()
        if not start_node:
            warnings.append("No start node defined")

        # Check for end nodes
        end_nodes = definition.get_end_nodes()
        if not end_nodes:
            warnings.append("No end nodes defined")

        return WorkflowValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
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
