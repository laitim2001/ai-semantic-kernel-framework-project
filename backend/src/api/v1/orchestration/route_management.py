"""
Route Management API Routes.

Sprint 115: Story 115-3 - Route Management API and Data Migration

Provides CRUD endpoints for managing semantic routes stored in
Azure AI Search, plus a sync/migration endpoint and search testing.

Endpoints:
    POST   /api/v1/orchestration/routes        — Create a new route
    GET    /api/v1/orchestration/routes        — List routes (filterable)
    GET    /api/v1/orchestration/routes/{name} — Get single route detail
    PUT    /api/v1/orchestration/routes/{name} — Update a route
    DELETE /api/v1/orchestration/routes/{name} — Delete a route
    POST   /api/v1/orchestration/routes/sync   — Sync predefined routes
    POST   /api/v1/orchestration/routes/search — Test vector search
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

route_management_router = APIRouter(
    prefix="/orchestration/routes",
    tags=["orchestration-routes"],
    responses={
        503: {"description": "Azure AI Search is not enabled"},
    },
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateRouteRequest(BaseModel):
    """Request body for creating a new semantic route."""

    route_name: str = Field(..., min_length=1, max_length=100, description="Unique route name")
    category: str = Field(
        ...,
        pattern="^(incident|request|change|query)$",
        description="Intent category",
    )
    sub_intent: str = Field(..., min_length=1, max_length=100, description="Specific intent type")
    utterances: List[str] = Field(..., min_length=1, description="Example utterances (>=1)")
    description: str = Field(default="", description="Human-readable description")
    workflow_type: str = Field(default="simple", description="Workflow type")
    risk_level: str = Field(default="medium", description="Risk level")


class UpdateRouteRequest(BaseModel):
    """Request body for updating an existing route."""

    utterances: Optional[List[str]] = Field(None, description="New utterances (triggers re-embedding)")
    description: Optional[str] = Field(None, description="Updated description")
    workflow_type: Optional[str] = Field(None, description="Updated workflow type")
    risk_level: Optional[str] = Field(None, description="Updated risk level")
    enabled: Optional[bool] = Field(None, description="Enable or disable the route")


class SearchTestRequest(BaseModel):
    """Request body for testing vector search."""

    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Max results (1-20)")


class RouteResponse(BaseModel):
    """Generic response for route operations."""

    route_name: str
    category: str = ""
    sub_intent: str = ""
    utterance_count: int = 0
    workflow_type: str = "simple"
    risk_level: str = "medium"
    description: str = ""
    enabled: bool = True
    status: str = ""


class RouteDetailResponse(BaseModel):
    """Detailed response for a single route including utterances."""

    route_name: str
    category: str = ""
    sub_intent: str = ""
    utterances: List[str] = []
    utterance_count: int = 0
    workflow_type: str = "simple"
    risk_level: str = "medium"
    description: str = ""
    enabled: bool = True
    document_ids: List[str] = []


class SyncResponse(BaseModel):
    """Response for the sync/migration endpoint."""

    routes_synced: int
    utterances_synced: int
    documents_in_index: int = 0
    status: str = "success"


class DeleteResponse(BaseModel):
    """Response for the delete endpoint."""

    route_name: str
    documents_deleted: int
    status: str = "deleted"


class SearchResultItem(BaseModel):
    """A single search result item."""

    route_name: str = ""
    category: str = ""
    sub_intent: str = ""
    utterance: str = ""
    score: float = 0.0
    workflow_type: str = ""
    risk_level: str = ""


# ---------------------------------------------------------------------------
# Dependency — RouteManager factory
# ---------------------------------------------------------------------------


def get_route_manager():
    """Factory to create RouteManager with env-based configuration.

    Returns:
        Configured RouteManager instance.

    Raises:
        HTTPException: If Azure AI Search is not enabled via env vars.
    """
    use_azure = os.getenv("USE_AZURE_SEARCH", "false").lower() == "true"
    if not use_azure:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure AI Search is not enabled. Set USE_AZURE_SEARCH=true",
        )

    from src.integrations.orchestration.intent_router.semantic_router.azure_search_client import (
        AzureSearchClient,
    )
    from src.integrations.orchestration.intent_router.semantic_router.embedding_service import (
        EmbeddingService,
    )
    from src.integrations.orchestration.intent_router.semantic_router.route_manager import (
        RouteManager,
    )

    search_client = AzureSearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
        api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "semantic-routes"),
    )
    embedding_service = EmbeddingService(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        deployment=os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
        ),
    )
    return RouteManager(
        search_client=search_client,
        embedding_service=embedding_service,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@route_management_router.post(
    "",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new semantic route",
    description="Create a route with auto-generated embeddings for each utterance.",
)
async def create_route(
    request: CreateRouteRequest,
    manager=Depends(get_route_manager),
) -> RouteResponse:
    """Create a new semantic route with embedding generation.

    Args:
        request: Route creation payload.
        manager: Injected RouteManager instance.

    Returns:
        Created route metadata.
    """
    try:
        result = await manager.create_route(
            route_name=request.route_name,
            category=request.category,
            sub_intent=request.sub_intent,
            utterances=request.utterances,
            description=request.description,
            workflow_type=request.workflow_type,
            risk_level=request.risk_level,
        )
        return RouteResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create route: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create route",
        )


@route_management_router.get(
    "",
    response_model=List[RouteResponse],
    summary="List semantic routes",
    description="List all routes with optional category/enabled filters.",
)
async def list_routes(
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    manager=Depends(get_route_manager),
) -> List[RouteResponse]:
    """List all semantic routes.

    Args:
        category: Optional category filter.
        enabled: Optional enabled filter.
        manager: Injected RouteManager instance.

    Returns:
        List of route summaries.
    """
    try:
        results = await manager.get_routes(category=category, enabled=enabled)
        return [RouteResponse(**r) for r in results]
    except Exception as e:
        logger.error(f"Failed to list routes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list routes",
        )


@route_management_router.get(
    "/{route_name}",
    response_model=RouteDetailResponse,
    summary="Get a single route",
    description="Get route detail including all utterances and document IDs.",
)
async def get_route(
    route_name: str,
    manager=Depends(get_route_manager),
) -> RouteDetailResponse:
    """Get a single route by name.

    Args:
        route_name: Unique route name.
        manager: Injected RouteManager instance.

    Returns:
        Route detail with utterances.
    """
    try:
        result = await manager.get_route(route_name)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route '{route_name}' not found",
            )
        return RouteDetailResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get route '{route_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get route",
        )


@route_management_router.put(
    "/{route_name}",
    response_model=RouteResponse,
    summary="Update a route",
    description="Update route metadata or utterances (re-embedding if changed).",
)
async def update_route(
    route_name: str,
    request: UpdateRouteRequest,
    manager=Depends(get_route_manager),
) -> RouteResponse:
    """Update a route's metadata or utterances.

    Args:
        route_name: Route to update.
        request: Update payload.
        manager: Injected RouteManager instance.

    Returns:
        Updated route summary.
    """
    try:
        result = await manager.update_route(
            route_name=route_name,
            utterances=request.utterances,
            description=request.description,
            workflow_type=request.workflow_type,
            risk_level=request.risk_level,
            enabled=request.enabled,
        )
        return RouteResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update route '{route_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update route",
        )


@route_management_router.delete(
    "/{route_name}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteResponse,
    summary="Delete a route",
    description="Delete a route and all its utterance documents.",
)
async def delete_route(
    route_name: str,
    manager=Depends(get_route_manager),
) -> DeleteResponse:
    """Delete a route by name.

    Args:
        route_name: Route to delete.
        manager: Injected RouteManager instance.

    Returns:
        Deletion confirmation.
    """
    try:
        result = await manager.delete_route(route_name)
        return DeleteResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to delete route '{route_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete route",
        )


@route_management_router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Sync predefined routes to Azure AI Search",
    description="Migrate the 15 predefined semantic routes from Python definitions "
    "to the Azure AI Search index with auto-generated embeddings.",
)
async def sync_routes(
    manager=Depends(get_route_manager),
) -> SyncResponse:
    """Sync predefined routes to Azure AI Search.

    Args:
        manager: Injected RouteManager instance.

    Returns:
        Migration statistics.
    """
    try:
        result = await manager.sync_from_yaml()
        return SyncResponse(**result)
    except Exception as e:
        logger.error(f"Failed to sync routes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync routes",
        )


@route_management_router.post(
    "/search",
    response_model=List[SearchResultItem],
    summary="Test vector search",
    description="Run a test vector search query and return results with scores.",
)
async def search_test(
    request: SearchTestRequest,
    manager=Depends(get_route_manager),
) -> List[SearchResultItem]:
    """Test the search functionality.

    Args:
        request: Search query and parameters.
        manager: Injected RouteManager instance.

    Returns:
        Search results with relevance scores.
    """
    try:
        results = await manager.search_test(query=request.query, top_k=request.top_k)
        return [SearchResultItem(**r) for r in results]
    except Exception as e:
        logger.error(f"Search test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search test failed",
        )
