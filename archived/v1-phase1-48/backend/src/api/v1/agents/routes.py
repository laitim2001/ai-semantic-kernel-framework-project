# =============================================================================
# IPA Platform - Agent API Routes
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# RESTful API endpoints for Agent management:
#   - POST /agents/ - Create agent
#   - GET /agents/ - List agents
#   - GET /agents/{id} - Get agent
#   - PUT /agents/{id} - Update agent
#   - DELETE /agents/{id} - Delete agent
#   - POST /agents/{id}/run - Run agent
# =============================================================================

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.agents.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentListResponse,
    AgentRunRequest,
    AgentRunResponse,
)
from src.domain.agents.service import (
    AgentConfig,
    AgentService,
    get_agent_service,
)
from src.infrastructure.database.session import get_session
from src.infrastructure.database.repositories.agent import AgentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


# =============================================================================
# Dependencies
# =============================================================================


async def get_agent_repository(
    session: AsyncSession = Depends(get_session),
) -> AgentRepository:
    """Dependency for AgentRepository."""
    return AgentRepository(session)


async def get_service() -> AgentService:
    """Dependency for AgentService."""
    return get_agent_service()


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Agent",
    description="Create a new AI agent with instructions and tools.",
)
async def create_agent(
    request: AgentCreateRequest,
    repo: AgentRepository = Depends(get_agent_repository),
) -> AgentResponse:
    """
    Create a new agent.

    - **name**: Unique agent identifier
    - **instructions**: System prompt for the agent
    - **tools**: List of tool names the agent can use
    """
    # Check for duplicate name
    existing = await repo.get_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{request.name}' already exists",
        )

    # Create agent
    agent = await repo.create(
        name=request.name,
        description=request.description,
        instructions=request.instructions,
        category=request.category,
        tools=request.tools,
        model_config=request.model_config_data,
        max_iterations=request.max_iterations,
    )

    logger.info(f"Created agent: {agent.name} (id={agent.id})")

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        instructions=agent.instructions,
        category=agent.category,
        tools=agent.tools if isinstance(agent.tools, list) else [],
        model_config_data=agent.model_config if isinstance(agent.model_config, dict) else {},
        max_iterations=agent.max_iterations,
        status=agent.status,
        version=agent.version,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.get(
    "/",
    response_model=AgentListResponse,
    summary="List Agents",
    description="Get paginated list of agents with optional filters.",
)
async def list_agents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status",
    ),
    search: Optional[str] = Query(default=None, description="Search in name/description"),
    repo: AgentRepository = Depends(get_agent_repository),
) -> AgentListResponse:
    """
    List agents with pagination and filters.

    - **page**: Page number (1-indexed)
    - **page_size**: Number of items per page
    - **category**: Optional category filter
    - **status**: Optional status filter
    - **search**: Optional search query
    """
    if search:
        items, total = await repo.search(search, page=page, page_size=page_size)
    else:
        filters = {}
        if category:
            filters["category"] = category
        if status_filter:
            filters["status"] = status_filter

        items, total = await repo.list(page=page, page_size=page_size, **filters)

    return AgentListResponse(
        items=[
            AgentResponse(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                instructions=agent.instructions,
                category=agent.category,
                tools=agent.tools if isinstance(agent.tools, list) else [],
                model_config_data=agent.model_config if isinstance(agent.model_config, dict) else {},
                max_iterations=agent.max_iterations,
                status=agent.status,
                version=agent.version,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
            )
            for agent in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get Agent",
    description="Get a specific agent by ID.",
)
async def get_agent(
    agent_id: UUID,
    repo: AgentRepository = Depends(get_agent_repository),
) -> AgentResponse:
    """Get agent by ID."""
    agent = await repo.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        instructions=agent.instructions,
        category=agent.category,
        tools=agent.tools if isinstance(agent.tools, list) else [],
        model_config_data=agent.model_config if isinstance(agent.model_config, dict) else {},
        max_iterations=agent.max_iterations,
        status=agent.status,
        version=agent.version,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update Agent",
    description="Update an existing agent.",
)
async def update_agent(
    agent_id: UUID,
    request: AgentUpdateRequest,
    repo: AgentRepository = Depends(get_agent_repository),
) -> AgentResponse:
    """
    Update agent fields.

    Only provided fields will be updated.
    """
    # Check exists
    existing = await repo.get(agent_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )

    # Check name uniqueness if changing name
    if request.name and request.name != existing.name:
        name_taken = await repo.get_by_name(request.name)
        if name_taken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent with name '{request.name}' already exists",
            )

    # Build update data
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.instructions is not None:
        update_data["instructions"] = request.instructions
    if request.category is not None:
        update_data["category"] = request.category
    if request.tools is not None:
        update_data["tools"] = request.tools
    if request.model_config_data is not None:
        update_data["model_config"] = request.model_config_data
    if request.max_iterations is not None:
        update_data["max_iterations"] = request.max_iterations
    if request.status is not None:
        update_data["status"] = request.status

    # Update
    agent = await repo.update(agent_id, **update_data)

    # Increment version
    await repo.increment_version(agent_id)
    agent = await repo.get(agent_id)

    logger.info(f"Updated agent: {agent.name} (id={agent.id})")

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        instructions=agent.instructions,
        category=agent.category,
        tools=agent.tools if isinstance(agent.tools, list) else [],
        model_config_data=agent.model_config if isinstance(agent.model_config, dict) else {},
        max_iterations=agent.max_iterations,
        status=agent.status,
        version=agent.version,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Agent",
    description="Delete an agent.",
)
async def delete_agent(
    agent_id: UUID,
    repo: AgentRepository = Depends(get_agent_repository),
) -> None:
    """Delete agent by ID."""
    deleted = await repo.delete(agent_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )

    logger.info(f"Deleted agent: {agent_id}")


# =============================================================================
# Execution Endpoint
# =============================================================================


@router.post(
    "/{agent_id}/run",
    response_model=AgentRunResponse,
    summary="Run Agent",
    description="Execute an agent with a message.",
)
async def run_agent(
    agent_id: UUID,
    request: AgentRunRequest,
    repo: AgentRepository = Depends(get_agent_repository),
    service: AgentService = Depends(get_service),
) -> AgentRunResponse:
    """
    Run an agent with a message.

    - **message**: The user message to process
    - **context**: Optional additional context
    - **tools_override**: Optional tool list to use instead of defaults
    """
    # Get agent from database
    agent = await repo.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )

    # Check agent is active
    if agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent is not active (status: {agent.status})",
        )

    # Ensure service is initialized
    if not service.is_initialized:
        await service.initialize()

    # Build config
    config = AgentConfig(
        name=agent.name,
        instructions=agent.instructions,
        tools=[],  # Tools will be resolved in S1-3
        model_config=agent.model_config if isinstance(agent.model_config, dict) else {},
        max_iterations=agent.max_iterations,
    )

    # Run agent
    try:
        result = await service.run_agent_with_config(
            config=config,
            message=request.message,
            context=request.context,
        )

        logger.info(
            f"Agent {agent.name} executed: "
            f"tokens={result.llm_tokens}, cost=${result.llm_cost:.6f}"
        )

        return AgentRunResponse(
            result=result.text,
            stats={
                "llm_calls": result.llm_calls,
                "llm_tokens": result.llm_tokens,
                "llm_cost": result.llm_cost,
            },
            tool_calls=result.tool_calls,
        )

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )
